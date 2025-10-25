class Validator:
    def check_for_pii(self, text: str) -> bool:
        if "email is" in text or "phone is" in text:
            print("Warning: Potential PII detected.")
            return True
        return False

    def check_content_policy(self, text: str) -> bool:
        banned_phrases = ["illicit", "harmful"]
        if any(phrase in text for phrase in banned_phrases):
            print("Warning: Content policy violation detected.")
            return True
        return False