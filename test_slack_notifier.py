#!/usr/bin/env python3
"""
slack_notifier.py の簡易テストスクリプト

環境変数が設定されていない状態での動作確認用。
実際のSlack APIを呼び出さずに、関数のインターフェースと基本動作をテストする。
"""

import os
import sys

# 環境変数をクリア（テスト用）
os.environ.pop("SLACK_BOT_TOKEN", None)
os.environ.pop("SLACK_CHANNEL", None)

from slack_notifier import validate_config, upload_images, send_message


def test_validate_config():
    """validate_config()のテスト"""
    print("=== validate_config() テスト ===")

    result = validate_config()

    assert isinstance(result, dict), "返り値はdict型である必要があります"
    assert "valid" in result, "valid キーが必要です"
    assert "token_set" in result, "token_set キーが必要です"
    assert "channel_set" in result, "channel_set キーが必要です"
    assert "errors" in result, "errors キーが必要です"

    # 環境変数が設定されていない場合
    assert result["valid"] is False, "環境変数未設定時はvalid=Falseである必要があります"
    assert result["token_set"] is False, "トークン未設定時はtoken_set=Falseである必要があります"
    assert result["channel_set"] is False, "チャンネル未設定時はchannel_set=Falseである必要があります"
    assert len(result["errors"]) > 0, "エラーメッセージが含まれている必要があります"

    print("[OK] validate_config() は正しく動作しています")
    print(f"  valid: {result['valid']}")
    print(f"  errors: {result['errors']}")
    print()


def test_upload_images_no_token():
    """upload_images()のエラーハンドリングテスト（トークン未設定）"""
    print("=== upload_images() エラーテスト ===")

    result = upload_images(
        file_paths=["dummy.jpg"],
        message="テスト"
    )

    assert isinstance(result, dict), "返り値はdict型である必要があります"
    assert "success" in result, "success キーが必要です"
    assert "uploaded_count" in result, "uploaded_count キーが必要です"
    assert "error" in result, "error キーが必要です"

    # 環境変数未設定の場合はエラーとなる
    assert result["success"] is False, "環境変数未設定時は失敗する必要があります"
    assert result["uploaded_count"] == 0, "失敗時はアップロード数0である必要があります"
    assert result["error"] is not None, "エラーメッセージが必要です"

    print("[OK] upload_images() は正しくエラーハンドリングしています")
    print(f"  success: {result['success']}")
    print(f"  error: {result['error']}")
    print()


def test_send_message_no_token():
    """send_message()のエラーハンドリングテスト（トークン未設定）"""
    print("=== send_message() エラーテスト ===")

    result = send_message("テストメッセージ")

    assert isinstance(result, dict), "返り値はdict型である必要があります"
    assert "success" in result, "success キーが必要です"
    assert "error" in result, "error キーが必要です"

    # 環境変数未設定の場合はエラーとなる
    assert result["success"] is False, "環境変数未設定時は失敗する必要があります"
    assert result["error"] is not None, "エラーメッセージが必要です"

    print("[OK] send_message() は正しくエラーハンドリングしています")
    print(f"  success: {result['success']}")
    print(f"  error: {result['error']}")
    print()


def main():
    """テスト実行"""
    print("slack_notifier.py の基本動作テスト")
    print("=" * 50)
    print()

    try:
        test_validate_config()
        test_upload_images_no_token()
        test_send_message_no_token()

        print("=" * 50)
        print("[OK] すべてのテストに合格しました")
        print()
        print("次のステップ:")
        print("  1. .env ファイルを作成して環境変数を設定")
        print("  2. python slack_notifier.py --validate で設定確認")
        print("  3. python slack_notifier.py --test で実際のAPI動作確認")

        return 0

    except AssertionError as e:
        print()
        print("[NG] テスト失敗:", str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
