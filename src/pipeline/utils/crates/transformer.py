import csv

from typing import Dict, Generator, List
from sqlalchemy import UUID
from src.pipeline.utils.crates.structures import Crate, CrateVersion, User, URL
from src.pipeline.utils.transformer import Transformer
from src.pipeline.models import Package, Version


# crates provides homepage and repository urls, so we'll initialize this transformer
# with the ids for those url types
class CratesTransformer(Transformer):
    def __init__(self, homepage_url_type_id: UUID, repository_url_type_id: UUID):
        super().__init__("crates")
        self.files = {
            "projects": "crates.csv",
            "versions": "versions.csv",
            "dependencies": "dependencies.csv",
            "users": "users.csv",
            "urls": "crates.csv",
        }
        self.url_types = {
            "homepage": homepage_url_type_id,
            "repository": repository_url_type_id,
        }
        # TODO: see line 54 in crates.py, but we need to reduce the number of Dicts
        # we are creating to just 2:
        # Dict[crate_id, Crate] and Dict[version_id, CrateVersion]
        # some considerations for a solution:
        # - where do we populate the maps? definitely upon loading the packages. should
        #   we populate them as we go? or keep that separate? the tradeoff is simplicity
        #   vs. performance. i'd have to iterate twice, but the simplicity is nice
        self.crates: Dict[int, Crate] = {}
        self.name_map: Dict[str, int] = {}
        self.crate_versions: Dict[int, CrateVersion] = {}
        self.num_map: Dict[str, int] = {}
        self.user_map: Dict[int, User] = {}
        self.url_map: Dict[str, URL] = {}

    def packages(self) -> Generator[str, None, None]:
        projects_path = self.finder(self.files["projects"])

        with open(projects_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                # track it in our map
                crate_id = row["id"]
                name = row["name"]
                self.crates[crate_id] = Crate(crate_id=crate_id, name=name)
                self.name_map[name] = crate_id

                # get the homepage and repository urls
                # but don't yield them yet
                homepage_url = row["homepage"]
                repository_url = row["repository"]

                if homepage_url.strip():
                    self.crates[crate_id].urls.append(homepage_url)
                    self.url_map[homepage_url] = URL(
                        type=self.url_types["homepage"], db_id=None
                    )
                if repository_url.strip():
                    self.crates[crate_id].urls.append(repository_url)
                    self.url_map[repository_url] = URL(
                        type=self.url_types["repository"], db_id=None
                    )

                # yield name for loading into postgres
                yield {"name": name}

    def versions(self) -> Generator[Dict[str, int], None, None]:
        versions_path = self.finder(self.files["versions"])

        with open(versions_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                # track it on our crates map
                crate_id = row["crate_id"]
                if crate_id not in self.crates:
                    raise ValueError(f"Crate {crate_id} not found in crates")
                self.crates[crate_id].versions.append(row["num"])

                # track it on our versions map
                version_id = row["id"]
                version_num = row["num"]
                self.crate_versions[version_id] = CrateVersion(
                    version_id=version_id, version=version_num
                )
                self.num_map[version_num] = version_id

                # get the information we need
                package_id = self.get_crate_db_id(crate_id)

                yield {
                    "package_id": package_id,
                    "version": version_num,
                }

    def dependencies(self):
        dependencies_path = self.finder(self.files["dependencies"])

        with open(dependencies_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                start_id = row["version_id"]
                end_id = row["dependency_id"]
                semver = row["req"]

                version_id = self.get_crate_version_db_id(start_id)
                dependency_id = self.get_crate_db_id(end_id)
                yield {
                    "version_id": version_id,
                    "dependency_id": dependency_id,
                    "semver_range": semver,
                }

    # crate_owners.csv has the crate_id to user mapping
    # we need to maintain the user_id to username mapping
    def users(self):
        users_path = self.finder(self.files["users"])

        with open(users_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                crates_user_id = row["id"]
                username = row["gh_login"]
                self.user_map[crates_user_id] = User(
                    id=crates_user_id, username=username
                )
                yield {"username": username}

    # note that this function does not open a file
    # it actually yields a url, by going through the map which was already built
    # TODO: can we avoid this double iteration? this represents a similar tradeoff
    # mentioned on line 30 in this file. separation of concerns is a good thing, and
    # python is pretty good about loops
    def urls(self):
        for url in self.url_map.keys():
            yield url

    def url_types(self):
        yield {"type": "homepage"}
        yield {"type": "repository"}

    def url_to_pkg(self):
        for _, crate in self.crates.items():
            for url in crate.urls:
                yield {
                    "package_id": crate.db_id,
                    "url_id": self.url_map[url].db_id,
                    "url_type_id": self.url_map[url].type,  # already an ID!
                }

    def get_crate_db_id(self, crate_id: int) -> UUID:
        return self.crates[crate_id].db_id

    def get_crate_version_db_id(self, version_id: int) -> UUID:
        return self.crate_versions[version_id].db_id

    def update_crates_db_ids(self, packages: List[Package]):
        for pkg in packages:
            try:
                crate_id = self.name_map[pkg.name]
                self.crates[crate_id].db_id = pkg.id
            except KeyError:
                self.logger.warn(f"pkg {pkg.name} not found in name map")

    def update_crates_versions_db_ids(self, versions: List[Version]):
        for version in versions:
            # version is a number and a package_id
            crate_version_id = self.num_map[version.version]
            self.crate_versions[crate_version_id].db_id = version.id

    def update_crates_urls_db_ids(self, urls: List[URL]):
        for url in urls:
            if url.url == "":
                self.logger.warn(f"skipping empty url in db: {url.id}")
                continue
            try:
                self.url_map[url.url].db_id = url.id
            except KeyError:
                self.logger.warn(f"skipping {url.url} in db: {url.id}")
