from __future__ import annotations

import logging


logger = logging.getLogger(__name__)


class Validator:
    def check_for_pii(self, text: str) -> bool:
        if "email is" in text or "phone is" in text:
            logger.warning("Potential PII detected in generated content.")
            return True
        return False

    def check_content_policy(self, text: str) -> bool:
        banned_phrases = ["illicit", "harmful"]
        if any(phrase in text for phrase in banned_phrases):
            logger.warning("Content policy violation detected in generated content.")
            return True
        return False