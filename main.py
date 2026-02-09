from __future__ import annotations

import argparse
import logging
import time
from typing import Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

import requests

from email_service import send_needs_response_email
from llm_service import classify_answer_required_post, generate_response
from subreddit_list import subreddits

BASE = "https://old.reddit.com"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"


def _get_json(url: str, params: Dict[str, str], timeout: int = 15) -> dict:
    headers = {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7",
        "Accept-Language": "en-US,en;q=0.9",
    }
    resp = requests.get(url, headers=headers, params=params, timeout=timeout)

    # Basic backoff for rate limiting
    if resp.status_code == 429:
        retry_after = int(resp.headers.get("retry-after", "5"))
        time.sleep(max(1, retry_after))
        resp = requests.get(url, headers=headers, params=params, timeout=timeout)

    resp.raise_for_status()
    return resp.json()


def fetch_posts_from_subreddit(
    subreddit: str,
    minutes: int = 15,
    limit_per_page: int = 100,
    pages_to_scan: int = 5,
) -> List[Dict[str, Optional[str]]]:
    """
    Returns list of dicts: {id, created_utc, title, body}
    Only includes posts created within the last `minutes`.
    """
    cutoff = time.time() - (minutes * 60)

    url = f"{BASE}/{subreddit}/new/.json"
    after = None
    out: List[Dict[str, Optional[str]]] = []

    for _ in range(pages_to_scan):
        params = {"limit": str(limit_per_page)}
        if after:
            params["after"] = after

        data = _get_json(url, params=params)

        children = data.get("data", {}).get("children", [])
        if not children:
            break

        # If we hit older than cutoff and listings are in descending time order,
        # we can stop early.
        oldest_in_page = None

        for child in children:
            post = child.get("data", {})
            created_utc = float(post.get("created_utc", 0.0))
            oldest_in_page = created_utc if oldest_in_page is None else min(oldest_in_page, created_utc)

            if created_utc >= cutoff:
                title = post.get("title")
                body = post.get("selftext") or ""  # empty for link posts
                out.append(
                    {
                        "id": post.get("id"),
                        "created_utc": created_utc,
                        "title": title,
                        "body": body,
                    }
                )

        after = data.get("data", {}).get("after")
        if not after:
            break

        if oldest_in_page is not None and oldest_in_page < cutoff:
            break

        # Small delay to be polite / avoid triggering limits
        time.sleep(0.3)

    # Newest first
    out.sort(key=lambda x: x["created_utc"] or 0, reverse=True)
    return out


def run_once(minutes: int = 180) -> None:
    """Run a single scrape cycle across all subreddits."""
    for subreddit in subreddits:
        try:
            print(f"Fetching posts from {subreddit}...")
            posts = fetch_posts_from_subreddit(subreddit, minutes=minutes, pages_to_scan=2)

            for post in posts:
                print("===")
                print(post["title"] or "")
                print()
                print(post["body"] or "")
            print("\n\n")
            for post in posts:
                if not post["body"] or post["body"].strip() == "":
                    continue
                answer_required = classify_answer_required_post(post["title"] or "", post["body"])
                print(f"Post ID: {post['id']}, Subject: {post['title'] or ''}, Needs answer: {answer_required}")
                if answer_required == "YES":
                    response = generate_response(
                        post["body"],
                    )
                    print(f"--- Post Content ---\n{post['body']}\n")
                    print(f"--- Generated Response ---\n{response}\n")
                    if post["id"]:
                        send_needs_response_email(
                            post_id=post["id"],
                            title=post["title"] or "",
                            body=post["body"],
                            generated_response=response,
                            subreddit=subreddit,
                        )
                        logging.info(f"Sent email for post ID {post['id']}")
            time.sleep(3)
        except Exception:
            logging.exception(f"Failed to process {subreddit}")
            continue


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes", type=int, default=180, help="Look back window in minutes (default: 180)")
    args = parser.parse_args()

    print(f"Starting scrape cycle (last {args.minutes} min)...")
    run_once(minutes=args.minutes)
    print("Scrape cycle complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
