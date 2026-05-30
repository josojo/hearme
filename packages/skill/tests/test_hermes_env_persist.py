"""Tests for ~/.hermes/.env upsert (`upsert_hermes_env`) + onboard/install-plugin
persistence (`_persist_broker_urls`).

The bug this targets: a user runs `hearme-skill onboard --broker-url http://prod:8000
...`, onboarding succeeds, but the Hermes cron job (started by systemd in a
fresh process) doesn't inherit that arg — it falls back to the localhost
default in config.py and the `list_open_questions` tool dies with
`httpx.ConnectError: All connection attempts failed`. Persisting the URL the
user actually onboarded against to ~/.hermes/.env fixes it because the
gateway/cron units load that file.
"""

from __future__ import annotations

from pathlib import Path

from hearme_skill import skill as skill_mod


def test_upsert_writes_new_file(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    written = skill_mod.upsert_hermes_env(
        {"HEARME_SKILL_BROKER_URL": "http://prod:8000"}, env_path=env_path
    )
    assert written == env_path
    assert env_path.read_text() == "HEARME_SKILL_BROKER_URL=http://prod:8000\n"


def test_upsert_creates_parent_dir(tmp_path: Path) -> None:
    env_path = tmp_path / "subdir" / ".env"
    skill_mod.upsert_hermes_env(
        {"HEARME_SKILL_BROKER_URL": "http://prod:8000"}, env_path=env_path
    )
    assert env_path.exists()


def test_upsert_preserves_unrelated_keys_and_comments(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "# some comment\n"
        "GATEWAY_ALLOW_ALL_USERS=true\n"
        "\n"
        "OTHER_VAR=keepme\n"
    )
    skill_mod.upsert_hermes_env(
        {"HEARME_SKILL_BROKER_URL": "http://prod:8000"}, env_path=env_path
    )
    text = env_path.read_text()
    assert "# some comment" in text
    assert "GATEWAY_ALLOW_ALL_USERS=true" in text
    assert "OTHER_VAR=keepme" in text
    assert "HEARME_SKILL_BROKER_URL=http://prod:8000" in text


def test_upsert_replaces_existing_value(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "HEARME_SKILL_BROKER_URL=http://old:8000\n"
        "OTHER=stays\n"
    )
    skill_mod.upsert_hermes_env(
        {"HEARME_SKILL_BROKER_URL": "http://new:8000"}, env_path=env_path
    )
    lines = env_path.read_text().splitlines()
    assert "HEARME_SKILL_BROKER_URL=http://new:8000" in lines
    assert "HEARME_SKILL_BROKER_URL=http://old:8000" not in lines
    assert "OTHER=stays" in lines


def test_upsert_replaces_export_prefixed_key(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("export HEARME_SKILL_BROKER_URL=http://old:8000\n")
    skill_mod.upsert_hermes_env(
        {"HEARME_SKILL_BROKER_URL": "http://new:8000"}, env_path=env_path
    )
    text = env_path.read_text()
    # The replaced line drops the `export ` prefix — fine for systemd
    # EnvironmentFile (which doesn't honor `export` anyway).
    assert "HEARME_SKILL_BROKER_URL=http://new:8000" in text
    assert "http://old:8000" not in text


def test_upsert_handles_multiple_keys_some_existing(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("HEARME_SKILL_BROKER_URL=http://old:8000\n")
    skill_mod.upsert_hermes_env(
        {
            "HEARME_SKILL_BROKER_URL": "http://new:8000",
            "HEARME_SKILL_SELF_BRIDGE_URL": "http://new:8787",
        },
        env_path=env_path,
    )
    text = env_path.read_text()
    assert "HEARME_SKILL_BROKER_URL=http://new:8000" in text
    assert "HEARME_SKILL_SELF_BRIDGE_URL=http://new:8787" in text
    assert text.count("HEARME_SKILL_BROKER_URL") == 1


def test_upsert_is_idempotent(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    payload = {"HEARME_SKILL_BROKER_URL": "http://prod:8000"}
    skill_mod.upsert_hermes_env(payload, env_path=env_path)
    first = env_path.read_text()
    skill_mod.upsert_hermes_env(payload, env_path=env_path)
    assert env_path.read_text() == first


def test_persist_broker_urls_writes_only_explicit(tmp_path: Path, monkeypatch) -> None:
    env_path = tmp_path / ".env"
    monkeypatch.setattr(skill_mod, "_hermes_env_path", lambda: env_path)
    result = skill_mod._persist_broker_urls(
        broker_url="http://prod:8000",
        bridge_url="http://localhost:8787",  # equals the default -> not persisted
        broker_default="http://localhost:8000",
        bridge_default="http://localhost:8787",
    )
    assert result is not None
    path, written = result
    assert path == env_path
    assert written == {"HEARME_SKILL_BROKER_URL": "http://prod:8000"}
    assert env_path.read_text() == "HEARME_SKILL_BROKER_URL=http://prod:8000\n"


def test_persist_broker_urls_skips_when_all_defaults(tmp_path: Path, monkeypatch) -> None:
    env_path = tmp_path / ".env"
    monkeypatch.setattr(skill_mod, "_hermes_env_path", lambda: env_path)
    result = skill_mod._persist_broker_urls(
        broker_url="http://localhost:8000",
        bridge_url="http://localhost:8787",
        broker_default="http://localhost:8000",
        bridge_default="http://localhost:8787",
    )
    assert result is None
    assert not env_path.exists()


def test_persist_broker_urls_both_when_both_explicit(tmp_path: Path, monkeypatch) -> None:
    env_path = tmp_path / ".env"
    monkeypatch.setattr(skill_mod, "_hermes_env_path", lambda: env_path)
    result = skill_mod._persist_broker_urls(
        broker_url="http://prod:8000",
        bridge_url="http://prod:8787",
        broker_default="http://localhost:8000",
        bridge_default="http://localhost:8787",
    )
    assert result is not None
    _, written = result
    assert written == {
        "HEARME_SKILL_BROKER_URL": "http://prod:8000",
        "HEARME_SKILL_SELF_BRIDGE_URL": "http://prod:8787",
    }
