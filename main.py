"""Gmail メール自動分類ツール"""

import argparse
import os
import time
import yaml

from auth import get_credentials
from gmail_client import GmailClient, Email
from classifiers.base import BaseClassifier
from classifiers.rule_based import RuleBasedClassifier

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.yaml")


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def create_classifier(config: dict) -> BaseClassifier:
    categories = config["categories"]
    classifier_type = config.get("classifier", "rule_based")

    if classifier_type == "llm":
        from classifiers.llm import LLMClassifier

        llm_cfg = config.get("llm", {})
        return LLMClassifier(
            categories=categories,
            endpoint=llm_cfg.get("endpoint", "http://localhost:11434/api/generate"),
            model=llm_cfg.get("model", "llama3"),
        )
    return RuleBasedClassifier(categories=categories)


def classify_messages(
    client: GmailClient,
    classifier: BaseClassifier,
    messages: list[Email],
    dry_run: bool = False,
    spam_senders: set[str] | None = None,
) -> dict[str, int]:
    """メールを分類してラベルを付与する。分類結果の集計を返す。"""
    stats: dict[str, int] = {}
    label_id_cache: dict[str, str] = {}
    has_spam_check = hasattr(classifier, "is_spam")

    for email in messages:
        subject_safe = email.subject[:60].encode("cp932", errors="replace").decode("cp932")

        # 1. 迷惑メール送信者の完全一致 + LLM内容確認
        if spam_senders and email.from_address.lower() in spam_senders:
            # LLMでも内容を確認し、正規メールなら通常分類に回す
            if not has_spam_check or classifier.is_spam(email):
                category = "[SPAM:送信者]"
                stats[category] = stats.get(category, 0) + 1
                print(f"  [{category:12s}] {subject_safe}")
                if not dry_run:
                    client.move_to_spam(email.id)
                continue

        # 2. LLMによる内容ベースのスパム判定
        if has_spam_check and classifier.is_spam(email):
            category = "[SPAM:内容]"
            stats[category] = stats.get(category, 0) + 1
            print(f"  [{category:12s}] {subject_safe}")
            if not dry_run:
                client.move_to_spam(email.id)
            continue

        # 3. 通常のサービス名分類
        category = classifier.classify(email)
        stats[category] = stats.get(category, 0) + 1
        print(f"  [{category:12s}] {subject_safe}")

        if not dry_run:
            if category not in label_id_cache:
                label_id_cache[category] = client.ensure_label(category)
            client.apply_label(email.id, label_id_cache[category])

    return stats


def cmd_classify(args: argparse.Namespace) -> None:
    """既存メールを一括分類する。"""
    config = load_config()
    creds = get_credentials()
    client = GmailClient(creds)
    classifier = create_classifier(config)

    print("迷惑メール送信者リストを取得中...")
    spam_senders = client.fetch_spam_senders()
    print(f"  {len(spam_senders)} 件のスパム送信者を検出\n")

    print(f"メールを取得中... (最大 {args.limit} 件)")
    messages = client.fetch_messages(max_results=args.limit)
    print(f"{len(messages)} 件のメールを取得しました。\n")

    if not messages:
        print("分類するメールがありません。")
        return

    if args.dry_run:
        print("=== ドライラン（ラベル付与なし） ===\n")
    else:
        print("=== メール分類中 ===\n")

    stats = classify_messages(client, classifier, messages, dry_run=args.dry_run, spam_senders=spam_senders)

    print(f"\n--- 分類結果 ---")
    for category, count in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"  {category}: {count} 件")
    print(f"  合計: {sum(stats.values())} 件")

    if args.dry_run:
        print("\n(ドライランのため、ラベルは付与されていません)")


def cmd_watch(args: argparse.Namespace) -> None:
    """新着メールを定期チェックして分類する。"""
    config = load_config()
    interval = config.get("watch_interval", 300)
    creds = get_credentials()
    client = GmailClient(creds)
    classifier = create_classifier(config)

    print("迷惑メール送信者リストを取得中...")
    spam_senders = client.fetch_spam_senders()
    print(f"  {len(spam_senders)} 件のスパム送信者を検出\n")

    print(f"新着メール監視を開始します（間隔: {interval}秒）")
    print("Ctrl+C で停止\n")

    # 最新メールのhistoryIdを記録
    last_check_query = "newer_than:1m"

    try:
        while True:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] チェック中...")
            messages = client.fetch_messages(query=last_check_query, max_results=50)

            if messages:
                print(f"  {len(messages)} 件の新着メール:")
                if args.dry_run:
                    classify_messages(client, classifier, messages, dry_run=True, spam_senders=spam_senders)
                else:
                    classify_messages(client, classifier, messages, dry_run=False, spam_senders=spam_senders)
            else:
                print("  新着メールなし")

            # 次回は直近の間隔分だけチェック
            minutes = max(1, interval // 60)
            last_check_query = f"newer_than:{minutes}m"

            print(f"  次回チェック: {interval}秒後\n")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n監視を停止しました。")


def main() -> None:
    parser = argparse.ArgumentParser(description="Gmail メール自動分類ツール")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # classify コマンド
    p_classify = subparsers.add_parser("classify", help="既存メールを一括分類")
    p_classify.add_argument("--dry-run", action="store_true", help="分類結果の表示のみ（ラベル付与しない）")
    p_classify.add_argument("--limit", type=int, default=100, help="処理するメール数（デフォルト: 100）")

    # watch コマンド
    p_watch = subparsers.add_parser("watch", help="新着メールを定期チェックして分類")
    p_watch.add_argument("--dry-run", action="store_true", help="分類結果の表示のみ（ラベル付与しない）")

    args = parser.parse_args()

    if args.command == "classify":
        cmd_classify(args)
    elif args.command == "watch":
        cmd_watch(args)


if __name__ == "__main__":
    main()
