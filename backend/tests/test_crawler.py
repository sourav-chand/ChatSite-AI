"""Smoke tests for the crawler URL normalizer."""
from app.crawler.async_crawler import normalize_url, is_binary


def test_normalize_strips_fragment():
    assert normalize_url("https://Example.com/foo#bar") == "https://example.com/foo"


def test_normalize_lowercases_host():
    assert normalize_url("HTTPS://Example.COM/Path") == "https://example.com/Path"


def test_is_binary_skips_assets():
    assert is_binary("https://x.com/logo.png")
    assert is_binary("https://x.com/file.pdf")
    assert not is_binary("https://x.com/about")
