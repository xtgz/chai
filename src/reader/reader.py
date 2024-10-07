from typing import Dict, List
import csv
import json
import os
import sys

DEFAULT_BATCH_SIZE = 100

# this is a temporary fix, but sometimes the raw files have weird characters
# and lots of data within certain fields
# this fix allows us to read the files with no hassles
csv.field_size_limit(10000000)


class Reader:
    def __init__(self, name: str):
        self.name = name
        self.input = f"data/{name}/latest"
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
        def write_batch(batch: List[Dict]) -> None:
            json.dump(batch, sys.stdout)
            sys.stdout.write("\n")
            sys.stdout.flush()

        with open(file_path) as f:
            reader = csv.DictReader(f)
            batch = []
            for row in reader:
                processed_row = row_processor(row)
                batch.append(processed_row)
                if len(batch) == self.batch_size:
                    write_batch(batch)
                    batch = []
                    # break

            if batch:
                write_batch(batch)
