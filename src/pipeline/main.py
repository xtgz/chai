import sys
import traceback
from os import getenv

from src.pipeline.crates import get_crates_packages
from src.pipeline.pkgx import get_pkgx_packages
from src.pipeline.utils.logger import Logger
from src.pipeline.utils.pg import DB

logger = Logger("main_pipeline")


def main():
    if len(sys.argv) != 2:
        print("usage: python main.py <package_manager>")
        sys.exit(1)

    if getenv("CHAI_DATABASE_URL") is None:
        logger.error("CHAI_DATABASE_URL is not set")
        sys.exit(1)

    # initialize the db and handoff everywhere
    db = DB()
    package_manager = sys.argv[1]

    try:
        if package_manager == "pkgx":
            get_pkgx_packages(db)
        elif package_manager == "crates":
            get_crates_packages(db)
        else:
            print("invalid package manager")
            sys.exit(1)
    except Exception as e:
        # collect all the exception information
        exc_type, exc_value, exc_traceback = sys.exc_info()
        # TODO: move this to logger class
        logger.error(f"{exc_type.__name__}: {exc_value}")
        logger.error(f"traceback: {''.join(traceback.format_tb(exc_traceback))}")
        sys.exit(1)


if __name__ == "__main__":
    main()
