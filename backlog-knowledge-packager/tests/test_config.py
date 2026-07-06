from pathlib import Path

import pytest

from backlog_packager.config import ConfigError, load_collect_config, parse_targets


def test_load_collect_config_from_env_file_with_cli_overrides(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("BACKLOG_SPACE_KEY", raising=False)
    monkeypatch.delenv("BACKLOG_API_KEY", raising=False)
    monkeypatch.delenv("BACKLOG_DOMAIN", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "BACKLOG_SPACE_KEY=env-space",
                "BACKLOG_API_KEY=secret",
                "BACKLOG_PROJECT_KEY=ENVPRJ",
                "BACKLOG_DOMAIN=backlog.jp",
            ]
        ),
        encoding="utf-8",
    )

    config = load_collect_config(
        project="PRJ",
        space="cli-space",
        targets="documents,wiki",
        output=tmp_path / "out",
        env_file=env_file,
    )

    assert config.space == "cli-space"
    assert config.project == "PRJ"
    assert config.domain == "backlog.jp"
    assert config.api_key == "secret"
    assert config.targets == ("documents", "wiki")
    assert config.output == tmp_path / "out"


def test_load_collect_config_can_read_project_from_env_file(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("BACKLOG_SPACE_KEY", raising=False)
    monkeypatch.delenv("BACKLOG_API_KEY", raising=False)
    monkeypatch.delenv("BACKLOG_PROJECT_KEY", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "BACKLOG_SPACE_KEY=env-space",
                "BACKLOG_API_KEY=secret",
                "BACKLOG_PROJECT_KEY=ENVPRJ",
            ]
        ),
        encoding="utf-8",
    )

    config = load_collect_config(project=None, env_file=env_file)

    assert config.project == "ENVPRJ"
    assert config.output == Path("output") / "ENVPRJ"


def test_parse_targets_rejects_unknown_value() -> None:
    with pytest.raises(ConfigError):
        parse_targets("documents,issues")


def test_load_collect_config_rejects_invalid_space_key(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("BACKLOG_SPACE_KEY", raising=False)
    monkeypatch.delenv("BACKLOG_API_KEY", raising=False)
    monkeypatch.delenv("BACKLOG_PROJECT_KEY", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "BACKLOG_SPACE_KEY=invalid_space",
                "BACKLOG_API_KEY=secret",
                "BACKLOG_PROJECT_KEY=ENVPRJ",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="BACKLOG_SPACE_KEY"):
        load_collect_config(project=None, env_file=env_file)


def test_missing_required_config_raises(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("BACKLOG_SPACE_KEY", raising=False)
    monkeypatch.delenv("BACKLOG_API_KEY", raising=False)

    with pytest.raises(ConfigError):
        load_collect_config(project="PRJ", env_file=tmp_path / ".env")
