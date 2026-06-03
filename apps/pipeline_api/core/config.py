from __future__ import annotations

import os
import warnings
from dataclasses import dataclass
from typing import Callable, TypeVar

from dotenv import load_dotenv


T = TypeVar("T")

if os.getenv("KGSAUTO_LOAD_DOTENV", "true").lower() not in {"0", "false", "no", "off"}:
    load_dotenv()


class ConfigValidationError(RuntimeError):
    """Raised when a runtime profile is missing required configuration."""


@dataclass(frozen=True)
class EnvValue:
    value: str | None
    source: str | None = None
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class LLMSettings:
    provider: str
    model: str
    openai_compatible_api_key: str | None
    openai_compatible_api_key_source: str | None
    openai_compatible_base_url: str | None
    openai_compatible_model: str | None
    google_api_key: str | None
    default_model: str | None
    openai_api_key: str | None
    openai_base_url: str | None
    openai_model: str | None
    cx_api_key: str | None


@dataclass(frozen=True)
class CoreSettings:
    strict: bool
    llm: LLMSettings

    @classmethod
    def from_env(cls) -> "CoreSettings":
        openai_compatible_key = _env_alias(
            "OPENAI_COMPATIBLE_API_KEY",
            aliases=("OPENAI_API_KEY", "CX_API_KEY"),
        )

        return cls(
            strict=_env_bool("CONFIG_STRICT", False),
            llm=LLMSettings(
                provider=_env_str("LLM_PROVIDER", "OpenAICompatible"),
                model=_env_str("LLM_MODEL", "cx/gpt-5.3-codex"),
                openai_compatible_api_key=openai_compatible_key.value,
                openai_compatible_api_key_source=openai_compatible_key.source,
                openai_compatible_base_url=_env_optional("OPENAI_COMPATIBLE_BASE_URL"),
                openai_compatible_model=_env_optional("OPENAI_COMPATIBLE_MODEL"),
                google_api_key=_env_optional("GOOGLE_API_KEY"),
                default_model=_env_str("DEFAULT_MODEL", "gemini-2.5-flash"),
                openai_api_key=_env_optional("OPENAI_API_KEY"),
                openai_base_url=_env_optional("OPENAI_BASE_URL"),
                openai_model=_env_optional("OPENAI_MODEL"),
                cx_api_key=_env_optional("CX_API_KEY"),
            ),
        )


def _env_optional(name: str) -> str | None:
    value = os.getenv(name)
    return value if value else None


def _env_str(name: str, default: str) -> str:
    return _env_optional(name) or default


def _env_bool(name: str, default: bool) -> bool:
    value = _env_optional(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ConfigValidationError(f"Invalid boolean value for {name}: {value!r}")


def _parse_env(name: str, default: T, parser: Callable[[str], T]) -> T:
    value = _env_optional(name)
    if value is None:
        return default
    try:
        return parser(value)
    except ValueError as exc:
        raise ConfigValidationError(f"Invalid value for {name}: {value!r}") from exc


def _env_alias(canonical: str, aliases: tuple[str, ...] = (), default: str | None = None) -> EnvValue:
    canonical_value = _env_optional(canonical)
    alias_values = [(alias, value) for alias in aliases if (value := _env_optional(alias))]

    if canonical_value:
        _warn_conflicting_aliases(canonical, canonical_value, alias_values)
        return EnvValue(canonical_value, canonical, aliases)
    if alias_values:
        source, value = alias_values[0]
        _warn_deprecated_alias(canonical, source)
        _warn_conflicting_aliases(source, value, alias_values[1:])
        return EnvValue(value, source, aliases)
    return EnvValue(default, None, aliases)


def _warn_deprecated_alias(canonical: str, alias: str) -> None:
    warnings.warn(
        f"{alias} is being used as a legacy alias for {canonical}. Prefer {canonical}.",
        DeprecationWarning,
        stacklevel=3,
    )


def _warn_conflicting_aliases(canonical: str, canonical_value: str, alias_values: list[tuple[str, str]]) -> None:
    conflicts = [name for name, value in alias_values if value != canonical_value]
    if not conflicts:
        return
    message = f"Conflicting config values for {canonical} and aliases: {', '.join(conflicts)}. Using {canonical}."
    if _env_bool("CONFIG_STRICT", False):
        raise ConfigValidationError(message)
    warnings.warn(message, RuntimeWarning, stacklevel=3)


def validate_settings(profile: str = "base") -> None:
    validators = {
        "base": _validate_base,
        "extraction": _validate_extraction,
    }
    try:
        validator = validators[profile]
    except KeyError as exc:
        raise ConfigValidationError(f"Unknown config validation profile: {profile}") from exc
    validator()


def _validate_base() -> None:
    return None


def _validate_extraction() -> None:
    _validate_llm_provider("extraction")


def _validate_llm_provider(profile: str) -> None:
    provider = settings.llm.provider.lower()
    if provider in {"openai-compatible", "openaicompatible"}:
        _require(
            profile=profile,
            value=settings.llm.openai_compatible_api_key,
            canonical="OPENAI_COMPATIBLE_API_KEY",
            aliases=("OPENAI_API_KEY", "CX_API_KEY"),
        )
        _require(profile=profile, value=settings.llm.openai_compatible_base_url, canonical="OPENAI_COMPATIBLE_BASE_URL")
    elif provider == "gemini":
        _require(profile=profile, value=settings.llm.google_api_key, canonical="GOOGLE_API_KEY")
    elif provider == "openai":
        _require(profile=profile, value=settings.llm.openai_api_key, canonical="OPENAI_API_KEY")


def _require(profile: str, value: str | None, canonical: str, aliases: tuple[str, ...] = ()) -> None:
    if value:
        return
    alias_text = f" Accepted legacy aliases: {', '.join(aliases)}." if aliases else ""
    raise ConfigValidationError(
        f"Missing required config for profile '{profile}': {canonical}.{alias_text} "
        f"Set {canonical} in the backend .env file."
    )


settings = CoreSettings.from_env()

LLM_PROVIDER: str = settings.llm.provider
LLM_MODEL: str = settings.llm.model

OPENAI_COMPATIBLE_API_KEY: str | None = settings.llm.openai_compatible_api_key
OPENAI_COMPATIBLE_BASE_URL: str | None = settings.llm.openai_compatible_base_url
OPENAI_COMPATIBLE_MODEL: str | None = settings.llm.openai_compatible_model

GOOGLE_API_KEY: str | None = settings.llm.google_api_key
DEFAULT_MODEL: str | None = settings.llm.default_model

OPENAI_API_KEY: str | None = settings.llm.openai_api_key
OPENAI_BASE_URL: str | None = settings.llm.openai_base_url
OPENAI_MODEL: str | None = settings.llm.openai_model
CX_API_KEY: str | None = settings.llm.cx_api_key
