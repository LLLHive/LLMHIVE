"""Tier Spend Governor — per-account + per-tier cost enforcement.

Enforces:
  1. Free tier: NO paid models, NO paid escalation, tool call caps.
  2. Elite+: per-request cost ceiling + per-account daily/monthly budgets.
  3. Global emergency breaker: shuts down all paid escalation if global
     spend in the last N minutes exceeds threshold.

Ledger backends:
  - in_memory: thread-safe, single-process only (default for local/dev)
  - firestore: multi-instance safe via Firestore documents + transactions
  - redis: legacy multi-instance backend retained for compatibility

Fail-closed: if a multi-instance ledger is configured but unavailable, paid escalation is
blocked with reason_blocked=ledger_unavailable_fail_closed.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ENV FLAGS (all default-safe: restrictive for free, protective for elite+)
# ---------------------------------------------------------------------------
FREE_TIER_MAX_COST_USD_REQUEST = float(
    os.getenv("FREE_TIER_MAX_COST_USD_REQUEST", "0.0")
)
FREE_TIER_MAX_TOOL_CALLS_REQUEST = int(
    os.getenv("FREE_TIER_MAX_TOOL_CALLS_REQUEST", "5")
)
FREE_TIER_MAX_TOOL_CALLS_DAY = int(
    os.getenv("FREE_TIER_MAX_TOOL_CALLS_DAY", "100")
)

ELITE_PLUS_MAX_COST_USD_REQUEST = float(
    os.getenv("ELITE_PLUS_MAX_COST_USD_REQUEST", "0.025")
)
ELITE_PLUS_ACCOUNT_DAILY_BUDGET_USD = float(
    os.getenv("ELITE_PLUS_ACCOUNT_DAILY_BUDGET_USD", "2.0")
)
ELITE_PLUS_ACCOUNT_MONTHLY_BUDGET_USD = float(
    os.getenv("ELITE_PLUS_ACCOUNT_MONTHLY_BUDGET_USD", "25.0")
)
ELITE_PLUS_ACCOUNT_CONCURRENCY_CAP = int(
    os.getenv("ELITE_PLUS_ACCOUNT_CONCURRENCY_CAP", "5")
)

GLOBAL_PAID_ESCALATION_BUDGET_USD_10MIN = float(
    os.getenv("GLOBAL_PAID_ESCALATION_BUDGET_USD_10MIN", "50.0")
)

INTERNAL_ADMIN_OVERRIDE_KEY = os.getenv("INTERNAL_ADMIN_OVERRIDE_KEY", "")

def _default_ledger_backend() -> str:
    configured = os.getenv("SPEND_LEDGER_BACKEND")
    if configured:
        return configured.lower()
    # Production defaults to Firestore for multi-instance safety.
    if os.getenv("K_SERVICE") or os.getenv("ENVIRONMENT", "").lower() == "production":
        return "firestore"
    return "in_memory"


# Ledger backend
SPEND_LEDGER_BACKEND = _default_ledger_backend()
SPEND_LEDGER_PREFIX = os.getenv("SPEND_LEDGER_PREFIX", "llmhive")
FIRESTORE_PROJECT_ID = os.getenv(
    "FIRESTORE_PROJECT_ID",
    os.getenv("GOOGLE_CLOUD_PROJECT", os.getenv("GCP_PROJECT_ID", "")),
)

# Per-account rate limiting
ACCOUNT_QPS_LIMIT = int(os.getenv("ACCOUNT_QPS_LIMIT", "10"))
ACCOUNT_RPM_LIMIT = int(os.getenv("ACCOUNT_RPM_LIMIT", "120"))


# ---------------------------------------------------------------------------
# Decision record (auditable)
# ---------------------------------------------------------------------------
@dataclass
class SpendDecision:
    tier: str
    account_id: str
    predicted_cost_usd: float
    allowed_paid_escalation: bool
    reason_blocked: str = ""
    spend_remaining_day: float = 0.0
    spend_remaining_month: float = 0.0
    tool_calls_remaining_request: int = 0
    global_breaker_active: bool = False
    is_internal_override: bool = False
    ledger_backend: str = "in_memory"
    rate_limited: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Abstract ledger interface
# ---------------------------------------------------------------------------
class SpendLedger(ABC):
    """Interface for spend tracking backends."""

    @abstractmethod
    def record_spend(self, account_id: str, amount: float) -> None: ...

    @abstractmethod
    def record_tool_calls(self, account_id: str, count: int) -> None: ...

    @abstractmethod
    def get_daily_spend(self, account_id: str) -> float: ...

    @abstractmethod
    def get_monthly_spend(self, account_id: str) -> float: ...

    @abstractmethod
    def get_daily_tool_calls(self, account_id: str) -> int: ...

    @abstractmethod
    def acquire_concurrency(self, account_id: str, cap: int) -> bool: ...

    @abstractmethod
    def release_concurrency(self, account_id: str) -> None: ...

    @abstractmethod
    def global_spend_last_n_minutes(self, minutes: int) -> float: ...

    @abstractmethod
    def get_status(self) -> Dict[str, Any]: ...

    @abstractmethod
    def check_rate_limit(self, account_id: str, qps: int, rpm: int) -> bool: ...

    def is_available(self) -> bool:
        return True


# ---------------------------------------------------------------------------
# In-memory ledger (single-process, thread-safe)
# ---------------------------------------------------------------------------
class InMemoryLedger(SpendLedger):
    """Thread-safe in-memory spend ledger. Adequate for single-instance."""

    def __init__(self):
        self._lock = threading.Lock()
        self._daily: Dict[str, float] = defaultdict(float)
        self._monthly: Dict[str, float] = defaultdict(float)
        self._daily_tool_calls: Dict[str, int] = defaultdict(int)
        self._concurrency: Dict[str, int] = defaultdict(int)
        self._global_window: list = []
        self._rate_windows: Dict[str, list] = defaultdict(list)
        self._last_reset_day: int = 0
        self._last_reset_month: int = 0

    def _maybe_reset(self) -> None:
        now = time.time()
        day_key = int(now // 86400)
        month_key = int(now // (86400 * 30))
        if day_key != self._last_reset_day:
            self._daily.clear()
            self._daily_tool_calls.clear()
            self._last_reset_day = day_key
        if month_key != self._last_reset_month:
            self._monthly.clear()
            self._last_reset_month = month_key

    def record_spend(self, account_id: str, amount: float) -> None:
        with self._lock:
            self._maybe_reset()
            self._daily[account_id] += amount
            self._monthly[account_id] += amount
            self._global_window.append((time.time(), amount))

    def record_tool_calls(self, account_id: str, count: int) -> None:
        with self._lock:
            self._maybe_reset()
            self._daily_tool_calls[account_id] += count

    def get_daily_spend(self, account_id: str) -> float:
        with self._lock:
            self._maybe_reset()
            return self._daily.get(account_id, 0.0)

    def get_monthly_spend(self, account_id: str) -> float:
        with self._lock:
            self._maybe_reset()
            return self._monthly.get(account_id, 0.0)

    def get_daily_tool_calls(self, account_id: str) -> int:
        with self._lock:
            self._maybe_reset()
            return self._daily_tool_calls.get(account_id, 0)

    def acquire_concurrency(self, account_id: str, cap: int) -> bool:
        with self._lock:
            current = self._concurrency.get(account_id, 0)
            if current >= cap:
                return False
            self._concurrency[account_id] = current + 1
            return True

    def release_concurrency(self, account_id: str) -> None:
        with self._lock:
            self._concurrency[account_id] = max(
                0, self._concurrency.get(account_id, 0) - 1
            )

    def global_spend_last_n_minutes(self, minutes: int = 10) -> float:
        cutoff = time.time() - (minutes * 60)
        with self._lock:
            self._global_window = [
                (t, a) for t, a in self._global_window if t > cutoff
            ]
            return sum(a for _, a in self._global_window)

    def check_rate_limit(self, account_id: str, qps: int, rpm: int) -> bool:
        now = time.time()
        with self._lock:
            window = self._rate_windows[account_id]
            window[:] = [t for t in window if t > now - 60]
            if len(window) >= rpm:
                return False
            recent_1s = sum(1 for t in window if t > now - 1)
            if recent_1s >= qps:
                return False
            window.append(now)
            return True

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "backend": "in_memory",
                "available": True,
                "active_accounts_daily": len(self._daily),
                "global_spend_10min": self.global_spend_last_n_minutes(10),
                "total_daily_spend": sum(self._daily.values()),
                "total_monthly_spend": sum(self._monthly.values()),
            }


# Backward compat alias
_SpendLedger = InMemoryLedger


# ---------------------------------------------------------------------------
# Redis-backed ledger (multi-instance safe)
# ---------------------------------------------------------------------------
class RedisLedger(SpendLedger):
    """Redis-backed spend ledger with atomic increments and TTL windows.

    Keys:
      {prefix}:daily:{account}   — INCRBYFLOAT, TTL 86400
      {prefix}:monthly:{account} — INCRBYFLOAT, TTL 2678400
      {prefix}:tools:{account}   — INCRBY, TTL 86400
      {prefix}:conc:{account}    — INCRBY/DECRBY
      {prefix}:global:window     — sorted set (score=timestamp, member=amount)
      {prefix}:rate:{account}    — sorted set (score=timestamp)
    """

    def __init__(self, prefix: str = SPEND_LEDGER_PREFIX):
        self._prefix = prefix
        self._client = None
        self._available = False
        self._connect()

    def _connect(self) -> None:
        try:
            import redis
            url = os.getenv("REDIS_URL")
            if url:
                self._client = redis.from_url(url, decode_responses=True)
            else:
                host = os.getenv("REDIS_HOST", "localhost")
                port = int(os.getenv("REDIS_PORT", "6379"))
                self._client = redis.Redis(host=host, port=port, decode_responses=True)
            self._client.ping()
            self._available = True
            logger.info("Redis spend ledger connected: %s", self._prefix)
        except Exception as e:
            logger.warning("Redis spend ledger unavailable: %s", e)
            self._available = False

    def is_available(self) -> bool:
        if not self._available:
            return False
        try:
            self._client.ping()
            return True
        except Exception:
            self._available = False
            return False

    def _key(self, *parts: str) -> str:
        return ":".join([self._prefix] + list(parts))

    def record_spend(self, account_id: str, amount: float) -> None:
        if not self.is_available():
            return
        try:
            pipe = self._client.pipeline()
            dk = self._key("daily", account_id)
            mk = self._key("monthly", account_id)
            gk = self._key("global", "window")

            pipe.incrbyfloat(dk, amount)
            pipe.expire(dk, 86400)
            pipe.incrbyfloat(mk, amount)
            pipe.expire(mk, 2678400)
            pipe.zadd(gk, {f"{time.time()}:{amount}": time.time()})
            pipe.zremrangebyscore(gk, 0, time.time() - 600)
            pipe.execute()
        except Exception as e:
            logger.warning("Redis record_spend failed: %s", e)
            self._available = False

    def record_tool_calls(self, account_id: str, count: int) -> None:
        if not self.is_available():
            return
        try:
            k = self._key("tools", account_id)
            self._client.incrby(k, count)
            self._client.expire(k, 86400)
        except Exception as e:
            logger.warning("Redis record_tool_calls failed: %s", e)

    def get_daily_spend(self, account_id: str) -> float:
        if not self.is_available():
            return 0.0
        try:
            v = self._client.get(self._key("daily", account_id))
            return float(v) if v else 0.0
        except Exception:
            return 0.0

    def get_monthly_spend(self, account_id: str) -> float:
        if not self.is_available():
            return 0.0
        try:
            v = self._client.get(self._key("monthly", account_id))
            return float(v) if v else 0.0
        except Exception:
            return 0.0

    def get_daily_tool_calls(self, account_id: str) -> int:
        if not self.is_available():
            return 0
        try:
            v = self._client.get(self._key("tools", account_id))
            return int(v) if v else 0
        except Exception:
            return 0

    def acquire_concurrency(self, account_id: str, cap: int) -> bool:
        if not self.is_available():
            return False
        try:
            k = self._key("conc", account_id)
            current = int(self._client.get(k) or 0)
            if current >= cap:
                return False
            self._client.incr(k)
            self._client.expire(k, 300)
            return True
        except Exception:
            return False

    def release_concurrency(self, account_id: str) -> None:
        if not self.is_available():
            return
        try:
            k = self._key("conc", account_id)
            self._client.decr(k)
        except Exception:
            pass

    def global_spend_last_n_minutes(self, minutes: int = 10) -> float:
        if not self.is_available():
            return 0.0
        try:
            gk = self._key("global", "window")
            cutoff = time.time() - (minutes * 60)
            entries = self._client.zrangebyscore(gk, cutoff, "+inf")
            total = 0.0
            for entry in entries:
                parts = str(entry).split(":")
                if len(parts) >= 2:
                    total += float(parts[1])
            return total
        except Exception:
            return 0.0

    def check_rate_limit(self, account_id: str, qps: int, rpm: int) -> bool:
        if not self.is_available():
            return True
        try:
            k = self._key("rate", account_id)
            now = time.time()
            pipe = self._client.pipeline()
            pipe.zremrangebyscore(k, 0, now - 60)
            pipe.zcard(k)
            pipe.zcount(k, now - 1, "+inf")
            results = pipe.execute()
            count_minute = results[1]
            count_second = results[2]
            if count_minute >= rpm or count_second >= qps:
                return False
            self._client.zadd(k, {str(now): now})
            self._client.expire(k, 120)
            return True
        except Exception:
            return True

    def get_status(self) -> Dict[str, Any]:
        available = self.is_available()
        return {
            "backend": "redis",
            "available": available,
            "prefix": self._prefix,
        }


# ---------------------------------------------------------------------------
# Firestore-backed ledger (multi-instance safe)
# ---------------------------------------------------------------------------
class FirestoreLedger(SpendLedger):
    """Firestore-backed spend ledger using atomic increments and transactions.

    Document layout (all names prefixed by SPEND_LEDGER_PREFIX):
      spend_daily/{account}__{day_key}
      spend_monthly/{account}__{month_key}
      tool_daily/{account}__{day_key}
      concurrency/{account}
      global_minute/{minute_epoch}
      rate_minute/{account}__{minute_epoch}
      rate_second/{account}__{second_epoch}
    """

    def __init__(
        self,
        prefix: str = SPEND_LEDGER_PREFIX,
        project_id: str = FIRESTORE_PROJECT_ID,
        client: Optional[Any] = None,
    ):
        self._prefix = prefix
        self._project_id = project_id
        self._client = client
        self._available = False
        self._firestore = None
        self._increment = None
        self._connect()

    def _connect(self) -> None:
        if self._client is not None:
            try:
                from google.cloud import firestore  # type: ignore

                self._firestore = firestore
                self._increment = firestore.Increment
            except Exception:
                self._firestore = None
                self._increment = None
            self._available = True
            return
        try:
            from google.cloud import firestore  # type: ignore

            self._firestore = firestore
            self._increment = firestore.Increment
            kwargs = {}
            if self._project_id:
                kwargs["project"] = self._project_id
            self._client = firestore.Client(**kwargs)
            # A simple existence check that works in Cloud Run with ADC.
            self._client.collections()
            self._available = True
            logger.info("Firestore spend ledger connected: %s", self._prefix)
        except Exception as e:
            logger.warning("Firestore spend ledger unavailable: %s", e)
            self._available = False

    def is_available(self) -> bool:
        return bool(self._available and self._client is not None)

    def _collection(self, name: str):
        return self._client.collection(f"{self._prefix}_{name}")

    @staticmethod
    def _day_key(now: Optional[float] = None) -> str:
        ts = datetime.fromtimestamp(now or time.time(), tz=timezone.utc)
        return ts.strftime("%Y%m%d")

    @staticmethod
    def _month_key(now: Optional[float] = None) -> str:
        ts = datetime.fromtimestamp(now or time.time(), tz=timezone.utc)
        return ts.strftime("%Y%m")

    @staticmethod
    def _minute_bucket(now: Optional[float] = None) -> int:
        return int((now or time.time()) // 60)

    @staticmethod
    def _second_bucket(now: Optional[float] = None) -> int:
        return int(now or time.time())

    def record_spend(self, account_id: str, amount: float) -> None:
        if not self.is_available():
            return
        try:
            now = time.time()
            day_key = self._day_key(now)
            month_key = self._month_key(now)
            minute_bucket = self._minute_bucket(now)
            day_ref = self._collection("spend_daily").document(f"{account_id}__{day_key}")
            month_ref = self._collection("spend_monthly").document(f"{account_id}__{month_key}")
            global_ref = self._collection("global_minute").document(str(minute_bucket))
            batch = self._client.batch()
            payload = {
                "updated_at": now,
                "account_id": account_id,
            }
            batch.set(
                day_ref,
                {**payload, "day_key": day_key, "amount": self._increment(amount)},
                merge=True,
            )
            batch.set(
                month_ref,
                {**payload, "month_key": month_key, "amount": self._increment(amount)},
                merge=True,
            )
            batch.set(
                global_ref,
                {"updated_at": now, "minute_bucket": minute_bucket, "amount": self._increment(amount)},
                merge=True,
            )
            batch.commit()
        except Exception as e:
            logger.warning("Firestore record_spend failed: %s", e)
            self._available = False

    def record_tool_calls(self, account_id: str, count: int) -> None:
        if not self.is_available():
            return
        try:
            now = time.time()
            day_key = self._day_key(now)
            ref = self._collection("tool_daily").document(f"{account_id}__{day_key}")
            ref.set(
                {
                    "updated_at": now,
                    "account_id": account_id,
                    "day_key": day_key,
                    "count": self._increment(count),
                },
                merge=True,
            )
        except Exception as e:
            logger.warning("Firestore record_tool_calls failed: %s", e)
            self._available = False

    def get_daily_spend(self, account_id: str) -> float:
        if not self.is_available():
            return 0.0
        try:
            doc = self._collection("spend_daily").document(
                f"{account_id}__{self._day_key()}"
            ).get()
            if not doc.exists:
                return 0.0
            return float((doc.to_dict() or {}).get("amount", 0.0))
        except Exception:
            return 0.0

    def get_monthly_spend(self, account_id: str) -> float:
        if not self.is_available():
            return 0.0
        try:
            doc = self._collection("spend_monthly").document(
                f"{account_id}__{self._month_key()}"
            ).get()
            if not doc.exists:
                return 0.0
            return float((doc.to_dict() or {}).get("amount", 0.0))
        except Exception:
            return 0.0

    def get_daily_tool_calls(self, account_id: str) -> int:
        if not self.is_available():
            return 0
        try:
            doc = self._collection("tool_daily").document(
                f"{account_id}__{self._day_key()}"
            ).get()
            if not doc.exists:
                return 0
            return int((doc.to_dict() or {}).get("count", 0))
        except Exception:
            return 0

    def acquire_concurrency(self, account_id: str, cap: int) -> bool:
        if not self.is_available():
            return False
        try:
            ref = self._collection("concurrency").document(account_id)
            transaction = self._client.transaction()

            @self._firestore.transactional
            def _txn(txn):
                snap = ref.get(transaction=txn)
                current = int((snap.to_dict() or {}).get("count", 0)) if snap.exists else 0
                if current >= cap:
                    return False
                txn.set(ref, {"count": current + 1, "updated_at": time.time()}, merge=True)
                return True

            return bool(_txn(transaction))
        except Exception as e:
            logger.warning("Firestore acquire_concurrency failed: %s", e)
            self._available = False
            return False

    def release_concurrency(self, account_id: str) -> None:
        if not self.is_available():
            return
        try:
            ref = self._collection("concurrency").document(account_id)
            transaction = self._client.transaction()

            @self._firestore.transactional
            def _txn(txn):
                snap = ref.get(transaction=txn)
                current = int((snap.to_dict() or {}).get("count", 0)) if snap.exists else 0
                txn.set(ref, {"count": max(0, current - 1), "updated_at": time.time()}, merge=True)

            _txn(transaction)
        except Exception:
            pass

    def global_spend_last_n_minutes(self, minutes: int = 10) -> float:
        if not self.is_available():
            return 0.0
        total = 0.0
        now_bucket = self._minute_bucket()
        try:
            for bucket in range(max(0, now_bucket - minutes + 1), now_bucket + 1):
                snap = self._collection("global_minute").document(str(bucket)).get()
                if snap.exists:
                    total += float((snap.to_dict() or {}).get("amount", 0.0))
            return total
        except Exception:
            return 0.0

    def check_rate_limit(self, account_id: str, qps: int, rpm: int) -> bool:
        if not self.is_available():
            return True
        try:
            now = time.time()
            sec_bucket = self._second_bucket(now)
            minute_bucket = self._minute_bucket(now)
            sec_ref = self._collection("rate_second").document(f"{account_id}__{sec_bucket}")
            minute_ref = self._collection("rate_minute").document(f"{account_id}__{minute_bucket}")
            transaction = self._client.transaction()

            @self._firestore.transactional
            def _txn(txn):
                sec_snap = sec_ref.get(transaction=txn)
                min_snap = minute_ref.get(transaction=txn)
                sec_count = int((sec_snap.to_dict() or {}).get("count", 0)) if sec_snap.exists else 0
                min_count = int((min_snap.to_dict() or {}).get("count", 0)) if min_snap.exists else 0
                if sec_count >= qps or min_count >= rpm:
                    return False
                txn.set(sec_ref, {"count": sec_count + 1, "updated_at": now}, merge=True)
                txn.set(minute_ref, {"count": min_count + 1, "updated_at": now}, merge=True)
                return True

            return bool(_txn(transaction))
        except Exception:
            # Rate limiter should not fail open for paid flows; the enclosing governor
            # will fail-closed if the backend becomes unavailable.
            self._available = False
            return True

    def get_status(self) -> Dict[str, Any]:
        return {
            "backend": "firestore",
            "available": self.is_available(),
            "project_id": self._project_id or "default",
            "prefix": self._prefix,
        }


# ---------------------------------------------------------------------------
# Ledger factory
# ---------------------------------------------------------------------------
def _create_ledger() -> SpendLedger:
    if SPEND_LEDGER_BACKEND == "firestore":
        ledger = FirestoreLedger(prefix=SPEND_LEDGER_PREFIX, project_id=FIRESTORE_PROJECT_ID)
        if not ledger.is_available():
            logger.warning(
                "SPEND_LEDGER_BACKEND=firestore but Firestore unavailable. "
                "Governor will FAIL CLOSED for paid escalation."
            )
        return ledger
    if SPEND_LEDGER_BACKEND == "redis":
        ledger = RedisLedger(prefix=SPEND_LEDGER_PREFIX)
        if not ledger.is_available():
            logger.warning(
                "SPEND_LEDGER_BACKEND=redis but Redis unavailable. "
                "Governor will FAIL CLOSED for paid escalation."
            )
        return ledger
    return InMemoryLedger()


_ledger = _create_ledger()


# ---------------------------------------------------------------------------
# Governor
# ---------------------------------------------------------------------------
class TierSpendGovernor:
    """Stateless decision engine backed by the configured SpendLedger."""

    def __init__(self, ledger: Optional[SpendLedger] = None):
        self._ledger = ledger or _ledger

    def evaluate(
        self,
        tier: str,
        account_id: str,
        predicted_cost_usd: float,
        tool_calls_requested: int = 0,
        is_internal: bool = False,
    ) -> SpendDecision:
        """Produce an auditable SpendDecision for this request."""

        if tier == "free":
            return self._evaluate_free(account_id, predicted_cost_usd,
                                       tool_calls_requested)

        return self._evaluate_elite_plus(
            account_id, predicted_cost_usd, tool_calls_requested, is_internal
        )

    def _evaluate_free(
        self,
        account_id: str,
        predicted_cost_usd: float,
        tool_calls_requested: int,
    ) -> SpendDecision:
        tool_day = self._ledger.get_daily_tool_calls(account_id)
        tool_remaining = max(0, FREE_TIER_MAX_TOOL_CALLS_DAY - tool_day)
        tool_req_remaining = FREE_TIER_MAX_TOOL_CALLS_REQUEST

        blocked_reason = ""
        if predicted_cost_usd > FREE_TIER_MAX_COST_USD_REQUEST:
            blocked_reason = (
                f"free_tier_cost_exceeded: predicted=${predicted_cost_usd:.4f} "
                f"> max=${FREE_TIER_MAX_COST_USD_REQUEST:.4f}"
            )
        if tool_calls_requested > FREE_TIER_MAX_TOOL_CALLS_REQUEST:
            blocked_reason += (
                f"; free_tier_tool_cap: {tool_calls_requested} "
                f"> {FREE_TIER_MAX_TOOL_CALLS_REQUEST}/request"
            )
        if tool_day >= FREE_TIER_MAX_TOOL_CALLS_DAY:
            blocked_reason += (
                f"; free_tier_daily_tool_cap: {tool_day} "
                f">= {FREE_TIER_MAX_TOOL_CALLS_DAY}/day"
            )

        rate_ok = self._ledger.check_rate_limit(
            account_id, ACCOUNT_QPS_LIMIT, ACCOUNT_RPM_LIMIT
        )

        return SpendDecision(
            tier="free",
            account_id=account_id,
            predicted_cost_usd=predicted_cost_usd,
            allowed_paid_escalation=False,
            reason_blocked=blocked_reason.strip("; ") if blocked_reason else "free_tier_no_paid",
            spend_remaining_day=0.0,
            spend_remaining_month=0.0,
            tool_calls_remaining_request=min(tool_req_remaining, tool_remaining),
            global_breaker_active=False,
            is_internal_override=False,
            ledger_backend=SPEND_LEDGER_BACKEND,
            rate_limited=not rate_ok,
        )

    def _evaluate_elite_plus(
        self,
        account_id: str,
        predicted_cost_usd: float,
        tool_calls_requested: int,
        is_internal: bool,
    ) -> SpendDecision:
        # Fail-closed: if a multi-instance backend is configured but unavailable.
        if SPEND_LEDGER_BACKEND in {"redis", "firestore"} and not self._ledger.is_available():
            logger.warning("%s unavailable — FAIL CLOSED for paid escalation", SPEND_LEDGER_BACKEND)
            return SpendDecision(
                tier="elite+",
                account_id=account_id,
                predicted_cost_usd=predicted_cost_usd,
                allowed_paid_escalation=False,
                reason_blocked="ledger_unavailable_fail_closed",
                spend_remaining_day=0.0,
                spend_remaining_month=0.0,
                global_breaker_active=True,
                is_internal_override=is_internal,
                ledger_backend=f"{SPEND_LEDGER_BACKEND}_unavailable",
                rate_limited=False,
            )

        daily = self._ledger.get_daily_spend(account_id)
        monthly = self._ledger.get_monthly_spend(account_id)
        global_10 = self._ledger.global_spend_last_n_minutes(10)

        remain_day = max(0.0, ELITE_PLUS_ACCOUNT_DAILY_BUDGET_USD - daily)
        remain_month = max(0.0, ELITE_PLUS_ACCOUNT_MONTHLY_BUDGET_USD - monthly)

        global_breaker = global_10 >= GLOBAL_PAID_ESCALATION_BUDGET_USD_10MIN

        blocked_reason = ""
        allowed = True

        if global_breaker and not is_internal:
            allowed = False
            blocked_reason = (
                f"global_breaker: 10min_spend=${global_10:.2f} "
                f">= threshold=${GLOBAL_PAID_ESCALATION_BUDGET_USD_10MIN:.2f}"
            )

        if predicted_cost_usd > ELITE_PLUS_MAX_COST_USD_REQUEST and not is_internal:
            allowed = False
            blocked_reason += (
                f"; request_ceiling: predicted=${predicted_cost_usd:.4f} "
                f"> max=${ELITE_PLUS_MAX_COST_USD_REQUEST:.4f}"
            )

        if predicted_cost_usd > remain_day and not is_internal:
            allowed = False
            blocked_reason += (
                f"; daily_budget: predicted=${predicted_cost_usd:.4f} "
                f"> remaining=${remain_day:.4f}"
            )

        if predicted_cost_usd > remain_month and not is_internal:
            allowed = False
            blocked_reason += (
                f"; monthly_budget: predicted=${predicted_cost_usd:.4f} "
                f"> remaining=${remain_month:.4f}"
            )

        rate_ok = self._ledger.check_rate_limit(
            account_id, ACCOUNT_QPS_LIMIT, ACCOUNT_RPM_LIMIT
        )

        return SpendDecision(
            tier="elite+",
            account_id=account_id,
            predicted_cost_usd=predicted_cost_usd,
            allowed_paid_escalation=allowed,
            reason_blocked=blocked_reason.strip("; ") if blocked_reason else "",
            spend_remaining_day=remain_day,
            spend_remaining_month=remain_month,
            tool_calls_remaining_request=FREE_TIER_MAX_TOOL_CALLS_REQUEST * 3,
            global_breaker_active=global_breaker,
            is_internal_override=is_internal,
            ledger_backend=SPEND_LEDGER_BACKEND,
            rate_limited=not rate_ok,
        )

    def record(
        self,
        account_id: str,
        actual_cost_usd: float,
        tool_calls_used: int = 0,
    ) -> None:
        if actual_cost_usd > 0:
            self._ledger.record_spend(account_id, actual_cost_usd)
        if tool_calls_used > 0:
            self._ledger.record_tool_calls(account_id, tool_calls_used)

    def acquire_concurrency(self, account_id: str) -> bool:
        return self._ledger.acquire_concurrency(
            account_id, ELITE_PLUS_ACCOUNT_CONCURRENCY_CAP
        )

    def release_concurrency(self, account_id: str) -> None:
        self._ledger.release_concurrency(account_id)

    def get_ledger_status(self) -> Dict[str, Any]:
        return self._ledger.get_status()


# Module-level singleton
governor = TierSpendGovernor()
