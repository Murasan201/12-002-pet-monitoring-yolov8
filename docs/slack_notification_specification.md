# Slack通知機能 仕様書

## バージョン情報

| 項目 | 内容 |
|------|------|
| バージョン | 1.2.0 |
| 作成日 | 2025-12-20 |
| 最終更新日 | 2025-12-20 |
| ステータス | 実装準備完了 |

---

## 1. 概要

### 1.1 目的

本モジュール（`slack_notifier.py`）は、ペット監視システムで撮影した画像をSlackに通知するための機能を提供する。独立した関数ライブラリとして設計され、メインプログラム（`main.py`）から呼び出して使用する。

### 1.2 機能概要

```
┌─────────────────────────────────────────────────────────────┐
│                    ペット監視システム                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐  │
│  │ カメラ撮影   │ -> │ 画像保存     │ -> │ slack_notifier  │  │
│  │ (3枚)       │    │ (JPEG)      │    │ (本モジュール)   │  │
│  └─────────────┘    └─────────────┘    └────────┬────────┘  │
└────────────────────────────────────────────────┼────────────┘
                                                  │
                                                  ▼
                                         ┌───────────────┐
                                         │   Slack API   │
                                         │ (files_upload │
                                         │     _v2)      │
                                         └───────┬───────┘
                                                  │
                                                  ▼
                                         ┌───────────────┐
                                         │ Slackチャンネル │
                                         │  画像表示      │
                                         └───────────────┘
```

### 1.3 設計方針

| 方針 | 説明 |
|------|------|
| モジュール設計 | 単一ファイル（`slack_notifier.py`）で完結 |
| ライブラリ利用 | `from slack_notifier import ...` で関数をインポート可能 |
| CLI実行 | `python slack_notifier.py --test` で単体テスト可能 |
| 環境変数管理 | トークン等は`.env`ファイルで管理 |

---

## 2. 技術仕様

### 2.1 採用するAPI

**Slack Web API `files_upload_v2`** を使用する。

#### 2.1.1 files_upload_v2 とは

Python SDK（`slack_sdk`）が提供する画像アップロード用の高レベルメソッド。内部で以下の2つのAPIを順次呼び出す：

```
┌────────────────────────────────────────────────────────┐
│              files_upload_v2 の内部動作                 │
├────────────────────────────────────────────────────────┤
│  Step 1: files.getUploadURLExternal                    │
│          → アップロード用の一時URLを取得                 │
│                                                        │
│  Step 2: ファイルをアップロード（HTTP PUT）              │
│          → 一時URLにファイルデータを送信                 │
│                                                        │
│  Step 3: files.completeUploadExternal                  │
│          → アップロード完了をSlackに通知                 │
│          → チャンネルへの投稿を実行                      │
└────────────────────────────────────────────────────────┘
```

#### 2.1.2 旧API（files.upload）との違い

| 項目 | 旧API (files.upload) | 新API (files_upload_v2) |
|------|---------------------|------------------------|
| ステータス | **2025年11月12日廃止予定** | 現行・推奨 |
| 大容量ファイル | 不安定 | 安定 |
| SDK対応 | - | slack_sdk が自動処理 |

> **重要**: 2024年5月16日以降に作成されたSlack Appでは旧APIは使用不可

#### 2.1.3 基本的な使用方法

```python
from slack_sdk import WebClient

client = WebClient(token="xoxb-xxxx")

# 単一ファイルのアップロード
response = client.files_upload_v2(
    channel="C01XXXXXX",           # チャンネルID
    file="path/to/image.jpg",      # ファイルパス
    initial_comment="ペット発見！"  # メッセージ
)

# 複数ファイルのアップロード
response = client.files_upload_v2(
    channel="C01XXXXXX",
    file_uploads=[
        {"file": "image1.jpg", "title": "写真1"},
        {"file": "image2.jpg", "title": "写真2"},
        {"file": "image3.jpg", "title": "写真3"}
    ],
    initial_comment="ペットを3枚撮影しました"
)
```

### 2.2 依存パッケージ

| パッケージ | バージョン | 用途 | インストール |
|-----------|-----------|------|-------------|
| `slack_sdk` | >= 3.27.0 | Slack Web API クライアント | `pip install slack_sdk` |
| `python-dotenv` | >= 1.0.0 | 環境変数の読み込み | `pip install python-dotenv` |

**requirements.txt への追加**:
```
slack_sdk>=3.27.0
python-dotenv>=1.0.0
```

### 2.3 必要なSlack権限（OAuth Scopes）

Bot Token Scopesに以下を追加：

| スコープ | 説明 | 用途 |
|----------|------|------|
| `files:write` | ファイルのアップロード | 画像送信に必須 |
| `chat:write` | メッセージの送信 | テキスト送信・コメント付与 |

---

## 3. モジュール構成

### 3.1 ファイル配置

```
project/
├── slack_notifier.py      # 本モジュール
├── .env                   # 環境変数（トークン等）※gitignore対象
├── .env.example           # 環境変数のテンプレート
├── main.py                # メインプログラム（呼び出し元）
├── camera_tracker.py      # カメラ追跡モジュール
└── captures/              # 撮影画像の保存ディレクトリ
    └── pet_YYYYMMDD_HHMMSS_N.jpg
```

### 3.2 環境変数

#### .env ファイル

```env
# Slack Bot設定
SLACK_BOT_TOKEN=your-slack-bot-token-here
SLACK_CHANNEL=C01XXXXXXXX
```

#### 環境変数の説明

| 変数名 | 必須 | 形式 | 説明 |
|--------|------|------|------|
| `SLACK_BOT_TOKEN` | ✅ | `xoxb-...` | Bot User OAuth Token |
| `SLACK_CHANNEL` | ✅ | `C` + 英数字 | 送信先チャンネルID |

#### チャンネルIDの取得方法

1. Slackでチャンネルを右クリック
2. 「チャンネル詳細を表示」を選択
3. 最下部の「チャンネルID」をコピー（例: `C01AB2CD3EF`）

---

## 4. API仕様

### 4.1 公開関数一覧

| 関数名 | 説明 | 主な用途 |
|--------|------|---------|
| `upload_images()` | 画像ファイルをアップロード | 画像通知 |
| `send_message()` | テキストメッセージを送信 | 状態通知 |
| `validate_config()` | 設定の検証 | 起動時チェック |

### 4.2 関数詳細

#### 4.2.1 `upload_images()`

```python
def upload_images(
    file_paths: list[str],
    channel: str | None = None,
    message: str | None = None
) -> dict:
    """
    画像ファイルをSlackにアップロードする。

    Args:
        file_paths: アップロードする画像ファイルのパスリスト（1〜10枚）
        channel: 送信先チャンネルID（省略時は環境変数SLACK_CHANNELを使用）
        message: 画像と一緒に投稿するメッセージ（省略可）

    Returns:
        dict: 実行結果
            {
                "success": True/False,
                "uploaded_count": int,      # アップロード成功数
                "error": str | None         # エラー時のメッセージ
            }

    Raises:
        FileNotFoundError: 指定ファイルが存在しない場合
        SlackApiError: Slack API呼び出しエラー時
    """
```

**使用例**:
```python
from slack_notifier import upload_images

# 複数画像をアップロード
result = upload_images(
    file_paths=[
        "captures/pet_20251220_120000_1.jpg",
        "captures/pet_20251220_120000_2.jpg",
        "captures/pet_20251220_120000_3.jpg"
    ],
    message="ペットを検出しました！"
)

if result["success"]:
    print(f"{result['uploaded_count']}枚の画像を送信しました")
else:
    print(f"エラー: {result['error']}")
```

#### 4.2.2 `send_message()`

```python
def send_message(
    message: str,
    channel: str | None = None
) -> dict:
    """
    テキストメッセージをSlackに送信する。

    Args:
        message: 送信するメッセージ
        channel: 送信先チャンネルID（省略時は環境変数を使用）

    Returns:
        dict: 実行結果
            {
                "success": True/False,
                "error": str | None
            }
    """
```

**使用例**:
```python
from slack_notifier import send_message

# システム起動通知
result = send_message("ペット監視システムを起動しました")

# スキャン結果通知
result = send_message("定期スキャン完了: ペット未検出")
```

#### 4.2.3 `validate_config()`

```python
def validate_config() -> dict:
    """
    Slack通知に必要な設定を検証する。

    Returns:
        dict: 検証結果
            {
                "valid": True/False,        # すべての設定が有効か
                "token_set": True/False,    # トークンが設定されているか
                "channel_set": True/False,  # チャンネルが設定されているか
                "errors": list[str]         # エラーメッセージのリスト
            }
    """
```

**使用例**:
```python
from slack_notifier import validate_config

# 起動時に設定を検証
config = validate_config()
if not config["valid"]:
    print("Slack設定エラー:")
    for error in config["errors"]:
        print(f"  - {error}")
    exit(1)
```

---

## 5. 実装フロー

### 5.1 画像アップロードの処理フロー

```
upload_images() 呼び出し
        │
        ▼
┌───────────────────┐
│ 1. 設定の読み込み   │  ← .envからトークン・チャンネルID取得
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ 2. ファイル存在確認 │  ← 全ファイルの存在をチェック
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ 3. WebClient初期化 │  ← slack_sdk.WebClient(token=...)
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ 4. files_upload_v2│  ← 画像をSlackにアップロード
│    API呼び出し     │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ 5. 結果を返却      │  ← {"success": True/False, ...}
└───────────────────┘
```

### 5.2 エラー発生時の処理

```python
# エラーハンドリングの実装例
from slack_sdk.errors import SlackApiError

try:
    response = client.files_upload_v2(...)
except SlackApiError as e:
    error_code = e.response["error"]

    if error_code == "invalid_auth":
        # トークンが無効
        return {"success": False, "error": "認証エラー: トークンを確認してください"}

    elif error_code == "channel_not_found":
        # チャンネルIDが不正
        return {"success": False, "error": "チャンネルが見つかりません"}

    elif error_code == "not_in_channel":
        # Botがチャンネルに参加していない
        return {"success": False, "error": "Botをチャンネルに招待してください"}

    else:
        return {"success": False, "error": f"APIエラー: {error_code}"}
```

### 5.3 主なエラーコードと対処法

| エラーコード | 原因 | 対処法 |
|-------------|------|--------|
| `invalid_auth` | トークンが無効または期限切れ | Slack Appでトークンを再発行 |
| `channel_not_found` | チャンネルIDが間違っている | チャンネルIDを再確認 |
| `not_in_channel` | Botがチャンネルに参加していない | `/invite @アプリ名` で招待 |
| `file_not_found` | ファイルパスが間違っている | ファイルの存在を確認 |
| `ratelimited` | API呼び出し頻度が高すぎる | 呼び出し間隔を空ける |

---

## 6. 事前準備（ユーザーが取得する情報）

本機能を利用するにあたり、ユーザーが事前に準備・取得する必要がある情報をまとめる。

### 6.1 料金プランについて

**Slack APIは無料プランで利用可能**。追加料金は発生しない。

#### 無料プラン（フリープラン）の制限

| 項目 | 制限 | 本システムへの影響 |
|------|------|-------------------|
| ファイルストレージ | 5GB（ワークスペース全体） | 画像は圧縮済み（数百KB/枚）のため当面問題なし |
| メッセージ・ファイル履歴 | 90日間 | 古い通知は閲覧不可になるが運用上許容範囲 |
| 連携アプリ数 | 10個まで | 本システムは1つのみ使用 |

> **結論**: 入門・学習用途では無料プランで十分。有料プランへのアップグレードは不要。

### 6.2 事前に必要なもの

#### 必須項目

| # | 項目 | 説明 | 取得方法 |
|---|------|------|---------|
| 1 | **Slackアカウント** | Slackにログインするためのアカウント | [slack.com](https://slack.com/) で作成 |
| 2 | **Slackワークスペース** | 通知を送信する先のワークスペース | 新規作成 or 既存のものを使用 |
| 3 | **Slack App** | API呼び出しに必要なアプリケーション | Slack APIサイトで作成（後述） |
| 4 | **Bot User OAuth Token** | API認証用トークン（`xoxb-`で始まる） | Slack App作成時に取得 |
| 5 | **チャンネルID** | 通知送信先チャンネルの識別子（`C`で始まる） | Slackアプリで確認 |

#### 不要な項目（参考）

| 項目 | 説明 |
|------|------|
| Incoming Webhook URL | 今回は使用しない（files_upload_v2を使用） |
| User Token | Bot Tokenのみ使用（ユーザートークンは不要） |
| Signing Secret | Webhookイベント受信時に必要（今回は送信のみ） |
| クレジットカード | 無料プランのため不要 |

### 6.3 取得情報の一覧と形式

| 情報 | 形式 | 例 | 保存先 |
|------|------|-----|--------|
| Bot User OAuth Token | `xoxb-{数字}-{数字}-{英数字}` | `your-slack-bot-token-here` | `.env` |
| チャンネルID | `C` + 英数字（11文字程度） | `C01AB2CD3EF` | `.env` |

### 6.4 準備作業のフロー

```
┌─────────────────────────────────────────────────────────────────┐
│                     事前準備フロー                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Step 1: Slackアカウント作成（未登録の場合）                      │
│          └─ https://slack.com/ でサインアップ                    │
│                           │                                     │
│                           ▼                                     │
│  Step 2: ワークスペース作成 or 参加                              │
│          └─ 通知を受け取るワークスペースを用意                    │
│                           │                                     │
│                           ▼                                     │
│  Step 3: 通知用チャンネル作成                                    │
│          └─ 例: #pet-monitor（任意の名前）                       │
│                           │                                     │
│                           ▼                                     │
│  Step 4: Slack App作成（→ 次セクションで詳述）                   │
│          └─ https://api.slack.com/apps                          │
│                           │                                     │
│                           ▼                                     │
│  Step 5: Bot Token取得                                          │
│          └─ OAuth & Permissions ページで取得                     │
│                           │                                     │
│                           ▼                                     │
│  Step 6: チャンネルID取得                                        │
│          └─ Slackアプリでチャンネル詳細から確認                   │
│                           │                                     │
│                           ▼                                     │
│  Step 7: .envファイル作成                                        │
│          └─ 取得した情報を設定                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 6.5 .env ファイルの設定例

```env
# ==============================================
# Slack通知設定
# ==============================================

# Bot User OAuth Token（Slack Appから取得）
# 形式: xoxb-で始まる文字列
SLACK_BOT_TOKEN=your-slack-bot-token-here

# 通知先チャンネルID（Slackアプリから取得）
# 形式: Cで始まる11文字程度の英数字
SLACK_CHANNEL=C01AB2CD3EF
```

### 6.6 よくある質問（FAQ）

| 質問 | 回答 |
|------|------|
| 無料で使えますか？ | はい。Slack APIは無料プランで利用可能です |
| クレジットカードは必要？ | 不要です |
| 既存のワークスペースでも使える？ | はい。管理者権限があればApp追加可能です |
| 個人用ワークスペースでも使える？ | はい。自分だけのワークスペースでもOKです |
| Bot Tokenは期限切れになる？ | 通常は無期限。再インストール時に再発行が必要 |
| 複数チャンネルに通知できる？ | はい。チャンネルIDを変えて呼び出し可能です |

---

## 7. Slack App セットアップ手順

### 7.0 事前準備：必要なパッケージのインストール

Slack通知機能を使用するには、以下のPythonパッケージが必要。

#### 必要なパッケージ

| パッケージ | バージョン | 用途 |
|-----------|-----------|------|
| `slack-sdk` | >= 3.27.0 | Slack Web API クライアント（files_upload_v2 対応） |
| `python-dotenv` | >= 1.0.0 | 環境変数ファイル（.env）の読み込み |

#### インストール手順

```bash
# 仮想環境をアクティブ化（プロジェクトで仮想環境を使用している場合）
source .venv/bin/activate

# パッケージのインストール
pip install slack-sdk python-dotenv
```

#### インストール確認

```bash
# インストールされたパッケージを確認
pip list | grep -E "slack-sdk|python-dotenv"
```

期待される出力（バージョンは異なる場合があります）：
```
python-dotenv    1.0.1
slack-sdk        3.39.0
```

> **Note**: `requirements.txt` にこれらのパッケージは既に含まれています。
> `pip install -r requirements.txt` でまとめてインストールすることも可能です。

---

### 7.1 Slack Appの作成

1. **Slack APIサイトにアクセス**
   - URL: https://api.slack.com/apps
   - Slackアカウントでログイン

2. **新規App作成**
   - 「Create New App」ボタンをクリック

3. **作成方法の選択ダイアログ**
   - 以下の選択肢が表示される：
     | 選択肢 | 説明 | 選択 |
     |--------|------|------|
     | From a manifest | YAMLファイルで一括設定（上級者向け） | - |
     | **From scratch** | GUIで手動設定（初心者向け） | ✅ |
   - **「From scratch」を選択**

4. **アプリ情報の入力ダイアログ（Name app & choose workspace）**

   以下のダイアログが表示される：

   | 項目 | 入力内容 | 説明 |
   |------|---------|------|
   | **App Name** | `Pet Monitor` | アプリ名（後から変更可能） |
   | **Pick a workspace to develop your app in:** | 通知を送りたいワークスペースを選択 | **※後から変更不可** |

   > **注意**: ワークスペースは後から変更できません。ダイアログには以下の警告が表示されます：
   > *"Keep in mind that you can't change this app's workspace later. If you leave the workspace, you won't be able to manage any apps you've built for it."*

   - 入力後、「Create App」ボタンをクリック
   - ※ボタンクリックで Slack API Terms of Service に同意したことになります

### 7.2 権限（OAuth Scopes）の設定

1. 左メニューから「OAuth & Permissions」を選択

2. 「Scopes」セクションまでスクロール

3. 「Bot Token Scopes」で「Add an OAuth Scope」をクリック
   - スコープ一覧のドロップダウンが表示される

4. **検索フィールドにスコープ名を入力して追加**

   以下の2つのスコープを検索して追加する：

   | 検索する文字列 | 表示される項目 | 説明 |
   |---------------|---------------|------|
   | `files:write` | **files:write** - Upload, edit, and delete files as Pet Watcher | 画像アップロードに必要 |
   | `chat:write` | **chat:write** - Send messages as Pet Watcher | メッセージ送信に必要 |

   **操作手順（各スコープごとに繰り返す）**：
   1. 「Add an OAuth Scope」をクリック
   2. 検索フィールドにスコープ名（例: `files:write`）を入力
   3. 表示された項目をクリックして追加

5. 追加完了後、「Bot Token Scopes」に2つのスコープが表示されていることを確認

### 7.3 ワークスペースへのインストール

1. 「OAuth & Permissions」ページの上部へスクロール

2. 「Install to Workspace」ボタンをクリック

3. 権限を確認し「許可する」をクリック

4. **Bot User OAuth Token** が表示される
   - `xoxb-` で始まるトークン
   - このトークンを `.env` ファイルに保存

### 7.4 チャンネルIDの取得

通知を送信するチャンネルのIDを取得する。

1. **Slackアプリ（デスクトップ版またはブラウザ版）でチャンネルを開く**

2. **チャンネル名をクリック**
   - 画面上部のチャンネル名（例: `#pet-monitor`）をクリック
   - チャンネル詳細のポップアップが表示される

3. **チャンネルIDを確認**
   - ポップアップの最下部までスクロール
   - 「チャンネルID」の項目に `C` で始まる文字列が表示される
   - 例: `C06NU1CGZ45`

4. **チャンネルIDをコピー**
   - チャンネルIDの横にあるコピーアイコンをクリック
   - または、文字列を選択してコピー

5. **`.env` ファイルに保存**
   ```
   SLACK_CHANNEL=C06NU1CGZ45
   ```

### 7.5 チャンネルへのBot招待

Botがチャンネルにメッセージを送信するには、チャンネルへの招待が必要。

1. Slackアプリで通知を送りたいチャンネルを開く

2. メッセージ入力欄に以下を入力:
   ```
   /invite @Pet Watcher
   ```

3. Enterで送信 → Botがチャンネルに参加
   - 「Pet Watcher がチャンネルに参加しました」と表示される

### 7.6 動作確認（テストプログラム）

`slack_notifier.py` はCLI（コマンドラインインターフェース）機能を備えており、セットアップ後の動作確認に使用できる。

#### 7.6.1 設定の検証

環境変数（`.env`ファイル）が正しく設定されているか確認する。

```bash
# 仮想環境をアクティブ化
source .venv/bin/activate

# 設定を検証
python slack_notifier.py --validate
```

**成功時の出力**:
```
Slack設定を確認中...
[OK] SLACK_BOT_TOKEN: 設定済み
[OK] SLACK_CHANNEL: 設定済み
[OK] すべての設定が有効です
```

**失敗時の出力例**（トークン未設定の場合）:
```
Slack設定を確認中...
[NG] SLACK_BOT_TOKEN: 未設定
[OK] SLACK_CHANNEL: 設定済み
[NG] 設定に問題があります
```

#### 7.6.2 テストメッセージの送信

Slackチャンネルにテストメッセージを送信して、通信が正常に行えるか確認する。

```bash
python slack_notifier.py --test
```

**成功時の出力**:
```
テストメッセージを送信中...
[OK] テストメッセージの送信に成功しました
```

**Slackに届くメッセージ**:
```
Slack通知モジュールのテストメッセージです
```

**失敗時の出力例**（Botがチャンネル未参加の場合）:
```
テストメッセージを送信中...
[NG] メッセージ送信に失敗しました: not_in_channel
    → Botをチャンネルに招待してください（/invite @Pet Watcher）
```

#### 7.6.3 画像のアップロードテスト

実際に画像ファイルをSlackにアップロードして動作確認する。

```bash
# 単一ファイル
python slack_notifier.py --upload test_image.jpg

# 複数ファイル
python slack_notifier.py --upload image1.jpg image2.jpg image3.jpg
```

**成功時の出力**:
```
画像をアップロード中...
[OK] 3枚の画像をアップロードしました
```

#### 7.6.4 ヘルプの表示

使用可能なオプションを確認する。

```bash
python slack_notifier.py --help
```

**出力**:
```
usage: slack_notifier.py [-h] [--validate] [--test] [--upload FILE [FILE ...]]

Slack通知モジュール - ペット監視システム用

options:
  -h, --help            show this help message and exit
  --validate            設定を検証
  --test                テストメッセージを送信
  --upload FILE [FILE ...]
                        画像をアップロード
```

#### 7.6.5 動作確認チェックリスト

セットアップ完了後、以下の順序で動作確認を行う：

| # | コマンド | 確認内容 | 期待結果 |
|---|---------|---------|---------|
| 1 | `--validate` | 環境変数の設定 | すべて「OK」 |
| 2 | `--test` | メッセージ送信 | Slackにメッセージ到着 |
| 3 | `--upload` | 画像アップロード | Slackに画像表示 |

すべての確認が完了すれば、Slack通知機能のセットアップは完了。

---

## 8. CLI機能

### 8.1 コマンドラインオプション

```bash
# 設定の検証
python slack_notifier.py --validate

# テストメッセージ送信
python slack_notifier.py --test

# 画像をアップロード
python slack_notifier.py --upload image1.jpg image2.jpg image3.jpg

# ヘルプ表示
python slack_notifier.py --help
```

### 8.2 CLI実装仕様

```python
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Slack通知モジュール")
    parser.add_argument("--validate", action="store_true", help="設定を検証")
    parser.add_argument("--test", action="store_true", help="テストメッセージを送信")
    parser.add_argument("--upload", nargs="+", metavar="FILE", help="画像をアップロード")

    args = parser.parse_args()

    if args.validate:
        # 設定検証を実行
        ...
    elif args.test:
        # テストメッセージ送信
        ...
    elif args.upload:
        # 画像アップロード
        ...
```

---

## 9. システム連携アーキテクチャ

### 9.1 モジュール間の役割分担

本システムは、各モジュールが明確な責務を持つ設計とする。

```
┌─────────────────────────────────────────────────────────────────┐
│                         main.py                                  │
│                    （オーケストレーター）                          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  タイマー（1時間ごと）                                    │    │
│  │    ↓                                                     │    │
│  │  1. camera_tracker から最新画像パスを取得                 │    │
│  │    ↓                                                     │    │
│  │  2. slack_notifier で画像を送信                          │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
        │                                    │
        ▼                                    ▼
┌───────────────────┐              ┌───────────────────┐
│  camera_tracker   │              │  slack_notifier   │
│  ・検出・追跡      │              │  ・Slack送信のみ   │
│  ・画像保存        │              │  ・画像パスを受け取る│
│  （バウンディング  │              │                   │
│    ボックス付き）  │              │                   │
└───────────────────┘              └───────────────────┘
```

### 9.2 各モジュールの責務

| モジュール | ファイル | 責務 |
|-----------|---------|------|
| **カメラ追跡** | `camera_tracker.py` | 物体検出、P制御追跡、**画像保存（バウンディングボックス付き）** |
| **Slack通知** | `slack_notifier.py` | **画像パスを受け取ってSlackに送信するだけ** |
| **メイン** | `main.py` | タイマー制御、モジュール間の連携（オーケストレーション） |

### 9.3 設計方針

| 原則 | 適用 |
|------|------|
| **単一責任** | 各モジュールが1つの役割に専念 |
| **疎結合** | モジュール間の依存が最小限（画像パスのみで連携） |
| **関心の分離** | 画像保存とSlack送信を別モジュールに分離 |

### 9.4 データフロー

```
1. camera_tracker: 常時ペットを追跡・検出
         ↓
2. camera_tracker: 画像を保存（バウンディングボックス付き）
         ↓  ← 画像ファイルパス
3. main.py: タイマートリガー（1時間ごと）
         ↓  ← 画像ファイルパスを渡す
4. slack_notifier: 画像をSlackに送信
```

---

## 10. メインプログラムからの呼び出し例

### 10.1 推奨パターン（定期送信）

```python
# main.py
import time
from camera_tracker import CameraTracker
from slack_notifier import upload_images, send_message, validate_config

# 送信間隔（秒）: 1時間 = 3600秒
SEND_INTERVAL = 3600

def main():
    # 起動時に設定を検証
    config = validate_config()
    if not config["valid"]:
        print(f"Slack設定エラー: {config['errors']}")
        return

    # 起動通知
    send_message("ペット監視システムを起動しました")

    # カメラ追跡モジュール初期化
    tracker = CameraTracker()
    last_send_time = 0

    while True:
        # 常時追跡（検出・追従）
        tracker.track()

        # 1時間ごとにSlack送信
        current_time = time.time()
        if current_time - last_send_time >= SEND_INTERVAL:
            # 保存済み画像のパスを取得
            image_path = tracker.get_latest_image()

            if image_path:
                # Slackに送信
                result = upload_images(
                    [image_path],
                    message="定期レポート: ペット監視画像"
                )
                if result["success"]:
                    print("定期レポートを送信しました")

            last_send_time = current_time

        time.sleep(0.1)

if __name__ == "__main__":
    main()
```

**注意（追跡が長時間継続する場合）**:
- 追跡処理が「検出が続く限り継続」する実装だと、追跡関数が長時間戻らず、タイマー判定が止まることがある
- 対策として、追跡/スキャンの内部ループから定期的に呼び出される **tick（コールバック）** を用意し、
  追跡中にも定期タスク（画像保存/Slack送信）を回す（協調スケジューリング）こと

推奨例（概念）:
```python
# main.py（概念例）
def run_periodic_tasks():
    ...

camera_tracker.scan_and_track(
    ...,
    tick_callback=run_periodic_tasks,
)
```

### 10.2 従来パターン（検出時に即時送信）

```python
# main.py - 検出時に即座に送信するパターン
from camera_tracker import CameraTracker
from slack_notifier import upload_images, send_message, validate_config

def main():
    # 起動時に設定を検証
    config = validate_config()
    if not config["valid"]:
        print(f"Slack設定エラー: {config['errors']}")
        return

    # 起動通知
    send_message("ペット監視システムを起動しました")

    # 監視ループ
    tracker = CameraTracker()

    while True:
        # スキャンと追跡
        detected = tracker.scan_and_track()

        if detected:
            # 画像を撮影（バウンディングボックス付き）
            images = tracker.capture_images(count=3)

            # Slack通知
            result = upload_images(
                file_paths=images,
                message="ペットを検出しました！"
            )

            if result["success"]:
                print("通知送信完了")
            else:
                print(f"通知失敗: {result['error']}")

        # 次のスキャンまで待機（10分）
        time.sleep(600)
```

---

## 10. セキュリティ考慮事項

### 10.1 トークンの保護

| 対策 | 説明 |
|------|------|
| `.env`ファイル使用 | トークンをソースコードに含めない |
| `.gitignore`追加 | `.env`をリポジトリにコミットしない |
| 権限最小化 | 必要なスコープのみを付与 |

### 10.2 .gitignore への追加

```gitignore
# 環境変数ファイル
.env
.env.local
.env.*.local

# 撮影画像（プライバシー保護）
captures/*.jpg
captures/*.jpeg
captures/*.png
```

---

## 11. 制限事項

| 項目 | 制限値 | 備考 |
|------|--------|------|
| ファイルサイズ | 最大20MB/ファイル | Slack無料プランの場合 |
| 一度にアップロード可能数 | 最大10ファイル | files_upload_v2の制限 |
| 対応フォーマット | JPEG, PNG, GIF | 本プロジェクトではJPEGを使用 |
| API呼び出し頻度 | 1回/秒程度を推奨 | レート制限回避のため |

---

## 12. 変更履歴

| 日付 | バージョン | 変更内容 |
|------|-----------|---------|
| 2025-12-20 | 1.2.0 | 事前準備セクション追加（無料プラン情報、ユーザー取得情報、FAQ） |
| 2025-12-20 | 1.1.0 | 実装詳細を追加、セットアップ手順を充実 |
| 2025-12-20 | 1.0.0 | 初版作成 |

---

## 13. 参考資料

### 公式ドキュメント

- [Slack API Documentation](https://api.slack.com/)
- [Python Slack SDK](https://slack.dev/python-slack-sdk/)
- [Uploading files with Python](https://docs.slack.dev/tools/python-slack-sdk/tutorial/uploading-files/)
- [files.upload API廃止のお知らせ](https://docs.slack.dev/changelog/2024-04-a-better-way-to-upload-files-is-here-to-stay/)

### 関連仕様書

- [要件定義書](./pet_monitoring_requirements.md) - システム全体の要件
- [検出・追跡仕様書](./detection_and_tracking_specification.md) - 画像撮影機能
