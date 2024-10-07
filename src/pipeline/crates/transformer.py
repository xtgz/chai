import csv
import json
import os
import sys
from typing import Dict

from utils.utils import safe_int
from src.pipeline.utils.crates.structures import DependencyType
from src.pipeline.utils.logger import Logger

DEFAULT_BATCH_SIZE = 10


class TransformerV2:
    def __init__(self, name: str):
        self.name = name
        self.input = f"data/{name}/latest"
        self.logger = Logger(name)
        self.files = {
            "packages": "",
            "versions": "",
            "dependencies": "",
            "users": "",
            "urls": "",
        }
        self.batch_size = DEFAULT_BATCH_SIZE

    def finder(self, file_name: str) -> str:
        input_dir = os.path.realpath(self.input)

        for root, _, files in os.walk(input_dir):
            if file_name in files:
                return os.path.join(root, file_name)
        else:
            self.logger.error(f"{file_name} not found in {input_dir}")
            raise FileNotFoundError(f"Missing {file_name} file")

    def output(self, file_path: str, row_processor: callable) -> None:
        with open(file_path) as f:
            reader = csv.DictReader(f)
            batch = []
            for row in reader:
                processed_row = row_processor(row)
                batch.append(processed_row)
                if len(batch) == self.batch_size:
                    json.dump(batch, sys.stdout)
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                    batch = []
                    sys.exit()
            if batch:
                json.dump(batch, sys.stdout)
                sys.stdout.write("\n")
                sys.stdout.flush()


class CratesTransformerV2(TransformerV2):
    def __init__(self):
        super().__init__("crates")
        self.files = {
            "projects": "crates.csv",
            "versions": "versions.csv",
            "dependencies": "dependencies.csv",
            "users": "users.csv",
            "urls": "crates.csv",
        }

    def packages(self):
        projects_path = self.finder(self.files["projects"])

        def process_row(row: Dict) -> Dict:
            return {
                "name": row["name"],
                "import_id": row["id"],
                "readme": row["readme"],
            }

        self.output(projects_path, process_row)

    def versions(self):
        versions_path = self.finder(self.files["versions"])

        def process_row(row: Dict) -> Dict:
            return {
                "crate_id": row["crate_id"],
                "version": row["num"],
                "import_id": row["id"],
                "size": safe_int(row["crate_size"]),
                "published_at": row["created_at"],
                "license": row["license"],
                "downloads": safe_int(row["downloads"]),
                "checksum": row["checksum"],
            }

        self.output(versions_path, process_row)

    def dependencies(self):
        dependencies_path = self.finder(self.files["dependencies"])

        def process_row(row: Dict) -> Dict:
            return {
                "start_id": row["version_id"],
                "end_id": row["crate_id"],
                "semver_range": row["req"],
                "dependency_type": DependencyType(int(row["kind"])).value,
            }

        self.output(dependencies_path, process_row)


if __name__ == "__main__":
    test = CratesTransformerV2()
    test.packages()
