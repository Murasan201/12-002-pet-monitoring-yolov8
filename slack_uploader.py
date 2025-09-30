"""
Slack Uploader Module for Pet Monitoring System

This module handles uploading images to Slack using the Web API.
Method A (recommended): Direct file upload using files_upload_v2
"""

import os
from typing import List, Optional
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


class SlackUploader:
    """Slack file uploader using Web API."""

    def __init__(self, bot_token: str):
        """
        Slackアップローダーの初期化

        Args:
            bot_token: Slack Bot User OAuth Token（ボット認証トークン）
        """
        # Slack Web APIクライアントを初期化
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

        Args:
            file_paths: アップロードするファイルパスのリスト
            channel: Slackチャンネル名またはID（例: "#pet-monitoring"）
            text: ファイルに添えるメッセージ（省略可）
            title: アップロードのタイトル（省略可）

        Returns:
            True: アップロード成功
            False: アップロード失敗
        """
        if not file_paths:
            print("No files to upload")
            return False

        # すべてのファイルが存在するか確認
        for file_path in file_paths:
            if not os.path.exists(file_path):
                print(f"File not found: {file_path}")
                return False

        try:
            # ========== ファイルアップロードの準備 ==========
            file_uploads = []
            for file_path in file_paths:
                # ファイルをバイナリモードで読み込み
                with open(file_path, "rb") as f:
                    file_content = f.read()

                # アップロード用のファイル情報を追加
                file_uploads.append({
                    "file": file_content,
                    "filename": os.path.basename(file_path),  # ファイル名のみ抽出
                })

            # ========== Slack APIでファイルアップロード ==========
            # files_upload_v2: 複数ファイルを一度にアップロードできる新API
            response = self.client.files_upload_v2(
                channel=channel,
                file_uploads=file_uploads,
                initial_comment=text or "Pet detected!",  # デフォルトメッセージ
                title=title,
            )

            # アップロード結果の確認
            if response["ok"]:
                print(f"Successfully uploaded {len(file_paths)} file(s) to {channel}")
                return True
            else:
                print(f"Upload failed: {response}")
                return False

        except SlackApiError as e:
            # Slack API特有のエラー処理
            print(f"Slack API error: {e.response['error']}")
            return False
        except Exception as e:
            # その他の予期しないエラー
            print(f"Unexpected error during upload: {e}")
            return False

    def send_message(self, channel: str, text: str) -> bool:
        """
        Slackチャンネルにテキストメッセージを送信

        Args:
            channel: Slackチャンネル名またはID
            text: 送信するメッセージテキスト

        Returns:
            True: 送信成功
            False: 送信失敗
        """
        try:
            # chat.postMessageでテキストメッセージを送信
            response = self.client.chat_postMessage(
                channel=channel,
                text=text,
            )

            if response["ok"]:
                print(f"Message sent to {channel}")
                return True
            else:
                print(f"Message send failed: {response}")
                return False

        except SlackApiError as e:
            print(f"Slack API error: {e.response['error']}")
            return False
        except Exception as e:
            print(f"Unexpected error sending message: {e}")
            return False

    def test_connection(self) -> bool:
        """
        Slack API接続のテスト

        トークンが正しく設定されているか、
        APIとの通信が正常にできるかを確認

        Returns:
            True: 接続成功
            False: 接続失敗
        """
        try:
            # auth.testで認証情報を確認
            response = self.client.auth_test()
            if response["ok"]:
                print(f"Connected to Slack as: {response['user']}")
                print(f"Team: {response['team']}")
                return True
            else:
                print("Connection test failed")
                return False

        except SlackApiError as e:
            print(f"Slack API error: {e.response['error']}")
            return False
        except Exception as e:
            print(f"Unexpected error: {e}")
            return False