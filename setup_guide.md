# Gmail Classifier セットアップガイド

## 1. Google Cloud プロジェクトの作成

1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. 画面上部のプロジェクト選択 → 「新しいプロジェクト」をクリック
3. プロジェクト名（例: `gmail-classifier`）を入力して「作成」

## 2. Gmail API の有効化

1. 左メニュー「APIとサービス」→「ライブラリ」
2. 「Gmail API」を検索してクリック
3. 「有効にする」をクリック

## 3. OAuth 同意画面の設定

1. 左メニュー「APIとサービス」→「OAuth 同意画面」
2. User Type: 「外部」を選択して「作成」
3. 以下を入力:
   - アプリ名: `Gmail Classifier`
   - ユーザーサポートメール: 自分のメールアドレス
   - デベロッパーの連絡先: 自分のメールアドレス
4. 「保存して次へ」
5. スコープの追加 → `https://www.googleapis.com/auth/gmail.modify` を追加
6. 「保存して次へ」
7. テストユーザーに自分のGmailアドレスを追加
8. 「保存して次へ」

## 4. OAuth クライアントID の作成

1. 左メニュー「APIとサービス」→「認証情報」
2. 「認証情報を作成」→「OAuth クライアント ID」
3. アプリケーションの種類: 「デスクトップアプリ」
4. 名前: `Gmail Classifier`（任意）
5. 「作成」をクリック
6. 表示されるダイアログで「JSONをダウンロード」をクリック

## 5. credentials.json の配置

ダウンロードしたJSONファイルを `credentials.json` にリネームして、このプロジェクトのルートディレクトリに配置してください。

```
gmail-classifier/
├── credentials.json  ← ここに配置
├── main.py
└── ...
```

## 6. 依存ライブラリのインストール

```bash
pip install -r requirements.txt
```

## 7. 動作確認

```bash
# ドライランで分類結果を確認（ラベル付与なし）
python main.py classify --dry-run --limit 10

# 実際にラベルを付与
python main.py classify --limit 10

# 新着メール監視
python main.py watch
```

初回実行時にブラウザが開き、Googleアカウントの認証を求められます。認証後、`token.json` が自動生成されます。

## 注意事項

- `credentials.json` と `token.json` は秘密情報です。Gitにコミットしないでください。
- テストユーザーとして登録したアカウントでのみ動作します（本番公開しない場合）。
- OAuth同意画面が「テスト」モードの場合、トークンは7日で期限切れになります。再度認証が必要になった場合は `token.json` を削除して再実行してください。
