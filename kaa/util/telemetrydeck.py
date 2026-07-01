"""TelemetryDeck v2 ingest API client (single-file, generic)."""

from __future__ import annotations

import hashlib
import locale
import logging
import platform
import queue
import sys
import threading
import time
import uuid
from typing import Any

import requests

logger = logging.getLogger(__name__)

_ENDPOINT = "https://nom.telemetrydeck.com/v2/namespace/{namespace}/"

# ISO 639-1 codes whose scripts run right-to-left
_RTL_LANGS = frozenset({"ar", "he", "fa", "ur", "yi", "ps", "ug"})


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _collect_system_defaults() -> dict[str, str]:
    """Collect system-level default payload fields that require no app context."""
    result: dict[str, str] = {}

    result["TelemetryDeck.Device.operatingSystem"] = platform.system()
    result["TelemetryDeck.Device.systemVersion"] = platform.version()
    result["TelemetryDeck.Device.architecture"] = platform.machine()

    try:
        loc = locale.getlocale()[0]  # e.g. "zh_CN", "en_US"
        if loc:
            result["TelemetryDeck.RunContext.locale"] = loc
            lang, _, region = loc.partition("_")
            result["TelemetryDeck.UserPreference.language"] = lang
            if region:
                result["TelemetryDeck.UserPreference.region"] = region
            result["TelemetryDeck.UserPreference.layoutDirection"] = (
                "rightToLeft" if lang in _RTL_LANGS else "leftToRight"
            )
    except Exception:
        pass

    if sys.platform == "win32":
        try:
            import winreg  # type: ignore[import]
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            )
            light, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            result["TelemetryDeck.UserPreference.colorScheme"] = (
                "Light" if light else "Dark"
            )
        except Exception:
            pass

    return result


class TelemetryDeckClient:
    """Fire-and-forget TelemetryDeck v2 client.

    Signals are batched and delivered by a background daemon thread,
    so ``signal()`` never blocks the caller.

    Args:
        app_id:         TelemetryDeck app identifier.
        namespace:      TelemetryDeck organisation namespace (used in the URL).
        client_user:    Stable user/device identifier; SHA-256 hashed before sending.
        app_version:    App version string → ``TelemetryDeck.AppInfo.version``.
        sdk_name:       SDK name → ``TelemetryDeck.SDK.name``.
        sdk_version:    SDK version → ``TelemetryDeck.SDK.version`` /
                        ``TelemetryDeck.SDK.nameAndVersion``.
        build_type:     Build type string (e.g. ``"debug"``, ``"release"``) →
                        ``TelemetryDeck.SDK.buildType``.
        extra_defaults: Extra key-value pairs merged into every signal's payload.
        test_mode:      When ``True``, signals are excluded from production queries.
        session_id:     Session identifier; a random UUID is generated if omitted.
        batch_size:     Maximum signals per HTTP request.
        flush_interval: Seconds between automatic flushes even if batch is not full.
        request_timeout: HTTP request timeout in seconds.

    Usage::

        client = TelemetryDeckClient(
            app_id="AAAA-BBBB-CCCC-DDDD",
            namespace="my-org",
            client_user=device_id,
            app_version="2026.6",
            sdk_name="MyApp-Python",
            sdk_version="1.0",
            build_type="release",
        )
        client.signal("App.launch")
        client.signal("Feature.used", payload={"Feature.name": "autoplay"})
        client.shutdown()
    """

    def __init__(
        self,
        *,
        app_id: str,
        namespace: str,
        client_user: str,
        app_version: str | None = None,
        sdk_name: str = "TelemetryDeckPython",
        sdk_version: str | None = None,
        build_type: str | None = None,
        extra_defaults: dict[str, Any] | None = None,
        test_mode: bool = False,
        session_id: str | None = None,
        batch_size: int = 10,
        flush_interval: float = 5.0,
        request_timeout: float = 10.0,
    ) -> None:
        self._app_id = app_id
        self._url = _ENDPOINT.format(namespace=namespace)
        self._client_user = _sha256(client_user)
        self._test_mode = test_mode
        self._session_id = session_id or str(uuid.uuid4())
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._request_timeout = request_timeout

        base = _collect_system_defaults()

        if app_version is not None:
            base["TelemetryDeck.AppInfo.version"] = app_version

        base["TelemetryDeck.SDK.name"] = sdk_name
        if sdk_version is not None:
            base["TelemetryDeck.SDK.version"] = sdk_version
            base["TelemetryDeck.SDK.nameAndVersion"] = f"{sdk_name} {sdk_version}"
        if build_type is not None:
            base["TelemetryDeck.SDK.buildType"] = build_type

        if extra_defaults:
            base.update({k: str(v) for k, v in extra_defaults.items()})

        self._base_payload: dict[str, str] = {k: str(v) for k, v in base.items()}

        self._queue: queue.Queue[dict[str, Any]] = queue.Queue()
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=self._worker, daemon=True, name="telemetrydeck"
        )
        self._thread.start()

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def signal(
        self,
        signal_type: str,
        *,
        payload: dict[str, Any] | None = None,
        float_value: float | None = None,
    ) -> None:
        """Queue a signal for asynchronous delivery. Never blocks."""
        merged = dict(self._base_payload)
        if payload:
            merged.update({k: str(v) for k, v in payload.items()})

        event: dict[str, Any] = {
            "appID": self._app_id,
            "clientUser": self._client_user,
            "sessionID": self._session_id,
            "type": signal_type,
            "isTestMode": self._test_mode,
            "payload": merged,
        }
        if float_value is not None:
            event["floatValue"] = float_value

        self._queue.put_nowait(event)

    def flush(self) -> None:
        """Block until all queued signals have been dequeued for sending."""
        self._queue.join()

    def shutdown(self, timeout: float = 10.0) -> None:
        """Drain remaining signals and stop the background worker thread."""
        self._stop.set()
        self._thread.join(timeout=timeout)

    # ------------------------------------------------------------------ #
    # Background worker                                                    #
    # ------------------------------------------------------------------ #

    def _worker(self) -> None:
        batch: list[dict[str, Any]] = []
        last_send = time.monotonic()

        while True:
            try:
                event = self._queue.get(timeout=0.25)
                batch.append(event)
                self._queue.task_done()
            except queue.Empty:
                pass

            while len(batch) < self._batch_size:
                try:
                    event = self._queue.get_nowait()
                    batch.append(event)
                    self._queue.task_done()
                except queue.Empty:
                    break

            now = time.monotonic()
            if batch and (
                len(batch) >= self._batch_size
                or now - last_send >= self._flush_interval
            ):
                self._post(batch)
                batch = []
                last_send = now

            if self._stop.is_set():
                while True:
                    try:
                        event = self._queue.get_nowait()
                        batch.append(event)
                        self._queue.task_done()
                    except queue.Empty:
                        break
                if batch:
                    self._post(batch)
                break

    def _post(self, events: list[dict[str, Any]]) -> None:
        try:
            resp = requests.post(
                self._url,
                json=events,
                headers={"Content-Type": "application/json; charset=utf-8"},
                timeout=self._request_timeout,
            )
            if resp.ok:
                logger.debug("TelemetryDeck: sent %d signal(s)", len(events))
            else:
                logger.warning(
                    "TelemetryDeck HTTP %s: %s", resp.status_code, resp.text[:200]
                )
        except Exception as exc:
            logger.debug("TelemetryDeck: send failed: %s", exc)
