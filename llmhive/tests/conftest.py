"""Test configuration for LLMHive."""
import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("LLMHIVE_FAIL_ON_STUB", "false")  # Allow stub responses in tests

ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "llmhive" / "src"
LEGACY_SRC_ROOT = ROOT / "src"

if SRC_ROOT.exists():
    sys.path.insert(0, str(SRC_ROOT))
elif LEGACY_SRC_ROOT.exists():
    # Support historic layouts where code lived directly under /src
    sys.path.insert(0, str(LEGACY_SRC_ROOT))
else:
    raise RuntimeError("Unable to locate application source directory for tests")

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
