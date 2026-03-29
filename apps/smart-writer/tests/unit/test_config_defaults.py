"""Tests for environment-driven config (no network)."""

import os

import pytest

from app.config import (
    DEFAULT_MAX_CONCURRENT_LLM,
    get_audit_timeout_sec,
    get_llm_retry_config,
    get_max_concurrent_llm,
)


def test_get_max_concurrent_llm_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SMART_WRITER_MAX_CONCURRENT_LLM", raising=False)
    assert get_max_concurrent_llm() == DEFAULT_MAX_CONCURRENT_LLM


def test_get_max_concurrent_llm_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMART_WRITER_MAX_CONCURRENT_LLM", "3")
    assert get_max_concurrent_llm() == 3


def test_get_max_concurrent_llm_invalid_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMART_WRITER_MAX_CONCURRENT_LLM", "not-an-int")
    assert get_max_concurrent_llm() == DEFAULT_MAX_CONCURRENT_LLM


def test_get_max_concurrent_llm_clamped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMART_WRITER_MAX_CONCURRENT_LLM", "999")
    assert get_max_concurrent_llm() == 16


def test_get_audit_timeout_none_when_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMART_WRITER_AUDIT_TIMEOUT_SEC", "0")
    assert get_audit_timeout_sec() is None


def test_get_audit_timeout_positive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMART_WRITER_AUDIT_TIMEOUT_SEC", "120")
    assert get_audit_timeout_sec() == 120.0


def test_get_llm_retry_config_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SMART_WRITER_LLM_RETRY_MAX_ATTEMPTS", raising=False)
    monkeypatch.delenv("SMART_WRITER_LLM_RETRY_BASE_SEC", raising=False)
    monkeypatch.delenv("SMART_WRITER_LLM_RETRY_MAX_SEC", raising=False)
    n, base, cap = get_llm_retry_config()
    assert n >= 1
    assert base > 0
    assert cap >= base
