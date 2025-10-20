"""Test configuration for LLMHive."""
import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

ROOT = Path(__file__).resolve().parents[2]
src_path = ROOT / "src"
if not src_path.exists():
    src_path = ROOT / "llmhive" / "src"
sys.path.insert(0, str(src_path))

import pytest
from fastapi.testclient import TestClient

from llmhive.app.database import engine, session_scope
from llmhive.app.main import app
from llmhive.app.models import Base


@pytest.fixture(scope="session", autouse=True)
def create_schema() -> None:
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def db_session():
    with session_scope() as session:
        yield session
