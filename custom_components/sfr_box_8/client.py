"""Bounded WebSocket exchanges for the SFR STB8 protocol."""

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from aiohttp import ClientError
from aiohttp import ClientSession
from aiohttp import ClientWebSocketResponse
from yarl import URL

_LOGGER = logging.getLogger(__name__)
_RESPONSE_TIMEOUT = 3
_POWER_STATES = {"powerOn": True, "powerOff": False}


class BoxError(Exception):
    """The decoder failed to return a usable response."""


class CommandRejectedError(BoxError):
    """The decoder explicitly rejected the command."""


class BoxClient:
    """Open a WebSocket for a status request or an entire key sequence."""

    def __init__(self, session: ClientSession, host: str, port: int) -> None:
        """Set the decoder endpoint and shared HTTP session."""
        self._session = session
        self._url = URL.build(scheme="ws", host=host, port=port, path="/ws")
        self._last_request_id = 0

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[ClientWebSocketResponse]:
        """Bound the handshake and close the socket even after cancellation."""
        try:
            async with asyncio.timeout(_RESPONSE_TIMEOUT):
                socket = await self._session.ws_connect(self._url, max_msg_size=65536)
        except (ClientError, OSError, TimeoutError) as err:
            raise BoxError(f"Connexion au décodeur impossible ({self._url.host})") from err

        try:
            yield socket
        finally:
            try:
                async with asyncio.timeout(0.5):
                    await socket.close()
            except (ClientError, OSError, TimeoutError):
                _LOGGER.debug("Fermeture WebSocket interrompue pour %s", self._url.host)

    async def _exchange(self, socket: ClientWebSocketResponse, action: str, **fields: object) -> dict:
        self._last_request_id = max(self._last_request_id + 1, time.time_ns() // 1_000_000)
        request_id = self._last_request_id
        payload = {
            "action": action,
            "deviceId": "default-stb8",
            "requestId": request_id,
            **fields,
        }
        _LOGGER.debug("Envoi de %s à %s (requête %s)", action, self._url.host, request_id)
        try:
            async with asyncio.timeout(_RESPONSE_TIMEOUT):
                await socket.send_json(payload)
                while True:
                    response = json.loads(await socket.receive_str())
                    if not isinstance(response, dict):
                        continue
                    if response.get("requestId") != request_id:
                        continue  # A notification or a response to a different request.
                    if response.get("action") != action:
                        raise BoxError(f"Réponse incohérente pour {action}")
                    code = response.get("remoteResponseCode")
                    _LOGGER.debug("Réponse %s pour %s (requête %s)", code, action, request_id)
                    if code == "KO":
                        raise CommandRejectedError(f"Le décodeur a refusé {action}")
                    if code != "OK":
                        raise BoxError(f"Code de réponse inconnu pour {action}")
                    return response
        except (ClientError, OSError, TimeoutError, ValueError, TypeError) as err:
            raise BoxError(f"Aucune réponse exploitable du décodeur pour {action}") from err

    async def status(self, socket: ClientWebSocketResponse | None = None) -> bool:
        """Read the current power state from a correlated getStatus reply."""
        if socket is None:
            async with self.connection() as connection:
                return await self.status(connection)

        reply = await self._exchange(socket, "getStatus")
        try:
            return _POWER_STATES[reply["data"]["power"]]
        except (KeyError, TypeError) as err:
            raise BoxError("État d’alimentation du décodeur inconnu") from err

    async def send_key(self, socket: ClientWebSocketResponse, key: str) -> None:
        """Wait for the acknowledgement of a single key press."""
        await self._exchange(socket, "buttonEvent", params={"key": key})
