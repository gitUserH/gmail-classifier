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
            timeout=60,
        )
        resp.raise_for_status()
        answer = resp.json().get("response", "").strip()

        # 最初の1行だけ取得し、余計な記号・スペースを正規化
        label = answer.split("\n")[0].strip()
        label = re.sub(r"[\"'`\.\,\!]", "", label).strip()
        label = re.sub(r"\s+", " ", label).strip()

        # 長すぎる回答はLLMが説明文を返したケースなのでOther扱い
        if not label or len(label) > 20:
            return "Other"
        # 先頭大文字に統一（note → Note, amazon → Amazon）
        return label[0].upper() + label[1:] if label[0].isascii() else label

    def is_spam(self, email: Email) -> bool:
        """LLMでメールの内容を分析し、迷惑メールかどうか判定する。"""
        prompt = self._build_spam_prompt(email)

        try:
            resp = requests.post(
                self.endpoint,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=60,
            )
            resp.raise_for_status()
            answer = resp.json().get("response", "").strip().lower()
            return answer.startswith("yes")
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            return False

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

    def _build_spam_prompt(self, email: Email) -> str:
        return (
            "以下のメールが明らかな迷惑メール（スパム）かどうか判定してください。\n"
            "迷惑メールと判定するのは以下のケースのみです:\n"
            "- 身に覚えのない当選通知、高額報酬・副業の案内\n"
            "- フィッシング詐欺（偽のログインページへの誘導など）\n"
            "- 架空請求、脅迫的な内容\n"
            "- 出会い系、アダルト関連の勧誘\n"
            "- 不自然な日本語、明らかな機械翻訳による詐欺メール\n\n"
            "以下は迷惑メールではありません（NOと判定してください）:\n"
            "- 企業やサービスからの正規のメルマガ、セール案内、キャンペーン通知\n"
            "- 予約確認、注文確認、配送通知など自分が利用したサービスからの通知\n"
            "- 病院、クリニック、行政機関からの連絡\n"
            "- 求人情報、ニュースレター\n"
            "- 迷うならNOと判定してください\n\n"
            f"From: {email.from_address}\n"
            f"Subject: {email.subject}\n"
            f"Body: {email.snippet}\n\n"
            "迷惑メールですか？ YES または NO のみで回答してください。\n"
            "回答:"
        )
