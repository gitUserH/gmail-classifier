"""Gmail APIラッパー（メール取得・ラベル操作）"""

import base64
import re
from dataclasses import dataclass
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials


@dataclass
class Email:
    id: str
    from_address: str
    subject: str
    snippet: str
    label_ids: list[str]


class GmailClient:
    def __init__(self, creds: Credentials):
        self.service = build("gmail", "v1", credentials=creds)
        self._label_cache: dict[str, str] | None = None

    def fetch_messages(self, query: str = "", max_results: int = 100) -> list[Email]:
        """メール一覧を取得する（ページネーション対応）。"""
        messages = []
        page_token = None

        while len(messages) < max_results:
            batch_size = min(max_results - len(messages), 100)
            result = (
                self.service.users()
                .messages()
                .list(
                    userId="me",
                    q=query,
                    maxResults=batch_size,
                    pageToken=page_token,
                )
                .execute()
            )

            msg_refs = result.get("messages", [])
            if not msg_refs:
                break

            for ref in msg_refs:
                email = self._get_message_detail(ref["id"])
                if email:
                    messages.append(email)

            page_token = result.get("nextPageToken")
            if not page_token:
                break

        return messages

    def _get_message_detail(self, msg_id: str) -> Email | None:
        """メール詳細を取得する。"""
        msg = (
            self.service.users()
            .messages()
            .get(userId="me", id=msg_id, format="metadata", metadataHeaders=["From", "Subject"])
            .execute()
        )

        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        from_raw = headers.get("From", "")
        # "Name <email@example.com>" からメールアドレス部分を抽出
        match = re.search(r"<(.+?)>", from_raw)
        from_address = match.group(1) if match else from_raw

        return Email(
            id=msg_id,
            from_address=from_address,
            subject=headers.get("Subject", ""),
            snippet=msg.get("snippet", ""),
            label_ids=msg.get("labelIds", []),
        )

    def get_labels(self) -> dict[str, str]:
        """ラベル一覧を取得する。{ラベル名: ラベルID} の辞書を返す。"""
        if self._label_cache is not None:
            return self._label_cache

        result = self.service.users().labels().list(userId="me").execute()
        labels = result.get("labels", [])
        self._label_cache = {label["name"]: label["id"] for label in labels}
        return self._label_cache

    def ensure_label(self, label_name: str) -> str:
        """ラベルが存在しなければ作成し、ラベルIDを返す。"""
        labels = self.get_labels()
        # 大文字小文字を無視して既存ラベルを検索
        for existing_name, label_id in labels.items():
            if existing_name.lower() == label_name.lower():
                return label_id

        body = {
            "name": label_name,
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show",
        }
        result = self.service.users().labels().create(userId="me", body=body).execute()
        # キャッシュを更新
        self._label_cache = None
        return result["id"]

    def apply_label(self, msg_id: str, label_id: str) -> None:
        """メールにラベルを付与する。"""
        self.service.users().messages().modify(
            userId="me",
            id=msg_id,
            body={"addLabelIds": [label_id]},
        ).execute()

    def fetch_spam_senders(self, max_results: int = 500) -> set[str]:
        """迷惑メールフォルダの送信者アドレス一覧を取得する。"""
        senders: set[str] = set()
        page_token = None

        while len(senders) < max_results:
            batch_size = min(max_results - len(senders), 100)
            result = (
                self.service.users()
                .messages()
                .list(
                    userId="me",
                    labelIds=["SPAM"],
                    maxResults=batch_size,
                    pageToken=page_token,
                )
                .execute()
            )

            msg_refs = result.get("messages", [])
            if not msg_refs:
                break

            for ref in msg_refs:
                email = self._get_message_detail(ref["id"])
                if email:
                    senders.add(email.from_address.lower())

            page_token = result.get("nextPageToken")
            if not page_token:
                break

        return senders

    def move_to_spam(self, msg_id: str) -> None:
        """メールを迷惑メールフォルダに移動する。"""
        self.service.users().messages().modify(
            userId="me",
            id=msg_id,
            body={"addLabelIds": ["SPAM"], "removeLabelIds": ["INBOX"]},
        ).execute()
