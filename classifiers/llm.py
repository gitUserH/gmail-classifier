"""LLM分類器（サービス名抽出方式）"""

import re
import requests
from classifiers.base import BaseClassifier
from gmail_client import Email


class LLMClassifier(BaseClassifier):
    def __init__(self, categories: dict, endpoint: str, model: str):
        self.categories = categories
        self.endpoint = endpoint
        self.model = model

    def classify(self, email: Email) -> str:
        """Ollama APIを使って送信元のサービス名/ブランド名を抽出する。"""
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

        # 最初の1行だけ取得し、余計な記号を除去
        label = answer.split("\n")[0].strip()
        label = re.sub(r"[\"'`\.\,\!]", "", label).strip()

        # 長すぎる回答はLLMが説明文を返したケースなのでOther扱い
        if not label or len(label) > 20:
            return "Other"
        return label

    def _build_prompt(self, email: Email) -> str:
        return (
            "以下のメールの送信元のサービス名またはブランド名を短く抽出してください。\n"
            "ルール:\n"
            "- 正式なサービス名やブランド名を短く返してください（例: 楽天証券, JCB, Ponta, Amazon）\n"
            "- 余計な説明は不要です。名前だけを1つ返してください。\n"
            "- 判別できない場合は「Other」と返してください。\n"
            "- 必ず20文字以内で回答してください。\n\n"
            f"From: {email.from_address}\n"
            f"Subject: {email.subject}\n"
            f"Snippet: {email.snippet}\n\n"
            "サービス名:"
        )
