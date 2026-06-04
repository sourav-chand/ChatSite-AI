"""Smoke tests for the chunking strategies."""
import pytest

from app.chunking.strategies import chunk_fixed, chunk_recursive, count_tokens


def test_recursive_respects_chunk_size():
    text = ("Sentence one. " * 200) + "\n\n" + ("Sentence two. " * 200)
    chunks = chunk_recursive(text, chunk_size=128, overlap=16)
    assert len(chunks) > 1
    assert all(c.token_count <= 160 for c in chunks)


def test_fixed_produces_ordered_chunks():
    text = "word " * 1000
    chunks = chunk_fixed(text, chunk_size=100, overlap=10)
    assert len(chunks) > 1
    assert chunks[0].chunk_index == 0
    assert chunks[-1].chunk_index == len(chunks) - 1


def test_count_tokens_positive():
    assert count_tokens("hello world") > 0
