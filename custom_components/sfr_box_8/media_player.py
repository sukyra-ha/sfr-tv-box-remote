"""Power and channel selection for an SFR Box 8 TV."""

from homeassistant.components.media_player import MediaPlayerDeviceClass
from homeassistant.components.media_player import MediaPlayerEntity
from homeassistant.components.media_player import MediaPlayerEntityFeature
from homeassistant.components.media_player import MediaPlayerState
from homeassistant.components.media_player import MediaType
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .channels import channel_number
from .channels import channels_from_text
from .const import CONF_CHANNELS
from .const import DEFAULT_CHANNELS
from .coordinator import BoxConfigEntry
from .entity import BoxEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(hass: HomeAssistant, entry: BoxConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Add the decoder's media player."""
    async_add_entities([BoxMediaPlayer(entry)])


class BoxMediaPlayer(BoxEntity, MediaPlayerEntity):
    """Expose actual decoder power and selectable channel presets."""

    _attr_device_class = MediaPlayerDeviceClass.TV
    _attr_supported_features = (
        MediaPlayerEntityFeature.TURN_ON
        | MediaPlayerEntityFeature.TURN_OFF
        | MediaPlayerEntityFeature.SELECT_SOURCE
        | MediaPlayerEntityFeature.PLAY_MEDIA
    )

    def __init__(self, entry: BoxConfigEntry) -> None:
        """Prepare the configured favorites."""
        super().__init__(entry, "media_player")
        self._channels = channels_from_text(entry.options.get(CONF_CHANNELS, DEFAULT_CHANNELS))
        self._attr_source_list = list(self._channels)

    @property
    def state(self) -> MediaPlayerState:
        """Return the observed decoder power state."""
        return MediaPlayerState.ON if self.coordinator.data.power else MediaPlayerState.OFF

    @property
    def media_title(self) -> str | None:
        """Return the reported live channel name."""
        return self.coordinator.data.channel

    @property
    def media_content_type(self) -> MediaType | None:
        """Identify the reported title as a live channel."""
        return MediaType.CHANNEL if self.media_title else None

    async def async_select_source(self, source: str) -> None:
        """Tune to a configured favorite."""
        try:
            number = self._channels[source]
        except KeyError as err:
            raise ServiceValidationError(f"Chaîne absente des favoris : {source}") from err
        await self.coordinator.async_select_channel(number)

    async def async_play_media(self, media_type: str, media_id: str, **kwargs) -> None:
        """Tune to the requested channel number."""
        if media_type != MediaType.CHANNEL:
            raise ServiceValidationError("Sélectionnez le type de média channel")
        try:
            number = channel_number(media_id)
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err
        await self.coordinator.async_select_channel(number)
