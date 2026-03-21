"""ルールベース分類器"""

from classifiers.base import BaseClassifier
from gmail_client import Email


class RuleBasedClassifier(BaseClassifier):
    def __init__(self, categories: dict):
        self.categories = categories

    def classify(self, email: Email) -> str:
        """ドメインマッチ → キーワードマッチの順で判定し、カテゴリ名を返す。"""
        from_domain = self._extract_domain(email.from_address)

        # 1. ドメインマッチ（Personal以外）
        for category, rules in self.categories.items():
            if category == "Personal":
                continue
            for domain in rules.get("domains", []):
                if from_domain.endswith(domain):
                    return category

        # 2. 件名キーワードマッチ
        subject_lower = email.subject.lower()
        for category, rules in self.categories.items():
            if category == "Personal":
                continue
            for keyword in rules.get("keywords_subject", []):
                if keyword.lower() in subject_lower:
                    return category

        # 3. 本文（スニペット）キーワードマッチ
        snippet_lower = email.snippet.lower()
        for category, rules in self.categories.items():
            if category == "Personal":
                continue
            for keyword in rules.get("keywords_body", []):
                if keyword.lower() in snippet_lower:
                    return category

        # 4. どれにもマッチしなければ Personal
        return "Personal"

    @staticmethod
    def _extract_domain(email_address: str) -> str:
        """メールアドレスからドメイン部分を抽出する。"""
        if "@" in email_address:
            return email_address.split("@", 1)[1].lower()
        return email_address.lower()
