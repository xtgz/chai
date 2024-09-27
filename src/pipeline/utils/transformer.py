import csv
import os
from dataclasses import dataclass, field
from typing import Dict, Generator, List

from sqlalchemy import UUID
from src.pipeline.models import Package, Version
from src.pipeline.utils.logger import Logger

# TODO: do we need to do that?
# we do for now, but we can figure it out later
csv.field_size_limit(10000000)


# this is a file buffer
# it WILL NOT write a file anywhere
class Transformer:
    def __init__(self, name: str):
        self.name = name
        self.input = f"data/{name}/latest"
        self.logger = Logger(f"{name}_transformer")

    # knows what files to open
    def transform(self) -> str:
        # opens
        pass

    def projects(self, data: str):
        pass

    def versions(self, data: str):
        pass

    def dependencies(self, data: str):
        pass


# load this in once: build this dictionary
# {"1.0.0": "semverator", "1.0.1": "semverator"}
# {"semverator": {"versions": ["1.0.0", "1.0.1"], "uuid": uuid}} => another option
# {"semverator": uuid}
@dataclass
class Crate:
    crate_id: int
    name: str
    versions: List[int] = field(default_factory=list)
    db_id: UUID | None = None


@dataclass
class CrateVersion:
    version_id: int
    version: str
    db_id: UUID | None = None


class CratesTransformer(Transformer):
    def __init__(self):
        super().__init__("crates")
        self.files = {
            "projects": "crates.csv",
            "versions": "versions.csv",
            "dependencies": "dependencies.csv",
        }
        # TODO: we gotta redo this too, it works, but it's unnecessarily bulky
        self.crates: Dict[int, Crate] = {}
        self.name_map: Dict[str, int] = {}
        self.crate_versions: Dict[int, CrateVersion] = {}
        self.num_map: Dict[str, int] = {}

    # TODO: can I move this to the transformer class?
    def finder(self, file_name: str) -> str:
        input_dir = os.path.realpath(self.input)

        for root, _, files in os.walk(input_dir):
            if file_name in files:
                return os.path.join(root, file_name)
        else:
            self.logger.error(f"{file_name} not found in {input_dir}")
            raise FileNotFoundError(f"Missing {file_name} file")

    def packages(self) -> Generator[str, None, None]:
        projects_path = self.finder(self.files["projects"])

        with open(projects_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                # TODO: note that the fact that the below happens within this method
                # us also problematic, as we cannot run purely insert_versions, without
                # running this

                # track it in our map
                crate_id = row["id"]
                name = row["name"]
                self.crates[crate_id] = Crate(crate_id=crate_id, name=name)
                self.name_map[name] = crate_id

                # yield name for loading into postgres
                yield name

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
