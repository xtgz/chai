from dataclasses import dataclass, field
from typing import List
from sqlalchemy import UUID


@dataclass
class Crate:
    crate_id: int
    name: str
    versions: List[int] = field(default_factory=list)
    urls: List[str] = field(default_factory=list)
    db_id: UUID | None = None


@dataclass
class CrateVersion:
    version_id: int
    version: str
    db_id: UUID | None = None


@dataclass
class User:
    id: int
    username: str
    db_id: UUID | None = None


@dataclass
class URL:
    type: str
    db_id: UUID | None = None
