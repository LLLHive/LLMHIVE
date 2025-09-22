"""Constants and enumerations used across the application."""
from __future__ import annotations

from enum import Enum


class SubTaskRole(str, Enum):
    OPTIMIZER = "optimizer"
    CRITIC = "critic"
    REFEREE = "referee"
    FACTCHECK = "factcheck"
    WORKER = "worker"


class VoteVoter(str, Enum):
    AUTO = "auto"
    HUMAN = "human"
    REFEREE = "referee"


class FactCheckMethod(str, Enum):
    WEB = "web"
    DB = "db"
    API = "api"
    LLM = "llm"


class FactCheckVerdict(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    UNCLEAR = "unclear"
