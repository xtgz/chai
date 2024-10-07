from typing import Dict
from src.reader.reader import Reader
from src.utils.utils import safe_int


class CratesReader(Reader):
    def __init__(self):
        super().__init__("crates")
        self.files = {
            "packages": "crates.csv",
            "versions": "versions.csv",
            "dependencies": "dependencies.csv",
            "users": "users.csv",
            "urls": "crates.csv",
        }

    def packages(self):
        packages_path = self.finder(self.files["packages"])

        def process_row(row: Dict) -> Dict:
            return {
                "name": row["name"],
                "import_id": row["id"],
                "readme": row["readme"],
            }

        self.output(packages_path, process_row)

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
                "dependency_type": row["kind"],
            }

        self.output(dependencies_path, process_row)
