"""Read-only Home Assistant REST API client (Python standard library only)."""

from __future__ import annotations

import json
import os
import ssl
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener, HTTPSHandler


class HAError(RuntimeError):
    """A safe user-facing Home Assistant connection error."""


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward bearer tokens to a redirected destination.
        return None


class HAClient:
    def __init__(self, url: str | None = None, token: str | None = None, timeout: int = 15) -> None:
        url = (url if url is not None else os.environ.get("HA_URL", "")).strip().rstrip("/")
        token = token if token is not None else os.environ.get("HA_TOKEN", "")
        parts = urlsplit(url)
        if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password or parts.path not in {"", "/"} or parts.query or parts.fragment:
            raise HAError("Set HA_URL to your Home Assistant base URL, e.g. http://homeassistant.local:8123")
        if not token:
            raise HAError("Missing HA_TOKEN. Use a Home Assistant long-lived access token in an environment variable.")
        if timeout < 1:
            raise HAError("Timeout must be >= 1 second")
        self.url = url
        self._token = token
        self._timeout = timeout
        self._opener = build_opener(NoRedirects(), HTTPSHandler(context=ssl.create_default_context()))

    def get_json(self, path: str):
        req = Request(
            self.url + path,
            headers={"Authorization": "Bearer " + self._token, "Accept": "application/json", "User-Agent": "ha-upgrade-guard/0.1"},
            method="GET",
        )
        try:
            with self._opener.open(req, timeout=self._timeout) as response:
                return json.load(response)
        except HTTPError as error:
            if error.code == 401:
                raise HAError("Authentication failed (HTTP 401). Check HA_TOKEN.") from None
            if error.code in (301, 302, 303, 307, 308):
                raise HAError("Home Assistant redirected the request. Use its final local HTTPS or HTTP base URL directly.") from None
            raise HAError(f"Home Assistant returned HTTP {error.code} for {path}") from None
        except (URLError, TimeoutError, ConnectionError, OSError) as error:
            raise HAError(f"Could not connect to Home Assistant ({type(error).__name__}). Check HA_URL, network and SSL.") from None
        except (ValueError, UnicodeError):
            raise HAError(f"Home Assistant returned invalid JSON for {path}") from None

    def snapshot_data(self):
        states = self.get_json("/api/states")
        if not isinstance(states, list):
            raise HAError("/api/states returned unexpected data")
        config = self.get_json("/api/config")
        if not isinstance(config, dict):
            raise HAError("/api/config returned unexpected data")
        return states, config.get("version", "unknown")
