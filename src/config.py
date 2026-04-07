"""
Blitzy Platform API Test Suite — Configuration Management Module

Provides the ``Settings`` class for centralized, environment-driven
configuration of the API test suite.  All environment-specific values
(base URLs, authentication tokens, project / run identifiers) are read
exclusively from environment variables or ``.env`` files — nothing
sensitive is ever hard-coded.

At import time this module calls ``load_dotenv()`` so that any ``.env``
file present in the repository root is loaded before the first
``Settings`` instance is created.

YAML-based supplementary configuration (endpoint paths, field name
variants, validation parameters) is loaded from
``config/settings.yaml`` when available, with sensible defaults applied
when the file is absent.

Exports
-------
Settings : class
    Pydantic ``BaseModel`` subclass encapsulating every configurable
    knob used by the test suite.
get_settings : function
    Convenience factory that returns a ``Settings`` instance populated
    from the current environment.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Load environment variables from .env (idempotent — safe to call many times)
# This MUST execute before any Settings instantiation so that os.getenv()
# picks up values defined in the .env file.
# ---------------------------------------------------------------------------
load_dotenv()


class Settings(BaseModel):
    """Centralized configuration for the Blitzy Platform API test suite.

    Combines four configuration sources in order of precedence:

    1. Explicit constructor keyword arguments (highest precedence)
    2. Environment variables / ``.env`` file values (via ``from_env()``)
    3. ``config/settings.yaml`` YAML overrides (endpoint paths, field names)
    4. Built-in defaults coded in the field definitions (lowest precedence)

    Fields
    ------
    base_url : str
        Platform API base URL, e.g. ``https://api.blitzy.com``.
    api_token : str
        Bearer authentication token for API access.
    test_project_id : str
        Project ID with existing code generation runs (used by most tests).
    test_run_id : str
        Specific run ID for targeted metering tests.
    test_timeout : int
        Timeout in seconds for every HTTP request during test execution.
    log_level : str
        Python-standard log level name (DEBUG | INFO | WARNING | ERROR).
    endpoint_paths : Dict[str, str]
        Mapping of logical endpoint keys to URL path segments.
    percent_complete_field_names : List[str]
        Accepted JSON field name variants for the percent-complete value
        (both ``percent_complete`` and ``percentComplete``).
    """

    # --- API Connection Settings (populated from environment) ---------------
    base_url: str = Field(
        default="",
        description="Blitzy Platform API base URL (e.g., https://api.blitzy.com)",
    )
    api_token: str = Field(
        default="",
        repr=False,
        description="Authentication bearer token for API access",
    )

    # --- Test Data Configuration (populated from environment) ---------------
    test_project_id: str = Field(
        default="",
        description="Project ID with existing code generation runs",
    )
    test_run_id: str = Field(
        default="",
        description="Specific run ID for targeted metering tests",
    )

    # --- Optional Runtime Configuration (env with sensible defaults) --------
    test_timeout: int = Field(
        default=30,
        description="Test execution timeout in seconds",
    )
    log_level: str = Field(
        default="INFO",
        description="Log level for test output (DEBUG, INFO, WARNING, ERROR)",
    )

    # --- Retry Configuration (populated from settings.yaml) -----------------
    retry_count: int = Field(
        default=3,
        ge=0,
        description=(
            "Number of retry attempts for transient network failures "
            "before marking a request as failed."
        ),
    )
    retry_delay: float = Field(
        default=1.0,
        ge=0.0,
        description=(
            "Seconds to wait between retry attempts (simple linear backoff)."
        ),
    )

    # --- Endpoint Configuration (typically from settings.yaml) --------------
    endpoint_paths: Dict[str, str] = Field(
        default_factory=lambda: {
            "runs_metering": "/runs/metering",
            "runs_metering_current": "/runs/metering/current",
            "project": "/project",
        },
        description="API endpoint path definitions keyed by logical name",
    )

    # --- Field Name Configuration (typically from settings.yaml) ------------
    percent_complete_field_names: List[str] = Field(
        default_factory=lambda: ["percent_complete", "percentComplete"],
        description="Accepted field name variants for the percent_complete value",
    )

    # -----------------------------------------------------------------------
    # Factory: create from environment + YAML
    # -----------------------------------------------------------------------
    @classmethod
    def from_env(cls) -> "Settings":
        """Create a ``Settings`` instance from environment variables and YAML.

        This is the primary entry-point for obtaining configuration.  The
        method:

        1. Calls ``load_dotenv()`` to ensure any ``.env`` file is loaded.
        2. Reads the six environment-variable-backed fields via
           ``os.getenv()``.
        3. Attempts to load ``config/settings.yaml`` for supplementary
           endpoint-path and field-name overrides.
        4. Merges everything into a new ``Settings`` object.

        Returns
        -------
        Settings
            Fully populated configuration instance.
        """
        # Ensure .env is loaded (idempotent)
        load_dotenv()

        # Read environment variables with safe defaults
        env_settings: Dict[str, Any] = {
            "base_url": os.getenv("BASE_URL", ""),
            "api_token": os.getenv("API_TOKEN", ""),
            "test_project_id": os.getenv("TEST_PROJECT_ID", ""),
            "test_run_id": os.getenv("TEST_RUN_ID", ""),
            "test_timeout": int(os.getenv("TEST_TIMEOUT", "30")),
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
        }

        # Load YAML config if available
        yaml_config: Optional[Dict[str, Any]] = cls._load_yaml_config()

        # Merge YAML-sourced values into the settings dict
        if yaml_config:
            if "endpoint_paths" in yaml_config:
                env_settings["endpoint_paths"] = yaml_config["endpoint_paths"]
            if "field_names" in yaml_config:
                field_names_block = yaml_config["field_names"]
                env_settings["percent_complete_field_names"] = (
                    field_names_block.get(
                        "percent_complete",
                        ["percent_complete", "percentComplete"],
                    )
                )
            # Load retry configuration from test_defaults block
            if "test_defaults" in yaml_config:
                test_defaults_block = yaml_config["test_defaults"]
                if "retry_count" in test_defaults_block:
                    env_settings["retry_count"] = int(
                        test_defaults_block["retry_count"]
                    )
                if "retry_delay" in test_defaults_block:
                    env_settings["retry_delay"] = float(
                        test_defaults_block["retry_delay"]
                    )

        return cls(**env_settings)

    # -----------------------------------------------------------------------
    # Internal: YAML loader
    # -----------------------------------------------------------------------
    @staticmethod
    def _load_yaml_config() -> Optional[dict]:
        """Load and parse ``config/settings.yaml`` if it exists.

        The method probes two file-system locations so that the
        configuration is found regardless of whether tests are executed
        from the repository root or from within a sub-package:

        1. ``<cwd>/config/settings.yaml``
        2. ``<project_root>/config/settings.yaml`` (derived from this
           module's ``__file__`` path, going up two directory levels from
           ``src/config.py``).

        Returns
        -------
        dict or None
            Parsed YAML contents, or ``None`` when the file cannot be
            located.

        Notes
        -----
        Uses ``yaml.safe_load()`` exclusively — ``yaml.load()`` with an
        unrestricted ``Loader`` is never used, preventing arbitrary
        code-execution vulnerabilities.
        """
        yaml_paths: List[str] = [
            os.path.join(os.getcwd(), "config", "settings.yaml"),
            os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "config",
                "settings.yaml",
            ),
        ]
        for yaml_path in yaml_paths:
            if os.path.exists(yaml_path):
                with open(yaml_path, "r", encoding="utf-8") as fh:
                    return yaml.safe_load(fh)
        return None

    # -----------------------------------------------------------------------
    # Validation: required settings check
    # -----------------------------------------------------------------------
    def validate_required_settings(self) -> None:
        """Raise a descriptive ``ValueError`` if critical settings are empty.

        Checks that ``base_url``, ``api_token``, and ``test_project_id``
        are all populated with non-empty strings.  When any are missing
        the error message lists every absent variable by its
        environment-variable name and points the user to ``.env.example``
        for guidance.

        Raises
        ------
        ValueError
            If one or more of ``BASE_URL``, ``API_TOKEN``, or
            ``TEST_PROJECT_ID`` is not set.
        """
        missing: List[str] = []
        if not self.base_url:
            missing.append("BASE_URL")
        if not self.api_token:
            missing.append("API_TOKEN")
        if not self.test_project_id:
            missing.append("TEST_PROJECT_ID")

        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}. "
                f"Please set them in your .env file or environment. "
                f"See .env.example for reference."
            )

    # -----------------------------------------------------------------------
    # Convenience: full URL construction
    # -----------------------------------------------------------------------
    def get_endpoint_url(self, endpoint_key: str) -> str:
        """Build the full URL for a named API endpoint.

        Parameters
        ----------
        endpoint_key : str
            Logical endpoint name matching a key in ``endpoint_paths``
            (e.g. ``"runs_metering"``, ``"runs_metering_current"``,
            ``"project"``).

        Returns
        -------
        str
            Absolute URL formed by joining ``base_url`` with the
            endpoint's path segment.

        Raises
        ------
        KeyError
            If ``endpoint_key`` does not exist in ``endpoint_paths``.
        """
        if endpoint_key not in self.endpoint_paths:
            raise KeyError(
                f"Unknown endpoint key '{endpoint_key}'. "
                f"Available keys: {list(self.endpoint_paths.keys())}"
            )
        return f"{self.base_url.rstrip('/')}{self.endpoint_paths[endpoint_key]}"


# ---------------------------------------------------------------------------
# Module-level convenience function
# ---------------------------------------------------------------------------
def get_settings() -> Settings:
    """Create and return a ``Settings`` instance from the environment.

    This is a thin wrapper around ``Settings.from_env()`` provided for
    callers that prefer a plain-function API over the class-method style.

    Returns
    -------
    Settings
        Fully populated configuration instance.
    """
    return Settings.from_env()
