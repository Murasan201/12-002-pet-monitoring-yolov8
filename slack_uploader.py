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
        Initialize Slack uploader.

        Args:
            bot_token: Slack Bot User OAuth Token
        """
        self.client = WebClient(token=bot_token)

    def upload_files(
        self,
        file_paths: List[str],
        channel: str,
        text: Optional[str] = None,
        title: Optional[str] = None,
    ) -> bool:
        """
        Upload files to Slack channel using files_upload_v2.

        Args:
            file_paths: List of file paths to upload
            channel: Slack channel ID or name (e.g., "#pet-monitoring")
            text: Optional message text to accompany the files
            title: Optional title for the upload

        Returns:
            True if upload succeeded, False otherwise
        """
        if not file_paths:
            print("No files to upload")
            return False

        # Verify all files exist
        for file_path in file_paths:
            if not os.path.exists(file_path):
                print(f"File not found: {file_path}")
                return False

        try:
            # Prepare file uploads
            file_uploads = []
            for file_path in file_paths:
                with open(file_path, "rb") as f:
                    file_content = f.read()

                file_uploads.append({
                    "file": file_content,
                    "filename": os.path.basename(file_path),
                })

            # Upload files
            response = self.client.files_upload_v2(
                channel=channel,
                file_uploads=file_uploads,
                initial_comment=text or "Pet detected!",
                title=title,
            )

            if response["ok"]:
                print(f"Successfully uploaded {len(file_paths)} file(s) to {channel}")
                return True
            else:
                print(f"Upload failed: {response}")
                return False

        except SlackApiError as e:
            print(f"Slack API error: {e.response['error']}")
            return False
        except Exception as e:
            print(f"Unexpected error during upload: {e}")
            return False

    def send_message(self, channel: str, text: str) -> bool:
        """
        Send a text message to Slack channel.

        Args:
            channel: Slack channel ID or name
            text: Message text

        Returns:
            True if message sent successfully, False otherwise
        """
        try:
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
        Test Slack API connection.

        Returns:
            True if connection successful, False otherwise
        """
        try:
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