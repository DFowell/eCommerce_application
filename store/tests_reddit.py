"""Tests for the Reddit helper and the /reddit/ view (Reddit is mocked)."""
from unittest.mock import MagicMock, patch

import requests
from django.test import TestCase
from django.urls import reverse

from functions.reddit import USER_AGENT, get_subreddit_posts

SAMPLE = {
    "data": {
        "children": [
            {"data": {"title": "Hello Django", "author": "alice", "permalink": "/r/django/comments/abc/hello/", "score": 42}},
            {"data": {"title": "Second", "author": "bob", "permalink": "/r/django/comments/def/second/", "score": 7}},
        ]
    }
}


def fake_response(payload=SAMPLE, status_ok=True):
    """Return a fake ``requests`` response with the given JSON and status."""
    resp = MagicMock()
    resp.json.return_value = payload
    if not status_ok:
        resp.raise_for_status.side_effect = requests.HTTPError("429")
    return resp


class HelperTests(TestCase):
    """Tests for functions.reddit.get_subreddit_posts."""

    @patch("functions.reddit.requests.get")
    def test_parses_posts_and_sends_user_agent(self, mock_get):
        """Posts are parsed into dicts and a User-Agent header is sent."""
        mock_get.return_value = fake_response()
        posts = get_subreddit_posts("django")
        self.assertEqual(posts[0], {"title": "Hello Django", "author": "alice",
                                    "url": "https://www.reddit.com/r/django/comments/abc/hello/", "score": 42})
        self.assertEqual(len(posts), 2)
        args, kwargs = mock_get.call_args
        self.assertEqual(args[0], "https://www.reddit.com/r/django.json")
        self.assertEqual(kwargs["headers"]["User-Agent"], USER_AGENT)

    @patch("functions.reddit.requests.get")
    def test_bad_status_raises(self, mock_get):
        """An HTTP error status raises a requests exception."""
        mock_get.return_value = fake_response(status_ok=False)
        with self.assertRaises(requests.RequestException):
            get_subreddit_posts()

    @patch("functions.reddit.requests.get")
    def test_unexpected_body_raises_valueerror(self, mock_get):
        """A body without the expected structure raises ValueError."""
        mock_get.return_value = fake_response(payload={"oops": 1})
        with self.assertRaises(ValueError):
            get_subreddit_posts()


class ViewTests(TestCase):
    """Tests for the reddit_feed view."""

    @patch("store.views.get_subreddit_posts")
    def test_view_shows_posts(self, mock_posts):
        """Title, author and link of each post are displayed."""
        mock_posts.return_value = [{"title": "Hello Django", "author": "alice", "url": "https://www.reddit.com/x", "score": 1}]
        resp = self.client.get(reverse("reddit_feed"))
        self.assertContains(resp, "Hello Django")
        self.assertContains(resp, "u/alice")
        self.assertContains(resp, 'href="https://www.reddit.com/x"')

    @patch("store.views.get_subreddit_posts", side_effect=requests.ConnectionError("down"))
    def test_view_handles_failure(self, _):
        """A Reddit failure shows a friendly message instead of crashing."""
        resp = self.client.get(reverse("reddit_feed"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "couldn&#x27;t load the Reddit feed")
