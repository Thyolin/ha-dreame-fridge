"""Small async client for the Dreamehome cloud (devices bound to a Dreamehome account)."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import itertools
import json
import logging
import secrets
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import aiohttp
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from .const import (
    API_HOST_SUFFIX,
    API_PORT,
    APP_BASIC_AUTH,
    APP_PASSWORD_SALT,
    APP_SIGN_KEY,
    APP_USER_AGENT,
    APP_VERSION_CODE,
    DEFAULT_TENANT,
)

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=15)
BATCH_SIZE = 8


class DreameError(Exception):
    """Base error."""


class DreameAuthError(DreameError):
    """E-mail/password rejected."""


class DreameConnectionError(DreameError):
    """Cloud not reachable or returned garbage."""


def _md5(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()  # noqa: S324 - protocol requirement


def _canonical(params: dict[str, Any], nested: bool = False) -> str:
    """Build the string the cloud expects for the request signature.

    Keys are sorted. On the top level, scalars are written raw and lists as
    compact JSON. Inside nested objects scalars are JSON encoded and lists are
    left out.
    """
    parts: list[str] = []
    for key in sorted(params):
        value = params[key]
        if isinstance(value, dict):
            inner = _canonical(value, nested=True)
            parts.append(f"{key}=[{inner}]" if inner else f"{key}=]")
        elif isinstance(value, list):
            if not nested:
                parts.append(f"{key}={json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)}")
        elif isinstance(value, bool):
            parts.append(f"{key}={str(value).lower()}")
        elif value is None:
            parts.append(f"{key}=null")
        elif nested:
            parts.append(f"{key}={json.dumps(value, ensure_ascii=False)}")
        else:
            parts.append(f"{key}={value}")
    return "&".join(parts)


def _split_key(key: str) -> tuple[int, int]:
    siid, piid = key.split(".")
    return int(siid), int(piid)


@dataclass
class DreameDevice:
    """A device from the account's device list."""

    did: str
    model: str
    name: str
    mac: str | None
    firmware: str | None
    online: bool
    owner_uid: str
    mqtt_host: str

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> DreameDevice:
        return cls(
            did=str(data["did"]),
            model=data.get("model") or "",
            name=data.get("customName") or data.get("displayName") or "",
            mac=data.get("mac"),
            firmware=data.get("ver"),
            online=bool(data.get("online")),
            owner_uid=str(data.get("masterUid") or ""),
            mqtt_host=data.get("bindDomain") or "",
        )

    @property
    def command_host(self) -> str:
        """First label of the bind domain, used in the command endpoint."""
        return self.mqtt_host.split(".", 1)[0]


class DreameCloud:
    """Login, device list and MIoT property access via the Dreamehome cloud."""

    def __init__(self, session: aiohttp.ClientSession, username: str, password: str, country: str) -> None:
        self._session = session
        self._username = username
        self._password = password
        self.country = country
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._expires_at = 0.0
        self._tenant = DEFAULT_TENANT
        self._locale: tuple[str, str, str] | None = None  # region, lang, country code
        self.user_id: str | None = None
        self._visitor = secrets.token_hex(16)
        self._ids = itertools.count(secrets.randbelow(1000) + 1)
        self._login_lock = asyncio.Lock()
        self.on_token_refresh: list = []

    @property
    def base_url(self) -> str:
        return f"https://{self.country}{API_HOST_SUFFIX}:{API_PORT}"

    @property
    def access_token(self) -> str | None:
        return self._access_token

    # ------------------------------------------------------------------ http
    def _headers(self, content_type: str) -> dict[str, str]:
        user = self._username
        headers = {
            "User-Agent": APP_USER_AGENT,
            "Accept-Encoding": "gzip",
            "Content-Type": content_type,
            "Authorization": f"Basic {APP_BASIC_AUTH}",
            "Tenant-Id": self._tenant,
            "Dreame-Meta": (
                f"cv=a_{APP_VERSION_CODE};canvasHash={_md5(user + 'c')[:8]}"
                f";webglHash={_md5(user + 'w')[:8]};visitorIdHash={self._visitor}"
            ),
        }
        if self._locale:
            padder = padding.PKCS7(128).padder()
            raw = padder.update("|".join(self._locale).encode()) + padder.finalize()
            enc = Cipher(algorithms.AES(APP_SIGN_KEY), modes.ECB()).encryptor()  # noqa: S305 - protocol
            headers["Dreame-Rlc"] = base64.b64encode(enc.update(raw) + enc.finalize()).decode()
        if self._access_token:
            headers["Dreame-Auth"] = self._access_token
        return headers

    async def _post(self, path: str, headers: dict[str, str], body: str | None) -> tuple[int, Any]:
        try:
            async with self._session.post(
                f"{self.base_url}/{path.lstrip('/')}", headers=headers, data=body, timeout=REQUEST_TIMEOUT
            ) as resp:
                text = await resp.text()
                status = resp.status
        except (aiohttp.ClientError, TimeoutError) as err:
            raise DreameConnectionError(f"Request to {path} failed: {err}") from err
        try:
            return status, json.loads(text) if text else {}
        except ValueError as err:
            raise DreameConnectionError(f"Invalid answer from {path} (HTTP {status})") from err

    # ----------------------------------------------------------------- login
    async def login(self) -> None:
        """Log in with the refresh token if possible, else with e-mail/password."""
        async with self._login_lock:
            if self._refresh_token:
                try:
                    await self._token_request(
                        "grant_type=refresh_token&scope=all&platform=ANDROID&type=account"
                        f"&refresh_token={self._refresh_token}"
                    )
                    return
                except DreameAuthError:
                    _LOGGER.debug("Refresh token rejected, logging in with password")
                    self._refresh_token = None
            body = (
                "grant_type=password&scope=all&platform=ANDROID&type=account"
                f"&username={quote(self._username, safe='')}"
                f"&password={_md5(self._password + APP_PASSWORD_SALT)}"
            )
            if self._locale:
                body += f"&country={self._locale[2]}&lang={self._locale[1]}"
            await self._token_request(body)

    async def _token_request(self, body: str) -> None:
        self._access_token = None
        status, data = await self._post(
            "dreame-auth/oauth/token", self._headers("application/x-www-form-urlencoded"), body
        )
        if status in (400, 401, 403):
            raise DreameAuthError(data.get("error_description") or data.get("msg") or f"HTTP {status}")
        if status != 200 or "access_token" not in data:
            raise DreameConnectionError(f"Login failed (HTTP {status})")
        self._access_token = data["access_token"]
        self._refresh_token = data.get("refresh_token")
        self._expires_at = time.time() + int(data.get("expires_in") or 3600)
        self._tenant = data.get("tenant_id") or DEFAULT_TENANT
        self.user_id = str(data.get("uid") or "")
        if data.get("region") and data.get("lang") and data.get("country"):
            self._locale = (data["region"], data["lang"], data["country"])
        for callback in self.on_token_refresh:
            callback()

    async def _ensure_token(self) -> None:
        if not self._access_token or time.time() > self._expires_at - 600:
            await self.login()

    # ------------------------------------------------------------------- api
    async def call(self, path: str, params: dict[str, Any] | None = None, _retry: bool = True) -> Any:
        """Signed JSON call. Returns the ``data`` field of the answer."""
        await self._ensure_token()
        body = None
        if params is not None:
            stamp = int(time.time() * 1000)
            signed = dict(params)
            signed["sign"] = _md5(_canonical(params) + str(stamp) + APP_SIGN_KEY.decode())
            signed["timestamp"] = stamp
            body = json.dumps(signed, separators=(",", ":"))
        status, data = await self._post(path, self._headers("application/json"), body)
        if status == 401 and _retry:
            self._access_token = None
            return await self.call(path, params, _retry=False)
        if status == 401:
            raise DreameAuthError("Session rejected")
        if status != 200 or not isinstance(data, dict) or data.get("code") != 0:
            raise DreameConnectionError(f"{path}: HTTP {status}, {str(data)[:200]}")
        return data.get("data")

    async def devices(self) -> list[DreameDevice]:
        data = await self.call("dreame-user-iot/iotuserbind/device/listV2")
        records = ((data or {}).get("page") or {}).get("records") or []
        return [DreameDevice.from_api(r) for r in records if r.get("did")]

    async def _command(self, device: DreameDevice, method: str, params: list[dict[str, Any]]) -> list[dict]:
        msg_id = next(self._ids)
        data = await self.call(
            f"dreame-iot-com-{device.command_host}/device/sendCommand",
            {
                "did": device.did,
                "id": msg_id,
                "data": {"did": device.did, "id": msg_id, "method": method, "params": params},
            },
        )
        result = (data or {}).get("result")
        if not isinstance(result, list):
            raise DreameConnectionError(f"{method}: no result (device offline?)")
        return result

    async def get_properties(self, device: DreameDevice, keys: list[str]) -> dict[str, Any]:
        """Read properties directly from the device."""
        values: dict[str, Any] = {}
        for start in range(0, len(keys), BATCH_SIZE):
            params = []
            for key in keys[start : start + BATCH_SIZE]:
                siid, piid = _split_key(key)
                params.append({"did": device.did, "siid": siid, "piid": piid})
            for item in await self._command(device, "get_properties", params):
                if item.get("code") == 0 and "value" in item:
                    values[f"{item['siid']}.{item['piid']}"] = item["value"]
        return values

    async def set_property(self, device: DreameDevice, key: str, value: Any) -> None:
        siid, piid = _split_key(key)
        result = await self._command(
            device, "set_properties", [{"did": device.did, "siid": siid, "piid": piid, "value": value}]
        )
        if not result or any(item.get("code") != 0 for item in result):
            raise DreameError(f"Device refused {key}={value}: {result}")

    async def reported_properties(self, device: DreameDevice, keys: list[str]) -> dict[str, tuple[Any, float]]:
        """Last values the device reported to the cloud, with their timestamp (s)."""
        data = await self.call("dreame-user-iot/iotstatus/props", {"did": device.did, "keys": ",".join(keys)})
        out: dict[str, tuple[Any, float]] = {}
        for item in data or []:
            if "value" not in item:
                continue
            value = item["value"]
            try:
                value = int(value)
            except (TypeError, ValueError):
                pass
            out[item["key"]] = (value, (item.get("updateDate") or 0) / 1000)
        return out
