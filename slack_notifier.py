#!/usr/bin/env python3
"""
Slack通知モジュール

ペット監視システムで撮影した画像をSlackに通知する機能を提供する。
Slack Web API (files_upload_v2) を使用して画像とメッセージを送信する。

Usage:
    # ライブラリとして使用
    from slack_notifier import upload_images, send_message, validate_config

    # CLIとして使用
    python slack_notifier.py --validate
    python slack_notifier.py --test
    python slack_notifier.py --upload image1.jpg image2.jpg
"""

import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


# 環境変数を.envファイルから読み込む
load_dotenv()


def validate_config() -> dict:
    """
    Slack通知に必要な設定を検証する。

    起動時やデバッグ時に呼び出すことで、必要な環境変数が正しく設定されているかを確認できる。

    Returns:
        dict: 検証結果
            {
                "valid": True/False,        # すべての設定が有効か
                "token_set": True/False,    # トークンが設定されているか
                "channel_set": True/False,  # チャンネルが設定されているか
                "errors": list[str]         # エラーメッセージのリスト
            }

    Example:
        >>> config = validate_config()
        >>> if not config["valid"]:
        ...     print("設定エラー:", config["errors"])
    """
    errors = []

    # Bot User OAuth Tokenの確認
    token = os.getenv("SLACK_BOT_TOKEN")
    token_set = bool(token and token.strip())
    if not token_set:
        errors.append("SLACK_BOT_TOKEN が設定されていません")
    elif not token.startswith("xoxb-"):
        errors.append("SLACK_BOT_TOKEN の形式が正しくありません（xoxb-で始まる必要があります）")

    # チャンネルIDの確認
    channel = os.getenv("SLACK_CHANNEL")
    channel_set = bool(channel and channel.strip())
    if not channel_set:
        errors.append("SLACK_CHANNEL が設定されていません")
    elif not channel.startswith("C"):
        errors.append("SLACK_CHANNEL の形式が正しくありません（Cで始まる必要があります）")

    return {
        "valid": len(errors) == 0,
        "token_set": token_set,
        "channel_set": channel_set,
        "errors": errors
    }


def upload_images(
    file_paths: list[str],
    channel: Optional[str] = None,
    message: Optional[str] = None
) -> dict:
    """
    画像ファイルをSlackにアップロードする。

    複数の画像ファイルを一度にアップロードし、オプションでメッセージを添えることができる。
    内部でSlack Web APIのfiles_upload_v2メソッドを使用する。

    Args:
        file_paths: アップロードする画像ファイルのパスリスト（1〜10枚）
        channel: 送信先チャンネルID（省略時は環境変数SLACK_CHANNELを使用）
        message: 画像と一緒に投稿するメッセージ（省略可）

    Returns:
        dict: 実行結果
            {
                "success": True/False,       # 実行成功したか
                "uploaded_count": int,       # アップロード成功数
                "error": str | None          # エラー時のメッセージ
            }

    Raises:
        FileNotFoundError: 指定ファイルが存在しない場合
        SlackApiError: Slack API呼び出しエラー時

    Example:
        >>> result = upload_images(
        ...     file_paths=["pet_1.jpg", "pet_2.jpg"],
        ...     message="ペットを検出しました！"
        ... )
        >>> if result["success"]:
        ...     print(f"{result['uploaded_count']}枚送信完了")
    """
    # チャンネルIDの決定（引数 > 環境変数の優先順位）
    target_channel = channel or os.getenv("SLACK_CHANNEL")
    if not target_channel:
        return {
            "success": False,
            "uploaded_count": 0,
            "error": "チャンネルIDが指定されていません（引数または環境変数SLACK_CHANNELで指定してください）"
        }

    # ファイルの存在確認
    for file_path in file_paths:
        if not os.path.exists(file_path):
            return {
                "success": False,
                "uploaded_count": 0,
                "error": f"ファイルが見つかりません: {file_path}"
            }

    # ファイル数の検証（Slack APIの制限: 最大10ファイル）
    if len(file_paths) > 10:
        return {
            "success": False,
            "uploaded_count": 0,
            "error": "一度にアップロードできるファイルは最大10個までです"
        }

    # Botトークンの取得
    token = os.getenv("SLACK_BOT_TOKEN")
    if not token:
        return {
            "success": False,
            "uploaded_count": 0,
            "error": "SLACK_BOT_TOKEN が設定されていません"
        }

    try:
        # WebClientの初期化
        client = WebClient(token=token)

        # ファイルアップロードの準備
        # 複数ファイルをアップロードする場合はfile_uploadsパラメータを使用
        if len(file_paths) == 1:
            # 単一ファイルの場合はfileパラメータを使用
            response = client.files_upload_v2(
                channel=target_channel,
                file=file_paths[0],
                initial_comment=message  # メッセージがNoneの場合は無視される
            )
        else:
            # 複数ファイルの場合はfile_uploadsパラメータを使用
            file_uploads = [
                {
                    "file": file_path,
                    "title": os.path.basename(file_path)  # ファイル名をタイトルとして使用
                }
                for file_path in file_paths
            ]

            response = client.files_upload_v2(
                channel=target_channel,
                file_uploads=file_uploads,
                initial_comment=message
            )

        # アップロード成功
        return {
            "success": True,
            "uploaded_count": len(file_paths),
            "error": None
        }

    except SlackApiError as e:
        # Slack APIエラーのハンドリング
        error_code = e.response.get("error", "unknown_error")

        # エラーコードに応じたメッセージを返す
        error_messages = {
            "invalid_auth": "認証エラー: トークンが無効です。SLACK_BOT_TOKENを確認してください",
            "channel_not_found": "チャンネルが見つかりません。チャンネルIDを確認してください",
            "not_in_channel": "Botがチャンネルに参加していません。'/invite @アプリ名' でBotを招待してください",
            "file_not_found": "ファイルが見つかりません",
            "ratelimited": "API呼び出し頻度が高すぎます。しばらく待ってから再試行してください"
        }

        error_message = error_messages.get(
            error_code,
            f"Slack APIエラー: {error_code} - {e.response.get('error', 'unknown')}"
        )

        return {
            "success": False,
            "uploaded_count": 0,
            "error": error_message
        }

    except Exception as e:
        # その他の予期しないエラー
        return {
            "success": False,
            "uploaded_count": 0,
            "error": f"予期しないエラーが発生しました: {str(e)}"
        }


def send_message(
    message: str,
    channel: Optional[str] = None
) -> dict:
    """
    テキストメッセージをSlackに送信する。

    システムの状態通知やログメッセージを送信する際に使用する。

    Args:
        message: 送信するメッセージ
        channel: 送信先チャンネルID（省略時は環境変数SLACK_CHANNELを使用）

    Returns:
        dict: 実行結果
            {
                "success": True/False,   # 実行成功したか
                "error": str | None      # エラー時のメッセージ
            }

    Example:
        >>> result = send_message("ペット監視システムを起動しました")
        >>> if result["success"]:
        ...     print("メッセージ送信完了")
    """
    # チャンネルIDの決定
    target_channel = channel or os.getenv("SLACK_CHANNEL")
    if not target_channel:
        return {
            "success": False,
            "error": "チャンネルIDが指定されていません"
        }

    # Botトークンの取得
    token = os.getenv("SLACK_BOT_TOKEN")
    if not token:
        return {
            "success": False,
            "error": "SLACK_BOT_TOKEN が設定されていません"
        }

    try:
        # WebClientの初期化
        client = WebClient(token=token)

        # メッセージ送信
        response = client.chat_postMessage(
            channel=target_channel,
            text=message
        )

        return {
            "success": True,
            "error": None
        }

    except SlackApiError as e:
        # Slack APIエラーのハンドリング
        error_code = e.response.get("error", "unknown_error")

        error_messages = {
            "invalid_auth": "認証エラー: トークンが無効です",
            "channel_not_found": "チャンネルが見つかりません",
            "not_in_channel": "Botがチャンネルに参加していません"
        }

        error_message = error_messages.get(
            error_code,
            f"Slack APIエラー: {error_code}"
        )

        return {
            "success": False,
            "error": error_message
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"予期しないエラー: {str(e)}"
        }


def _cli_validate() -> int:
    """
    CLIモード: 設定を検証して結果を表示する。

    Returns:
        int: 終了コード（0: 成功, 1: 失敗）
    """
    print("Slack設定を確認中...")
    print()

    config = validate_config()

    # トークンの状態表示
    if config["token_set"]:
        print("[OK] SLACK_BOT_TOKEN: 設定済み")
    else:
        print("[NG] SLACK_BOT_TOKEN: 未設定")

    # チャンネルの状態表示
    if config["channel_set"]:
        print("[OK] SLACK_CHANNEL: 設定済み")
    else:
        print("[NG] SLACK_CHANNEL: 未設定")

    print()

    # 全体の結果表示
    if config["valid"]:
        print("[OK] すべての設定が有効です")
        return 0
    else:
        print("[NG] 設定にエラーがあります:")
        for error in config["errors"]:
            print(f"  - {error}")
        print()
        print("解決方法:")
        print("  1. .envファイルをプロジェクトルートに作成してください")
        print("  2. SLACK_BOT_TOKEN と SLACK_CHANNEL を設定してください")
        print("     SLACK_BOT_TOKEN=xoxb-your-token-here")
        print("     SLACK_CHANNEL=C01234ABCDE")
        return 1


def _cli_test() -> int:
    """
    CLIモード: テストメッセージを送信する。

    Returns:
        int: 終了コード（0: 成功, 1: 失敗）
    """
    print("テストメッセージを送信中...")

    # 設定検証
    config = validate_config()
    if not config["valid"]:
        print("[NG] 設定エラー:")
        for error in config["errors"]:
            print(f"  - {error}")
        return 1

    # メッセージ送信
    result = send_message("Slack通知モジュールのテストメッセージです")

    if result["success"]:
        print("[OK] テストメッセージの送信に成功しました")
        return 0
    else:
        print(f"[NG] エラー: {result['error']}")
        return 1


def _cli_upload(file_paths: list[str]) -> int:
    """
    CLIモード: 画像ファイルをアップロードする。

    Args:
        file_paths: アップロードするファイルパスのリスト

    Returns:
        int: 終了コード（0: 成功, 1: 失敗）
    """
    print(f"{len(file_paths)}個のファイルをアップロード中...")

    # 設定検証
    config = validate_config()
    if not config["valid"]:
        print("[NG] 設定エラー:")
        for error in config["errors"]:
            print(f"  - {error}")
        return 1

    # 画像アップロード
    result = upload_images(
        file_paths=file_paths,
        message=f"{len(file_paths)}枚の画像をアップロードしました"
    )

    if result["success"]:
        print(f"[OK] {result['uploaded_count']}個のファイルのアップロードに成功しました")
        return 0
    else:
        print(f"[NG] エラー: {result['error']}")
        return 1


def main() -> int:
    """
    CLIモードのメイン処理。

    Returns:
        int: 終了コード
    """
    import argparse

    # コマンドライン引数のパーサー設定
    parser = argparse.ArgumentParser(
        description="Slack通知モジュール - ペット監視システムの画像をSlackに送信します",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 設定を検証
  python slack_notifier.py --validate

  # テストメッセージを送信
  python slack_notifier.py --test

  # 画像をアップロード
  python slack_notifier.py --upload image1.jpg image2.jpg image3.jpg

環境変数:
  SLACK_BOT_TOKEN    Bot User OAuth Token (xoxb-で始まる)
  SLACK_CHANNEL      送信先チャンネルID (Cで始まる)

.envファイルの設定例:
  SLACK_BOT_TOKEN=xoxb-your-token-here
  SLACK_CHANNEL=C01234ABCDE
        """
    )

    # サブコマンド的なオプション（排他的グループ）
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--validate",
        action="store_true",
        help="設定を検証する"
    )
    group.add_argument(
        "--test",
        action="store_true",
        help="テストメッセージを送信する"
    )
    group.add_argument(
        "--upload",
        nargs="+",
        metavar="FILE",
        help="画像ファイルをアップロードする（最大10個）"
    )

    args = parser.parse_args()

    # コマンドに応じた処理を実行
    if args.validate:
        return _cli_validate()
    elif args.test:
        return _cli_test()
    elif args.upload:
        return _cli_upload(args.upload)

    return 1


if __name__ == "__main__":
    sys.exit(main())
