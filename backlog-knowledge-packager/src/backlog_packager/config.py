"""Configuration loading for the collect command."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


DEFAULT_DOMAIN = "backlog.com"
DEFAULT_TARGETS = ("documents", "wiki", "shared-files")
VALID_TARGETS = frozenset(DEFAULT_TARGETS)


class ConfigError(ValueError):
    """Raised when required CLI/env configuration is missing or invalid."""


@dataclass(frozen=True, slots=True)
class CollectConfig:
    space: str
    domain: str
    api_key: str
    project: str
    targets: tuple[str, ...]
    output: Path

    @property
    def base_url(self) -> str:
        return f"https://{self.space}.{self.domain}"


def load_collect_config(
    *,
    project: str | None,
    space: str | None = None,
    domain: str | None = None,
    targets: str | None = None,
    output: str | Path | None = None,
    env_file: str | Path | None = None,
) -> CollectConfig:
    """Load .env values and apply CLI argument overrides."""

    load_dotenv(dotenv_path=env_file)
    resolved_project = _required("project", project or os.getenv("BACKLOG_PROJECT_KEY"))
    resolved_space = _required("BACKLOG_SPACE_KEY", space or os.getenv("BACKLOG_SPACE_KEY"))
    api_key = _required("BACKLOG_API_KEY", os.getenv("BACKLOG_API_KEY"))
    resolved_domain = (domain or os.getenv("BACKLOG_DOMAIN") or DEFAULT_DOMAIN).strip()
    resolved_targets = parse_targets(targets)
    resolved_output = Path(output) if output is not None else Path("output") / resolved_project
    return CollectConfig(
        space=resolved_space,
        domain=resolved_domain,
        api_key=api_key,
        project=resolved_project,
        targets=resolved_targets,
        output=resolved_output,
    )


def parse_targets(value: str | None) -> tuple[str, ...]:
    if value is None or value.strip() == "":
        return DEFAULT_TARGETS
    targets = tuple(part.strip() for part in value.split(",") if part.strip())
    invalid = sorted(set(targets) - VALID_TARGETS)
    if invalid:
        raise ConfigError(f"invalid targets: {', '.join(invalid)}")
    if not targets:
        raise ConfigError("targets must not be empty")
    return targets


def _required(name: str, value: str | None) -> str:
    if value is None or value.strip() == "":
        raise ConfigError(f"{name} is required")
    return value.strip()
