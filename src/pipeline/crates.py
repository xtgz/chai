from src.pipeline.models import PackageManager
from src.pipeline.utils.fetcher import TarballFetcher
from src.pipeline.utils.logger import Logger
from src.pipeline.utils.pg import DB
from src.pipeline.utils.crates.transformer import CratesTransformer

FILE_LOCATION = "https://static.crates.io/db-dump.tar.gz"

logger = Logger("crates_orchestrator", mode=Logger.VERBOSE)


# this is the orchestrator for crates
# in general, the orchestrators:
# 0. prep the db for the package manager, getting its id, and anything else
#    that needs to be inserted before we load data (url types, etc)
# 1. fetch data associated with that package manager
# 2. call the various transformer methods associated with that package manager
# 3. load the data into the db
def get_crates_packages(db: DB) -> None:
    # get crates's package manager id, insert it if it doesn't exist
    package_manager_id = db.get_package_manager_id("crates")
    if package_manager_id is None:
        package_manager_id = db.insert_package_manager("crates")
    package_manager = PackageManager(id=package_manager_id, name="crates")

    # get the homepage and repository url types, insert them if they don't exist
    # homepage / repository because that is what crates provides
    homepage_url_type_id = db.select_url_types_homepages()
    if homepage_url_type_id is None:
        homepage_url_type_id = db.insert_url_types("homepage")
    logger.debug(f"homepage_url_type_id: {homepage_url_type_id}")

    repository_url_type_id = db.select_url_types_repositories()
    if repository_url_type_id is None:
        repository_url_type_id = db.insert_url_types("repository")
    logger.debug(f"repository_url_type_id: {repository_url_type_id}")

    # get the raw files
    logger.log("need to unravel a ~3GB tarball, this takes ~42 seconds")
    fetcher = TarballFetcher("crates", FILE_LOCATION)
    files = fetcher.fetch()
    fetcher.write(files)

    # use the transformer to figure out what we'd need for our ranker
    transformer = CratesTransformer(homepage_url_type_id, repository_url_type_id)
    logger.log("transforming crates packages")

    # load the projects, versions, and dependencies into our db
    logger.log("loading crates packages into db, currently this might take a while")

    # packages
    db.insert_packages(transformer.packages(), package_manager)

    # TODO: this is an example of how we are inefficiently using the ORM
    # the database generates ids for us, so we are going back to the db
    # to get the ids of the packages we just loaded, so that we can prepare the crates
    # data correctly, when loading versions, dependencies, users, and urls
    # instead, we should tweak the models so the ORM can take care of this for us

    # TODO: note that we'd still need a map here...the important map is the one
    # between `crate_id`, that comes from fetching, and whatever is loaded into the db
    # we are trying to avoid querying the db to get db_ids, but we already possess the
    # names, version numbers just by reading the files
    logger.log("getting loaded pkg_ids to correctly load versions (takes 5 seconds)")
    loaded_packages = db.select_packages_by_package_manager(package_manager)
    transformer.update_crates_db_ids(loaded_packages)

    # versions
    db.insert_versions(transformer.versions())

    # TODO: see line 54
    # logger.log("getting loaded ver_ids to correctly load deps (takes 50 seconds)")
    # loaded_versions = db.select_versions_by_package_manager(package_manager)
    # transformer.update_crates_versions_db_ids(loaded_versions)

    # dependencies
    # TODO: dependencies are causing OOM issues for now
    logger.log("skipping dependencies, because this causes OOM issues for now")
    # db.insert_dependencies(transformer.dependencies())

    # users
    logger.log("loading crates users into db")
    db.insert_users(transformer.users())

    # TODO: crate_owners.csv

    # urls
    logger.log("loading crates urls into db")
    db.insert_urls(transformer.urls())

    # TODO: see line 54
    logger.log(
        "getting loaded urls to we can establish the links between pkgs and urls"
    )
    loaded_urls = db.select_urls()
    transformer.update_crates_urls_db_ids(loaded_urls)

    # url <-> pkg
    logger.log("establishing links between pkgs and urls")
    db.insert_package_urls(transformer.url_to_pkg())

    # insert load history
    db.insert_load_history(package_manager_id)
    logger.log("✅ crates")
    logger.log("in a new terminal, run README.md/db-list-history to verify")
