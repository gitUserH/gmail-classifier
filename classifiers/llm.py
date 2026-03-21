"""LLM分類器（将来用スケルトン）"""

import requests
from classifiers.base import BaseClassifier
from gmail_client import Email


class LLMClassifier(BaseClassifier):
    def __init__(self, categories: dict, endpoint: str, model: str):
        self.categories = categories
        self.endpoint = endpoint
        self.model = model
        self._category_names = [name for name in categories if name != "Personal"]

    def classify(self, email: Email) -> str:
        """Ollama APIを使ってメールを分類する。"""
        prompt = self._build_prompt(email)

        resp = requests.post(
            self.endpoint,
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
            },
            timeout=30,
        )
        resp.raise_for_status()
        answer = resp.json().get("response", "").strip()

        # レスポンスからカテゴリ名を抽出
        for name in self._category_names:
            if name.lower() in answer.lower():
                return name
        return "Personal"

    def _build_prompt(self, email: Email) -> str:
        categories_str = ", ".join(self._category_names)
        return (
            f"以下のメールを次のカテゴリのいずれかに分類してください: {categories_str}\n"
            f"該当しない場合は Personal と回答してください。\n"
            f"カテゴリ名のみを回答してください。\n\n"
            f"From: {email.from_address}\n"
            f"Subject: {email.subject}\n"
            f"Body: {email.snippet}\n\n"
            f"カテゴリ:"
        )
