"""
Slack Uploader Module for Pet Monitoring System

This module handles uploading images to Slack using the Web API.
Method A (recommended): Direct file upload using files_upload_v2

【Slackへのファイルアップロード方式について】
方式A（本モジュールで採用）: Slack Web APIの files_upload_v2 を使用
  - メリット: 外部サーバー不要、Raspberry Piから直接アップロード可能
  - 必要な権限: chat:write, files:write
  - 複数ファイルを一度に送信可能

方式B（参考）: 外部ストレージ + Webhook
  - メリット: Webhookのみで実装可能
  - デメリット: S3/R2等の外部ストレージが必要、URL管理が必要
"""

import os
from typing import List, Optional
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


class SlackUploader:
    """
    Slack Web APIを使用したファイルアップローダー

    このクラスはSlack SDKのWebClientを使用して、
    画像ファイルやメッセージをSlackチャンネルに送信します。
    """

    def __init__(self, bot_token: str):
        """
        Slackアップローダーの初期化

        Args:
            bot_token: Slack Bot User OAuth Token（ボット認証トークン）
                      形式: xoxb-で始まる文字列
                      取得方法: Slack App管理画面の「OAuth & Permissions」から取得
        """
        # Slack Web APIクライアントを初期化
        # このクライアントがすべてのSlack API呼び出しを行う
        self.client = WebClient(token=bot_token)

    def upload_files(
        self,
        file_paths: List[str],
        channel: str,
        text: Optional[str] = None,
        title: Optional[str] = None,
    ) -> bool:
        """
        files_upload_v2を使用してSlackチャンネルにファイルをアップロード

        方式A（推奨）: Slack Web APIで直接ファイルをアップロード
        別サーバー不要で、Raspberry Piから直接Slackへ画像を送信できる

        【処理フロー】
        1. ファイルの存在確認
        2. 各ファイルをバイナリモードで読み込み
        3. Slack APIにアップロード
        4. レスポンスを確認して結果を返す

        Args:
            file_paths: アップロードするファイルパスのリスト
                       例: ["/path/to/image1.jpg", "/path/to/image2.jpg"]
            channel: Slackチャンネル名またはID
                    例: "#pet-monitoring" または "C01234567"
            text: ファイルに添えるメッセージ（省略可）
                 省略時は "Pet detected!" がデフォルトで使用される
            title: アップロードのタイトル（省略可）
                  ファイルグループの見出しとして表示される

        Returns:
            True: アップロード成功
            False: アップロード失敗（ファイルが存在しない、API呼び出し失敗など）
        """
        # ========== 入力チェック: ファイルリストが空でないか ==========
        if not file_paths:
            print("No files to upload")
            return False

        # ========== ファイル存在チェック ==========
        # アップロード前にすべてのファイルが存在するか確認
        # 1つでも存在しない場合はエラーとして処理
        for file_path in file_paths:
            if not os.path.exists(file_path):
                print(f"File not found: {file_path}")
                return False

        try:
            # ========== ファイルアップロードの準備 ==========
            # files_upload_v2 APIに渡す形式でファイル情報をリスト化
            file_uploads = []

            for file_path in file_paths:
                # ファイルをバイナリモードで読み込み
                # 'rb'モード: read binary（バイナリ読み込み）
                # 画像ファイルなどのバイナリデータを扱う際に必須
                with open(file_path, "rb") as f:
                    file_content = f.read()  # ファイル全体を読み込み

                # アップロード用のファイル情報を辞書形式で追加
                # "file": ファイルの中身（バイト列）
                # "filename": Slack上で表示されるファイル名
                file_uploads.append({
                    "file": file_content,
                    "filename": os.path.basename(file_path),  # パスからファイル名のみ抽出
                })

            # ========== Slack APIでファイルアップロード ==========
            # files_upload_v2: 複数ファイルを一度にアップロードできる新API
            # 旧版のfiles_uploadは非推奨となっているため、v2を使用
            response = self.client.files_upload_v2(
                channel=channel,  # 送信先チャンネル
                file_uploads=file_uploads,  # アップロードするファイルのリスト
                initial_comment=text or "Pet detected!",  # ファイルに添えるコメント
                title=title,  # ファイルグループのタイトル（省略可）
            )

            # ========== アップロード結果の確認 ==========
            # Slack APIは成功時にresponse["ok"] = Trueを返す
            if response["ok"]:
                print(f"Successfully uploaded {len(file_paths)} file(s) to {channel}")
                return True
            else:
                # API呼び出しは成功したが、何らかの理由で失敗した場合
                print(f"Upload failed: {response}")
                return False

        except SlackApiError as e:
            # Slack API特有のエラー処理
            # 例: 権限不足、チャンネルが見つからない、トークンが無効など
            print(f"Slack API error: {e.response['error']}")
            return False
        except Exception as e:
            # その他の予期しないエラー
            # 例: ネットワークエラー、ファイル読み込みエラーなど
            print(f"Unexpected error during upload: {e}")
            return False

    def send_message(self, channel: str, text: str) -> bool:
        """
        Slackチャンネルにテキストメッセージを送信

        ファイルを添付せず、テキストのみを送信する場合に使用
        画像なしで通知だけ送りたい場合などに便利

        Args:
            channel: Slackチャンネル名またはID
                    例: "#general" または "C01234567"
            text: 送信するメッセージテキスト
                 マークダウン記法が使用可能（*太字*、_斜体_など）

        Returns:
            True: 送信成功
            False: 送信失敗
        """
        try:
            # chat.postMessageでテキストメッセージを送信
            # これはSlackで最も基本的なメッセージ送信API
            response = self.client.chat_postMessage(
                channel=channel,  # 送信先チャンネル
                text=text,  # メッセージ本文
            )

            # レスポンスの確認
            if response["ok"]:
                print(f"Message sent to {channel}")
                return True
            else:
                print(f"Message send failed: {response}")
                return False

        except SlackApiError as e:
            # Slack API関連のエラー
            # 例: チャンネルへの投稿権限がない、チャンネルが存在しないなど
            print(f"Slack API error: {e.response['error']}")
            return False
        except Exception as e:
            # その他の予期しないエラー
            print(f"Unexpected error sending message: {e}")
            return False

    def test_connection(self) -> bool:
        """
        Slack API接続のテスト

        システム起動時やトラブルシューティング時に、
        トークンが正しく設定されているか、
        APIとの通信が正常にできるかを確認するために使用

        【確認内容】
        - トークンの有効性
        - ネットワーク接続
        - API権限

        Returns:
            True: 接続成功（トークン有効、通信正常）
            False: 接続失敗（トークン無効、通信エラーなど）
        """
        try:
            # auth.testで認証情報を確認
            # このAPIは認証トークンの情報を返す軽量なテスト用エンドポイント
            response = self.client.auth_test()

            # 接続成功時の処理
            if response["ok"]:
                # 接続成功時にボット情報とワークスペース情報を表示
                print(f"Connected to Slack as: {response['user']}")  # ボット名
                print(f"Team: {response['team']}")  # ワークスペース名
                return True
            else:
                # API呼び出しは成功したが認証失敗の場合
                print("Connection test failed")
                return False

        except SlackApiError as e:
            # Slack API関連のエラー
            # よくあるエラー: "invalid_auth"（トークンが無効）
            print(f"Slack API error: {e.response['error']}")
            return False
        except Exception as e:
            # その他の予期しないエラー
            # 例: ネットワーク接続エラー、タイムアウトなど
            print(f"Unexpected error: {e}")
            return False