"""Send individual remote control keys and key sequences."""

from collections.abc import Iterable

from homeassistant.components.remote import ATTR_DELAY_SECS
from homeassistant.components.remote import ATTR_HOLD_SECS
from homeassistant.components.remote import ATTR_NUM_REPEATS
from homeassistant.components.remote import DEFAULT_DELAY_SECS
from homeassistant.components.remote import RemoteEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import KEYS
from .coordinator import BoxConfigEntry
from .entity import BoxEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(hass: HomeAssistant, entry: BoxConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Add the decoder's remote entity."""
    async_add_entities([BoxRemote(entry)])


class BoxRemote(BoxEntity, RemoteEntity):
    """Expose the STB8 remote keys and decoder power."""

    def __init__(self, entry: BoxConfigEntry) -> None:
        """Associate the remote with the decoder."""
        super().__init__(entry, "remote")

    @property
    def is_on(self) -> bool:
        """Return whether the decoder is on."""
        return self.coordinator.data.power

    async def async_send_command(self, command: Iterable[str], **kwargs) -> None:
        """Validate and send a sequence of remote keys."""
        if kwargs.get(ATTR_HOLD_SECS):
            raise ServiceValidationError("Le décodeur accepte uniquement des appuis brefs")
        keys = []
        for item in command:
            key = item.strip().upper()
            if len(key) == 1 and key in "0123456789":
                key = f"NUM_{key}"
            if key not in KEYS:
                raise ServiceValidationError(f"Touche STB8 inconnue : {item}")
            keys.append(key)
        if not keys:
            raise ServiceValidationError("Indiquez au moins une touche")
        repeats = kwargs.get(ATTR_NUM_REPEATS, 1)
        await self.coordinator.async_send_keys(keys * repeats, kwargs.get(ATTR_DELAY_SECS, DEFAULT_DELAY_SECS))
