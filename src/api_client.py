"""
Blitzy Platform API Test Suite — HTTP Client Wrapper

Provides the :class:`APIClient` class that encapsulates all HTTP
communication with the three target Blitzy Platform API endpoints:

* ``GET /runs/metering``       — historical run metering data
* ``GET /runs/metering/current`` — live / in-progress run metering
* ``GET /project``             — project details with inline metering

Design principles
-----------------
* **Session reuse** — a single :class:`requests.Session` is created in the
  constructor for connection pooling and persistent header injection
  (``Authorization``, ``Content-Type``, ``Accept``).
* **Configuration-driven** — base URL, bearer token, request timeout, and
  endpoint paths are all sourced from a :class:`src.config.Settings`
  instance.  Nothing is hard-coded.
* **Transparent error propagation** — HTTP errors (4xx / 5xx) raise
  :class:`requests.exceptions.HTTPError`; connection and timeout errors
  likewise propagate to the caller so that test assertions receive the
  original exception context.
* **DRY internals** — the three public endpoint methods delegate to a
  single private helper, :meth:`_make_request`, that handles URL
  construction, request dispatch, status checking, and JSON parsing.

Exports
-------
APIClient : class
    Authenticated HTTP client for the three target Blitzy Platform API
    endpoints.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

import requests

from src.config import Settings

logger = logging.getLogger(__name__)


class APIClient:
    """Authenticated HTTP client for Blitzy Platform API endpoints.

    Wraps the :mod:`requests` library with connection pooling, bearer
    token authentication, and configurable timeouts.  Each of the three
    target endpoints has a dedicated convenience method that constructs
    the correct URL and query-parameter set.

    Parameters
    ----------
    settings : Settings
        Configuration instance providing ``base_url``, ``api_token``,
        ``test_timeout``, and ``endpoint_paths``.

    Attributes
    ----------
    settings : Settings
        The configuration instance supplied at construction time.
    session : requests.Session
        Persistent HTTP session with default ``Authorization``,
        ``Content-Type``, and ``Accept`` headers already set.
    base_url : str
        Normalised (trailing-slash-stripped) API base URL derived from
        ``settings.base_url``.

    Examples
    --------
    >>> from src.config import Settings
    >>> settings = Settings(
    ...     base_url="https://api.blitzy.com",
    ...     api_token="tok_abc123",
    ... )
    >>> client = APIClient(settings)
    >>> data = client.get_runs_metering("proj_42")  # doctest: +SKIP
    """

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    def __init__(self, settings: Settings) -> None:
        """Initialise the API client with the given *settings*.

        Creates a :class:`requests.Session` pre-configured with:

        * ``Authorization: Bearer <api_token>``
        * ``Content-Type: application/json``
        * ``Accept: application/json``

        The ``base_url`` is stored after stripping any trailing ``/``
        so that endpoint-path concatenation never produces a double
        slash (``//``).

        Parameters
        ----------
        settings : Settings
            Configuration providing ``base_url``, ``api_token``,
            ``test_timeout``, and ``endpoint_paths``.
        """
        self.settings: Settings = settings
        self.session: requests.Session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {settings.api_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )
        self.base_url: str = settings.base_url.rstrip("/")

    # ------------------------------------------------------------------
    # Public endpoint methods
    # ------------------------------------------------------------------
    def get_runs_metering(self, project_id: str) -> dict:
        """Retrieve metering data for code-generation runs of a project.

        Calls ``GET /runs/metering?projectId=<project_id>`` and returns
        the parsed JSON response.

        Parameters
        ----------
        project_id : str
            Identifier of the project whose historical run-metering
            records should be retrieved.

        Returns
        -------
        dict
            Parsed JSON body.  Typically an array (or wrapper object)
            of run-metering records, each expected to contain a
            ``percent_complete`` (or ``percentComplete``) field.

        Raises
        ------
        requests.exceptions.HTTPError
            If the server responds with a 4xx or 5xx status code.
        requests.exceptions.ConnectionError
            If a network-level connection cannot be established.
        requests.exceptions.Timeout
            If the request exceeds ``settings.test_timeout`` seconds.
        """
        endpoint: str = self.settings.endpoint_paths.get(
            "runs_metering", "/runs/metering"
        )
        params: dict = {"projectId": project_id}
        return self._make_request("GET", endpoint, params=params)

    def get_runs_metering_current(self) -> dict:
        """Retrieve metering data for the currently active run.

        Calls ``GET /runs/metering/current`` with no required query
        parameters and returns the parsed JSON response.

        Returns
        -------
        dict
            Parsed JSON body representing the active run's metering
            data, expected to include a ``percent_complete`` (or
            ``percentComplete``) field reflecting real-time progress.

        Raises
        ------
        requests.exceptions.HTTPError
            If the server responds with a 4xx or 5xx status code.
            A ``404`` may indicate that no run is currently active.
        requests.exceptions.ConnectionError
            If a network-level connection cannot be established.
        requests.exceptions.Timeout
            If the request exceeds ``settings.test_timeout`` seconds.
        """
        endpoint: str = self.settings.endpoint_paths.get(
            "runs_metering_current", "/runs/metering/current"
        )
        return self._make_request("GET", endpoint)

    def get_project(self, project_id: str) -> dict:
        """Retrieve project details including inline metering data.

        Calls ``GET /project?id=<project_id>`` and returns the parsed
        JSON response.

        Parameters
        ----------
        project_id : str
            Identifier of the project whose details (with embedded
            metering block) should be retrieved.

        Returns
        -------
        dict
            Parsed JSON body representing the project, containing a
            nested metering object with a ``percent_complete`` (or
            ``percentComplete``) field.

        Raises
        ------
        requests.exceptions.HTTPError
            If the server responds with a 4xx or 5xx status code.
        requests.exceptions.ConnectionError
            If a network-level connection cannot be established.
        requests.exceptions.Timeout
            If the request exceeds ``settings.test_timeout`` seconds.
        """
        endpoint: str = self.settings.endpoint_paths.get("project", "/project")
        params: dict = {"id": project_id}
        return self._make_request("GET", endpoint, params=params)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
    ) -> Any:
        """Execute an HTTP request with retry logic and return the parsed JSON body.

        This is the single internal choke-point through which every
        public endpoint method dispatches its request.  It handles:

        1. URL construction by joining ``self.base_url`` with *endpoint*.
        2. Request dispatch via ``self.session.request()`` with retry
           logic for transient failures (connection errors, timeouts,
           and server-side 5xx errors).
        3. HTTP-error detection via ``Response.raise_for_status()``.
        4. JSON response parsing via ``Response.json()``.

        Retry behaviour is governed by ``settings.retry_count`` and
        ``settings.retry_delay``.  Client-side errors (4xx) are **not**
        retried because they typically indicate a permanent problem
        (bad credentials, missing resource, invalid parameters).

        Parameters
        ----------
        method : str
            HTTP verb (e.g. ``"GET"``).
        endpoint : str
            URL path segment to append to ``self.base_url``
            (e.g. ``"/runs/metering"``).
        params : dict or None, optional
            Query-string parameters to include in the request.

        Returns
        -------
        Any
            The parsed JSON body of the response.  In practice this is
            almost always a :class:`dict`, but the return type is
            annotated as :data:`Any` because ``response.json()`` can
            technically return any JSON-compatible type.

        Raises
        ------
        requests.exceptions.HTTPError
            If the server responds with a 4xx or 5xx status code and
            all retry attempts have been exhausted.
        requests.exceptions.ConnectionError
            If a network-level connection cannot be established after
            all retry attempts.
        requests.exceptions.Timeout
            If every attempt exceeds ``settings.test_timeout`` seconds.
        ValueError
            If the response body is not valid JSON.
        """
        url: str = f"{self.base_url}{endpoint}"
        max_attempts: int = 1 + max(0, self.settings.retry_count)
        last_exception: Optional[Exception] = None

        for attempt in range(1, max_attempts + 1):
            try:
                logger.debug(
                    "API request: %s %s params=%s (attempt %d/%d)",
                    method,
                    url,
                    params,
                    attempt,
                    max_attempts,
                )
                response: requests.Response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    timeout=self.settings.test_timeout,
                )
                logger.debug(
                    "API response: %s %s → HTTP %d (%d bytes)",
                    method,
                    url,
                    response.status_code,
                    len(response.content),
                )
                response.raise_for_status()
                return response.json()

            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
            ) as exc:
                # Transient network failure — retry if attempts remain.
                last_exception = exc
                if attempt < max_attempts:
                    logger.warning(
                        "Transient error on attempt %d/%d for %s %s: %s. "
                        "Retrying in %.1fs…",
                        attempt,
                        max_attempts,
                        method,
                        url,
                        exc,
                        self.settings.retry_delay,
                    )
                    time.sleep(self.settings.retry_delay)
                else:
                    logger.error(
                        "All %d attempts exhausted for %s %s: %s",
                        max_attempts,
                        method,
                        url,
                        exc,
                    )
                    raise

            except requests.exceptions.HTTPError as exc:
                # 5xx server errors are transient — retry if attempts remain.
                # 4xx client errors are permanent — fail immediately.
                last_exception = exc
                status_code = (
                    exc.response.status_code if exc.response is not None else 0
                )
                if 500 <= status_code < 600 and attempt < max_attempts:
                    logger.warning(
                        "Server error (HTTP %d) on attempt %d/%d for %s %s. "
                        "Retrying in %.1fs…",
                        status_code,
                        attempt,
                        max_attempts,
                        method,
                        url,
                        self.settings.retry_delay,
                    )
                    time.sleep(self.settings.retry_delay)
                else:
                    logger.error(
                        "HTTP error for %s %s: %s",
                        method,
                        url,
                        exc,
                    )
                    raise

        # Unreachable under normal flow, but satisfies type checkers.
        if last_exception is not None:  # pragma: no cover
            raise last_exception
        raise RuntimeError(  # pragma: no cover
            f"Unexpected state: all {max_attempts} attempts completed "
            f"without returning or raising for {method} {url}"
        )
