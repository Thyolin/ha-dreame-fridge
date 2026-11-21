"""Push updates from the Dreamehome MQTT broker."""

from __future__ import annotations

import json
import logging
import secrets
import ssl
from collections.abc import Callable
from pathlib import Path
from typing import Any

import paho.mqtt.client as mqtt

from .api import DreameCloud, DreameDevice, _md5

_LOGGER = logging.getLogger(__name__)

CA_FILE = Path(__file__).with_name("dreame_iot_ca.pem")


def build_tls_context() -> ssl.SSLContext:
    """TLS context trusting only Dreame's private IoT root (blocking, run in executor).

    The broker uses a private CA whose root lacks some extensions that newer
    Python versions require in strict mode, so only that flag is relaxed. The
    chain and host name are still verified.
    """
    ctx = ssl.create_default_context(cafile=str(CA_FILE))
    ctx.verify_flags &= ~getattr(ssl, "VERIFY_X509_STRICT", 0)
    return ctx


class DreamePush:
    """Subscribes to the device status topic. Callbacks run in paho's thread."""

    def __init__(
        self,
        cloud: DreameCloud,
        device: DreameDevice,
        tls: ssl.SSLContext,
        on_properties: Callable[[list[dict[str, Any]]], None],
        on_state: Callable[[bool], None],
    ) -> None:
        self._cloud = cloud
        self._device = device
        self._on_properties = on_properties
        self._on_state = on_state
        self.connected = False
        host, _, port = device.mqtt_host.partition(":")
        self._host = host
        self._port = int(port or 8883)
        self._topic = f"/status/{device.did}/{device.owner_uid}/{device.model}/{cloud.country}/"
        client_id = "p_" + _md5(device.did + "mqtt" + secrets.token_hex(16))
        try:
            self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id, clean_session=True)
        except AttributeError:  # paho-mqtt < 2
            self._client = mqtt.Client(client_id, clean_session=True)
        self._client.tls_set_context(tls)
        self._client.reconnect_delay_set(2, 60)
        self._client.on_connect = self._handle_connect
        self._client.on_disconnect = self._handle_disconnect
        self._client.on_message = self._handle_message
        self.update_credentials()

    def update_credentials(self) -> None:
        """Use the current access token for the next (re)connect."""
        self._client.username_pw_set(self._cloud.user_id, self._cloud.access_token)

    def start(self) -> None:
        """Connect in the background (non-blocking apart from DNS)."""
        self._client.connect_async(self._host, self._port, keepalive=60)
        self._client.loop_start()

    def stop(self) -> None:
        self._client.disconnect()
        self._client.loop_stop()

    def _handle_connect(self, client, _userdata, _flags, reason_code, _props=None) -> None:
        if getattr(reason_code, "is_failure", reason_code != 0):
            _LOGGER.debug("MQTT connect refused: %s", reason_code)
            return
        _LOGGER.debug("MQTT connected, subscribing %s", self._topic)
        client.subscribe(self._topic)
        self.connected = True
        self._on_state(True)

    def _handle_disconnect(self, _client, _userdata, *args) -> None:
        self.connected = False
        _LOGGER.debug("MQTT disconnected: %s", args)
        self._on_state(False)

    def _handle_message(self, _client, _userdata, message) -> None:
        try:
            payload = json.loads(message.payload)
        except ValueError:
            return
        data = payload.get("data") if isinstance(payload, dict) else None
        if isinstance(data, dict) and data.get("method") == "properties_changed":
            params = [p for p in data.get("params") or [] if "siid" in p and "piid" in p]
            if params:
                self._on_properties(params)
