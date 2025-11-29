"""Lightweight fact-checking helpers for orchestrated answers."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Sequence

from .services.web_research import WebDocument, WebResearchClient


@dataclass(slots=True)
class FactCheckClaim:
    """Represents a single factual claim extracted from an answer."""

    text: str
    status: str  # "verified", "contested", "unknown"
    evidence_urls: List[str]


@dataclass(slots=True)
class FactCheckResult:
    """Aggregated fact-check results for an answer."""

    claims: List[FactCheckClaim]
    # Loop-back refinement: Additional metadata for loop-back logic
    verification_score: float = 0.0  # Overall verification score (0.0-1.0)
    failed_claims: List[FactCheckClaim] = field(default_factory=list)  # Claims that failed verification
    is_valid: bool = True  # Whether the answer passed verification

    def __post_init__(self):
        """Loop-back refinement: Calculate verification score and identify failed claims."""
        
        if not self.claims:
            self.verification_score = 1.0  # No claims to verify = perfect score
            self.is_valid = True
            return
        
        # Loop-back refinement: Calculate verification score
        total_claims = len(self.claims)
        verified = self.verified_count
        contested = self.contested_count
        
        # Score: verified claims get full weight, contested get negative weight
        self.verification_score = (verified - contested * 0.5) / max(total_claims, 1)
        self.verification_score = max(0.0, min(1.0, self.verification_score))
        
        # Loop-back refinement: Identify failed claims (contested or unknown)
        self.failed_claims = [
            claim for claim in self.claims
            if claim.status in ("contested", "unknown")
        ]
        
        # Loop-back refinement: Answer is valid if score >= 0.6 and no contested claims
        self.is_valid = (
            self.verification_score >= 0.6 and
            contested == 0
        )

    @property
    def verified_count(self) -> int:
        return sum(1 for c in self.claims if c.status == "verified")

    @property
    def contested_count(self) -> int:
        return sum(1 for c in self.claims if c.status == "contested")
    
    @property
    def unknown_count(self) -> int:
        """Loop-back refinement: Count of claims with unknown status."""
        return sum(1 for c in self.claims if c.status == "unknown")


class FactChecker:
    """Best-effort fact checker using the existing web research client.

    This implementation is intentionally heuristic and conservative; it is
    designed to provide helpful metadata rather than block responses.
    """

    def __init__(self, client: WebResearchClient) -> None:
        self.client = client

    async def check_answer(
        self,
        answer: str,
        *,
        prompt: str,
        web_documents: Sequence[WebDocument] | None = None,
    ) -> FactCheckResult:
        """Extract a few candidate claims and look for corroboration.
        
        Parallel Retrieval: Uses pre-retrieved evidence documents if available,
        falling back to fresh search only if no documents provided.
        """

        web_documents = list(web_documents or [])
        claims = self._extract_candidate_claims(answer)
        results: List[FactCheckClaim] = []

        if not claims:
            return FactCheckResult(claims=[])

        # Parallel Retrieval: Use pre-retrieved evidence if available
        if not web_documents:
            # Fall back to a fresh search using the original prompt.
            # This should rarely happen if parallel retrieval is working.
            try:
                web_documents = await self.client.search(prompt)
            except Exception:  # pragma: no cover - defensive
                web_documents = []

        urls = [doc.url for doc in web_documents if doc.url]
        for claim in claims:
            status = "unknown"
            evidence_urls: List[str] = []
            lowered = claim.lower()
            for doc in web_documents:
                snippet = (doc.snippet or "").lower()
                title = (doc.title or "").lower()
                if lowered and lowered.split(" ", 1)[0] in snippet or lowered in snippet:
                    status = "verified"
                    if doc.url:
                        evidence_urls.append(doc.url)
                elif lowered and lowered.split(" ", 1)[0] in title:
                    status = status or "verified"
                    if doc.url:
                        evidence_urls.append(doc.url)
            results.append(
                FactCheckClaim(
                    text=claim,
                    status=status,
                    evidence_urls=evidence_urls or urls[:2],
                )
            )
        return FactCheckResult(claims=results)

    def _extract_candidate_claims(self, answer: str, *, limit: int = 4) -> List[str]:
        """Naively split the answer into a few candidate 'claims'."""

        sentences = [
            s.strip()
            for s in answer.replace("\n", " ").split(".")
            if s.strip() and len(s.strip().split()) > 4
        ]
        return sentences[:limit]


