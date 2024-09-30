import os
from typing import Iterable, List, Type

from sqlalchemy import UUID, create_engine
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.decl_api import DeclarativeMeta
from sqlalchemy.orm.session import Session
from src.pipeline.models import DependsOn, LoadHistory, Package, PackageManager, Version
from src.pipeline.utils.logger import Logger

CHAI_DATABASE_URL = os.getenv("CHAI_DATABASE_URL")


class DB:
    def __init__(self):
        self.logger = Logger("DB")
        self.engine = create_engine(CHAI_DATABASE_URL)
        self.session = sessionmaker(self.engine)
        self.logger.debug("connected")

    # TODO: move to transformer_v2
    def _batch(
        self,
        items: Iterable[DeclarativeMeta],
        model: Type[DeclarativeMeta],
        batch_size: int = 10000,
    ) -> None:
        """just handles batching logic for any type of model we wanna insert"""
        self.logger.debug("starting a batch insert")
        with self.session() as session:
            batch = []
            for item in items:
                batch.append(item)
                if len(batch) == batch_size:
                    self.logger.debug(f"inserting {len(batch)} {model.__name__}")
                    self._insert_batch(batch, session, model)
                    batch = []  # reset

            if batch:
                self.logger.debug(f"finally, inserting {len(batch)} {model.__name__}")
                self._insert_batch(batch, session, model)

            session.commit()  # commit here

    def _insert_batch(
        self,
        batch: List[DeclarativeMeta],
        session: Session,
        model: Type[DeclarativeMeta],
    ) -> None:
        """
        inserts a batch of items, any model, into the database
        however, this mandates `on conflict do nothing`
        """
        # we use statements here, not ORMs because of the on_conflict_do_nothing
        # https://github.com/sqlalchemy/sqlalchemy/issues/5374
        stmt = (
            insert(model)
            .values([item.to_dict() for item in batch])
            .on_conflict_do_nothing()
        )
        session.execute(stmt)

    def insert_packages(
        self, package_generator: Iterable[str], package_manager: PackageManager
    ) -> List[UUID]:
        def package_object_generator():
            for name in package_generator:
                yield Package(
                    derived_id=f"{package_manager.name}/{name}",
                    name=name,
                    package_manager_id=package_manager.id,
                )

        return self._batch(package_object_generator(), Package, 10000)

    def insert_versions(self, version_generator: Iterable[dict[str, str]]):
        def version_object_generator():
            for item in version_generator:
                package_id = item["package_id"]
                version = item["version"]
                yield Version(
                    package_id=package_id,
                    version=version,
                )

        self._batch(version_object_generator(), Version, 10000)

    def insert_dependencies(self, dependency_generator: Iterable[dict[str, str]]):
        def dependency_object_generator():
            for item in dependency_generator:
                version_id = item["version_id"]
                dependency_id = item["dependency_id"]
                semver_range = item["semver_range"]
                yield DependsOn(
                    version_id=version_id,
                    dependency_id=dependency_id,
                    semver_range=semver_range,
                )

        self._batch(dependency_object_generator(), DependsOn, 10000)

    def insert_load_history(self, package_manager_id: str):
        with self.session() as session:
            session.add(LoadHistory(package_manager_id=package_manager_id))
            session.commit()

    def get_package_manager_id(self, package_manager: str):
        with self.session() as session:
            result = (
                session.query(PackageManager).filter_by(name=package_manager).first()
            )

            if result:
                self.logger.debug(f"id: {result.id}")
                return result.id
            return None

    def insert_package_manager(self, package_manager: str) -> UUID | None:
        with self.session() as session:
            exists = self.get_package_manager_id(package_manager) is not None
            if not exists:
                session.add(PackageManager(name=package_manager))
                session.commit()
                return (
                    session.query(PackageManager)
                    .filter_by(name=package_manager)
                    .first()
                    .id
                )

    def select_packages_by_package_manager(
        self, package_manager: PackageManager
    ) -> List[Package]:
        with self.session() as session:
            return (
                session.query(Package)
                .filter_by(package_manager_id=package_manager.id)
                .all()
            )

    def select_versions_by_package_manager(
        self, package_manager: PackageManager
    ) -> List[Version]:
        with self.session() as session:
            return (
                session.query(Version)
                .join(Package)
                .filter(Package.package_manager_id == package_manager.id)
                .all()
            )

    def print_statement(self, stmt):
        dialect = postgresql.dialect()
        compiled_stmt = stmt.compile(
            dialect=dialect, compile_kwargs={"literal_binds": True}
        )
        self.logger.log(str(compiled_stmt))


if __name__ == "__main__":
    db = DB()
    # random tests
    package_manager = PackageManager(
        name="crates", id=db.get_package_manager_id("crates")
    )
    print(db.select_package_manager_versions(package_manager))
