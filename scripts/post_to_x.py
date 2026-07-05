#!/usr/bin/env python3
"""X(Twitter)投稿スクリプト — X API v2 正規ルート。

使い方:
    python scripts/post_to_x.py "投稿本文"
    python scripts/post_to_x.py --file posts/drafts/2026-07-05-example.md
    python scripts/post_to_x.py --dry-run "テスト本文"

認証は環境変数から読む(リポジトリには絶対に書かない):
    X_API_KEY / X_API_SECRET / X_ACCESS_TOKEN / X_ACCESS_TOKEN_SECRET
取得方法は docs/strategy/x-automation-workflow.md を参照。
"""

import argparse
import os
import sys
from pathlib import Path

MAX_LEN = 280  # 全角は2文字換算のweighted lengthだが、安全側で単純計算もチェックする


def weighted_length(text: str) -> int:
    """Xのweighted length近似: CJK等は2、半角系は1として数える。"""
    total = 0
    for ch in text:
        total += 1 if ord(ch) < 0x1100 else 2
    return total


def extract_body(raw: str) -> str:
    """下書きMarkdownから本文を抽出する。`---post---` 区切りがあればその後ろ、なければ全文。"""
    marker = "---post---"
    if marker in raw:
        return raw.split(marker, 1)[1].strip()
    return raw.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Post to X via API v2")
    parser.add_argument("text", nargs="?", help="投稿本文")
    parser.add_argument("--file", help="下書きファイル(Markdown)から本文を読む")
    parser.add_argument("--dry-run", action="store_true", help="投稿せず内容と文字数だけ確認")
    args = parser.parse_args()

    if args.file:
        body = extract_body(Path(args.file).read_text(encoding="utf-8"))
    elif args.text:
        body = args.text.strip()
    else:
        parser.error("本文または --file を指定してください")

    wlen = weighted_length(body)
    print(f"--- 投稿内容({len(body)}文字 / weighted {wlen}/280) ---")
    print(body)
    print("---")
    if wlen > MAX_LEN:
        print("ERROR: 280(weighted)を超えています。短縮してください。", file=sys.stderr)
        return 1

    if args.dry_run:
        print("dry-run: 投稿はしていません。")
        return 0

    keys = ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"]
    missing = [k for k in keys if not os.environ.get(k)]
    if missing:
        print(f"ERROR: 環境変数が未設定です: {', '.join(missing)}", file=sys.stderr)
        print("X開発者ポータルでキーを発行し、環境シークレットに設定してください。", file=sys.stderr)
        return 1

    try:
        from requests_oauthlib import OAuth1Session
    except ImportError:
        print("ERROR: `pip install requests-oauthlib` を実行してください。", file=sys.stderr)
        return 1

    session = OAuth1Session(
        os.environ["X_API_KEY"],
        client_secret=os.environ["X_API_SECRET"],
        resource_owner_key=os.environ["X_ACCESS_TOKEN"],
        resource_owner_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
    )
    resp = session.post("https://api.x.com/2/tweets", json={"text": body})
    if resp.status_code != 201:
        print(f"ERROR: 投稿失敗 status={resp.status_code} body={resp.text}", file=sys.stderr)
        return 1

    tweet_id = resp.json()["data"]["id"]
    print(f"OK: 投稿しました https://x.com/i/web/status/{tweet_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
