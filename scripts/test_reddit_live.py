from __future__ import annotations

import argparse
import base64
import csv
import html
import json
import os
import sys
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from moctale_moderation import ModerationEngine, ModerationRequest


DEFAULT_SUBREDDITS = (
    "bollywood",
    "BollyBlindsNGossip",
    "IndianCinema",
    "Cricket",
    "india",
    "IndiaSpeaks",
)

USER_AGENT = "MoctaleModerationLiveTest/0.1 by local-dev"
REDDIT_BASE = "https://www.reddit.com"
REDDIT_OAUTH_BASE = "https://oauth.reddit.com"


@dataclass(frozen=True, slots=True)
class LiveComment:
    subreddit: str
    post_title: str
    source_url: str
    text: str
    score: int


def fetch_json(url: str, *, headers: dict[str, str] | None = None, timeout: int = 20, retries: int = 2) -> Any:
    request_headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if headers:
        request_headers.update(headers)
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            request = Request(url, headers=request_headers)
            with urlopen(request, timeout=timeout) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                return json.loads(response.read().decode(charset))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Could not fetch {url}: {last_error}") from last_error


def fetch_reddit_oauth_token(client_id: str, client_secret: str) -> str:
    credentials = f"{client_id}:{client_secret}".encode("utf-8")
    auth = base64.b64encode(credentials).decode("ascii")
    body = urlencode({"grant_type": "client_credentials"}).encode("ascii")
    headers = {
        "Authorization": f"Basic {auth}",
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    request = Request(f"{REDDIT_BASE}/api/v1/access_token", data=body, headers=headers, method="POST")
    with urlopen(request, timeout=20) as response:
        data = json.loads(response.read().decode("utf-8"))
    token = data.get("access_token")
    if not token:
        raise RuntimeError(f"Reddit OAuth did not return an access token: {data}")
    return str(token)


def plain_text(value: str) -> str:
    value = html.unescape(value or "")
    value = value.replace("\n", " ").replace("\r", " ")
    return " ".join(value.split())


def listing_url(base_url: str, subreddit: str, sort: str, limit: int) -> str:
    query = urlencode({"limit": limit, "raw_json": 1})
    return f"{base_url}/r/{subreddit}/{sort}.json?{query}"


def comments_url(base_url: str, permalink: str, sort: str, limit: int) -> str:
    query = urlencode({"limit": limit, "sort": sort, "raw_json": 1})
    return f"{base_url}{permalink}.json?{query}"


def iter_comment_nodes(node: Any):
    if not isinstance(node, dict):
        return
    data = node.get("data", {})
    if node.get("kind") == "t1":
        yield data
    replies = data.get("replies")
    if isinstance(replies, dict):
        children = replies.get("data", {}).get("children", [])
        for child in children:
            yield from iter_comment_nodes(child)


def fetch_live_comments(
    subreddits: list[str],
    *,
    base_url: str,
    headers: dict[str, str],
    post_sort: str,
    comment_sort: str,
    posts_per_subreddit: int,
    comments_per_post: int,
    max_comments: int,
) -> list[LiveComment]:
    comments: list[LiveComment] = []
    seen_text: set[str] = set()

    for subreddit in subreddits:
        listing = fetch_json(listing_url(base_url, subreddit, post_sort, posts_per_subreddit), headers=headers)
        posts = listing.get("data", {}).get("children", [])
        for post in posts:
            post_data = post.get("data", {})
            permalink = post_data.get("permalink")
            title = plain_text(post_data.get("title", ""))
            if not permalink:
                continue

            thread = fetch_json(comments_url(base_url, permalink, comment_sort, comments_per_post), headers=headers)
            if not isinstance(thread, list) or len(thread) < 2:
                continue

            source_url = f"{REDDIT_BASE}{permalink}"
            for comment in iter_comment_nodes(thread[1]):
                text = plain_text(comment.get("body", ""))
                if not text or text in {"[deleted]", "[removed]"} or len(text) < 8:
                    continue
                if text in seen_text:
                    continue
                seen_text.add(text)
                comments.append(
                    LiveComment(
                        subreddit=subreddit,
                        post_title=title,
                        source_url=source_url,
                        text=text[:1000],
                        score=int(comment.get("score") or 0),
                    )
                )
                if len(comments) >= max_comments:
                    return comments
    return comments


def context_for(comment: LiveComment) -> ModerationRequest:
    return ModerationRequest(
        text=comment.text,
        context_type="reply_to_comment",
        parent_review_rating="Timepass",
        movie_rating_perfection_pct=50,
        movie_rating_skip_pct=20,
    )


def print_results(rows: list[tuple[LiveComment, Any]], *, show_text: bool, top: int) -> None:
    counts = Counter(result.predicted_action for _, result in rows)
    print("Live Reddit moderation summary")
    print(f"comments={len(rows)}")
    for action, count in sorted(counts.items()):
        print(f"{action}={count}")

    print("\nHighest-risk examples")
    ranked = sorted(rows, key=lambda item: (item[1].predicted_action != "allow", item[1].risk_score), reverse=True)
    for i, (comment, result) in enumerate(ranked[:top], start=1):
        print(f"\n{i}. r/{comment.subreddit} | score={comment.score} | action={result.predicted_action} | risk={result.risk_score}")
        print(f"target={result.target_detected_pred} | severity={result.predicted_severity} | codes={','.join(result.reason_codes)}")
        print(f"url={comment.source_url}")
        if show_text:
            print(f"text={comment.text[:500]}")


def write_csv(path: Path, rows: list[tuple[LiveComment, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "subreddit",
                "score",
                "source_url",
                "post_title",
                "text",
                "predicted_action",
                "target_detected_pred",
                "predicted_category",
                "predicted_severity",
                "risk_score",
                "reason_codes",
                "reason",
            ],
        )
        writer.writeheader()
        for comment, result in rows:
            writer.writerow(
                {
                    "subreddit": comment.subreddit,
                    "score": comment.score,
                    "source_url": comment.source_url,
                    "post_title": comment.post_title,
                    "text": comment.text,
                    "predicted_action": result.predicted_action,
                    "target_detected_pred": result.target_detected_pred,
                    "predicted_category": result.predicted_category,
                    "predicted_severity": result.predicted_severity,
                    "risk_score": result.risk_score,
                    "reason_codes": "|".join(result.reason_codes),
                    "reason": result.reason,
                }
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch live Reddit comments and run Moctale moderation locally.")
    parser.add_argument("--subreddits", default=",".join(DEFAULT_SUBREDDITS), help="Comma-separated subreddit names.")
    parser.add_argument("--post-sort", default="hot", choices=["hot", "new", "top", "controversial"])
    parser.add_argument("--comment-sort", default="controversial", choices=["confidence", "top", "new", "controversial", "old"])
    parser.add_argument("--posts-per-subreddit", type=int, default=4)
    parser.add_argument("--comments-per-post", type=int, default=80)
    parser.add_argument("--max-comments", type=int, default=80)
    parser.add_argument("--top", type=int, default=20, help="Number of highest-risk examples to print.")
    parser.add_argument("--hide-text", action="store_true", help="Hide comment text in terminal output.")
    parser.add_argument("--output", type=Path, help="Optional CSV path for full results.")
    parser.add_argument("--reddit-client-id", default=os.getenv("REDDIT_CLIENT_ID"), help="Optional Reddit app client id.")
    parser.add_argument("--reddit-client-secret", default=os.getenv("REDDIT_CLIENT_SECRET"), help="Optional Reddit app client secret.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    subreddits = [item.strip().strip("r/") for item in args.subreddits.split(",") if item.strip()]
    base_url = REDDIT_BASE
    headers: dict[str, str] = {}
    if args.reddit_client_id and args.reddit_client_secret:
        token = fetch_reddit_oauth_token(args.reddit_client_id, args.reddit_client_secret)
        base_url = REDDIT_OAUTH_BASE
        headers["Authorization"] = f"Bearer {token}"

    comments = fetch_live_comments(
        subreddits,
        base_url=base_url,
        headers=headers,
        post_sort=args.post_sort,
        comment_sort=args.comment_sort,
        posts_per_subreddit=args.posts_per_subreddit,
        comments_per_post=args.comments_per_post,
        max_comments=args.max_comments,
    )
    engine = ModerationEngine()
    results = engine.analyze_many(context_for(comment) for comment in comments)
    rows = list(zip(comments, results))
    print_results(rows, show_text=not args.hide_text, top=args.top)
    if args.output:
        write_csv(args.output, rows)
        print(f"\nwrote={args.output}")


if __name__ == "__main__":
    main()
