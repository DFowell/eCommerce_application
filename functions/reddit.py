"""Helper for fetching posts from a subreddit via Reddit's public JSON feed."""
import logging

import requests

logger = logging.getLogger(__name__)

# Reddit rejects requests that don't identify themselves, so we always send a User-Agent.
USER_AGENT = "ecommerce-django-app/1.0 (learning project)"


def get_subreddit_posts(subreddit="django", limit=10, timeout=10):
    """Return a list of posts from r/<subreddit> as dicts:
    {"title", "author", "url", "score"}.

    `url` is the link to the original Reddit post.
    Raises requests.RequestException (network problem or bad status) or
    ValueError (unexpected response body) so the caller can show a friendly error.
    """
    # 1. build the request URL
    url = f"https://www.reddit.com/r/{subreddit}.json"

    # 2. send a GET request with a User-Agent header
    response = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        params={"limit": limit},
        timeout=timeout,
    )
    response.raise_for_status()

    # 3. parse the JSON response into a list of posts
    try:
        children = response.json()["data"]["children"]
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Unexpected response from Reddit") from exc

    posts = []
    for child in children:
        data = child.get("data", {})
        posts.append(
            {
                "title": data.get("title", "(no title)"),
                "author": data.get("author", "[unknown]"),
                "url": "https://www.reddit.com" + data.get("permalink", ""),
                "score": data.get("score", 0),
            }
        )
    return posts
