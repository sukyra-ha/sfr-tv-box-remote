"""Poll the decoder and serialize power transitions and key sequences."""

import asyncio
import logging
from dataclasses import dataclass
from datetime import timedelta
from itertools import groupby

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.update_coordinator import UpdateFailed

from .client import BoxClient
from .client import BoxError
from .client import CommandRejectedError
from .const import KEYS
from .live_channel import LiveChannelClient

_LOGGER = logging.getLogger(__name__)
_POWER_TIMEOUT = 12
_POWER_INTERVAL = 0.6
_CHANNEL_INTERVAL = 0.22

type BoxConfigEntry = ConfigEntry[BoxCoordinator]


@dataclass(frozen=True)
class BoxState:
    """Observed decoder state."""

    power: bool
    channel: str | None = None


class BoxCoordinator(DataUpdateCoordinator[BoxState]):
    """Share one authoritative power state and command queue per decoder."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: BoxConfigEntry,
        client: BoxClient,
        live: LiveChannelClient,
    ):
        """Schedule refreshes and initialize the decoder command lock."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=entry.title,
            update_interval=timedelta(seconds=20),
            always_update=False,
        )
        self.client = client
        self._live = live
        self._lock = asyncio.Lock()
        self._pending_power: tuple[bool, float] | None = None

    async def _async_update_data(self) -> BoxState:
        async with self._lock:
            try:
                power = await self._read_power()
            except BoxError as err:
                raise UpdateFailed(str(err)) from err
            channel = None
            if power:
                try:
                    channel = await self._live.read()
                except BoxError as err:
                    _LOGGER.debug("Chaîne indisponible pour %s : %s", self.name, err)
            return BoxState(power, channel)

    def _publish_power(self, power: bool) -> None:
        # Power commands do not query UPnP. Preserve the last observed channel while on.
        channel = self.data.channel if power and self.data else None
        self.async_set_updated_data(BoxState(power, channel))

    async def _read_power(self) -> bool:
        state = await self.client.status()
        if self._pending_power and state == self._pending_power[0]:
            self._pending_power = None
        return state

    async def _wait_for_pending_power(self) -> bool:
        target, deadline = self._pending_power
        try:
            async with asyncio.timeout_at(deadline):
                while True:
                    try:
                        state = await self._read_power()
                    except BoxError:
                        _LOGGER.debug("État temporairement indisponible après POWER")
                    else:
                        self._publish_power(state)
                        if state == target:
                            return state
                    await asyncio.sleep(_POWER_INTERVAL)
        except TimeoutError as err:
            self._pending_power = None
            raise BoxError("Le décodeur n’a pas confirmé le nouvel état d’alimentation") from err

    async def _set_power(self, target: bool | None) -> None:
        # Resolve any earlier cancelled transition before deciding to toggle again.
        if self._pending_power:
            await self._wait_for_pending_power()

        async with self.client.connection() as socket:
            state = await self.client.status(socket)
            self._publish_power(state)
            target = not state if target is None else target
            if state == target:
                return

            deadline = asyncio.get_running_loop().time() + _POWER_TIMEOUT
            self._pending_power = (target, deadline)
            try:
                await self.client.send_key(socket, KEYS["POWER"])
            except CommandRejectedError:
                self._pending_power = None
                raise
            except BoxError:
                # The key might already have reached the box. Only retry status reads.
                _LOGGER.debug("Accusé de réception POWER manquant, vérification de l’état")
        await self._wait_for_pending_power()

    async def async_set_power(self, target: bool | None) -> None:
        """Set a desired power state, or intentionally toggle a raw POWER key."""
        async with self._lock:
            try:
                await self._set_power(target)
            except BoxError as err:
                raise HomeAssistantError(str(err)) from err

    async def _send_keys(self, keys: list[str], delay: float) -> None:
        async with self.client.connection() as socket:
            for index, key in enumerate(keys):
                if index:
                    await asyncio.sleep(delay)
                await self.client.send_key(socket, KEYS[key])

    async def async_send_keys(self, keys: list[str], delay: float) -> None:
        """Send validated remote keys, including intentional POWER toggles."""
        async with self._lock:
            try:
                for index, (is_power, group) in enumerate(groupby(keys, key=lambda key: key == "POWER")):
                    if index:
                        await asyncio.sleep(delay)
                    if not is_power:
                        await self._send_keys(list(group), delay)
                        continue
                    for press, _ in enumerate(group):
                        if press:
                            await asyncio.sleep(delay)
                        await self._set_power(None)
            except BoxError as err:
                raise HomeAssistantError(str(err)) from err

    async def async_select_channel(self, number: str) -> None:
        """Wake the decoder if needed, then enter the digits together."""
        async with self._lock:
            try:
                await self._set_power(True)
                await self._send_keys([f"NUM_{digit}" for digit in number], _CHANNEL_INTERVAL)
            except BoxError as err:
                raise HomeAssistantError(str(err)) from err
