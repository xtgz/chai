#!/bin/bash

# wait for db to be ready
until pg_isready -h db -p 5432 -U postgres; do
  echo "waiting for database..."
  sleep 2
done

# make directory structure
# working_dir is /app
mkdir -p data/{crates,pkgx,homebrew,npm,pypi,rubys}

pkgx +python^3.11 +postgresql.org^16 python -u src/pipeline/main.py crates