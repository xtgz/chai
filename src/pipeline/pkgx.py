import json
import os

from requests import RequestException, get
from requests.exceptions import HTTPError
from src.pipeline.utils.logger import Logger

# env vars
PANTRY_URL = "https://api.github.com/repos/pkgxdev/pantry"
OUTPUT_DIR = "data/pkgx"

# setup
headers = {
    "Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}",
}


def get_contents(path: str) -> list[dict]:
    url = f"{PANTRY_URL}/contents/{path}"
    response = get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def get_pkgx_packages(logger: Logger) -> None:
    try:
        packages = {}
        projects = get_contents("projects")

        for project in projects:
            logger.debug(f"project: {project}")
            if project["type"] == "dir":
                project_contents = get_contents(project["path"])
                for item in project_contents:
                    if item["name"] == "package.yml":
                        response = get(item["download_url"], headers=headers)
                        packages[project["name"]] = response.text

        # Ensure output directory exists
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        # Write packages to JSON file
        output_file = os.path.join(OUTPUT_DIR, "pkgx_packages.json")
        with open(output_file, "w") as f:
            json.dump(packages, f, indent=2)

    except HTTPError as e:
        if e.response.status_code == 404:
            logger.error("404, probs bad url")
        elif e.response.status_code == 401:
            logger.error("401, probs bad token")
        raise e
    except RequestException as e:
        logger.error(f"RequestException: {e}")
        raise e
    except Exception as e:
        logger.error(f"Exception: {e}")
        raise e
