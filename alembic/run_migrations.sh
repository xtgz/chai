#!/bin/bash

# wait for db to be ready
until pg_isready -h db -p 5432 -U postgres; do
  echo "waiting for database..."
  sleep 2
done

# migrate
echo "db currently at $(pkgx +alembic +psycopg.org/psycopg2 alembic current)"
pkgx +alembic +psycopg.org/psycopg2 alembic upgrade head
echo "migrations run"