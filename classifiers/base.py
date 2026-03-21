"""分類器の基底クラス"""

from abc import ABC, abstractmethod
from gmail_client import Email


class BaseClassifier(ABC):
    @abstractmethod
    def classify(self, email: Email) -> str:
        """メールを分類してカテゴリ名（ラベル名）を返す。"""
        ...
