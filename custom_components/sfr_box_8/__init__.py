"""Home Assistant integration for SFR Box 8 TV."""

from homeassistant.const import CONF_HOST
from homeassistant.const import CONF_PORT
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import BoxClient
from .const import CONF_UPNP_URL
from .coordinator import BoxConfigEntry
from .coordinator import BoxCoordinator
from .live_channel import LiveChannelClient
from .live_channel import validate_control_url

PLATFORMS = (Platform.MEDIA_PLAYER, Platform.REMOTE)


async def async_setup_entry(hass: HomeAssistant, entry: BoxConfigEntry) -> bool:
    """Set up one decoder and both entity platforms."""
    session = async_get_clientsession(hass)
    host = entry.data[CONF_HOST]
    client = BoxClient(session, host, entry.data[CONF_PORT])
    upnp_url = entry.options.get(CONF_UPNP_URL)
    live = LiveChannelClient(session, validate_control_url(upnp_url, host)) if upnp_url else None
    coordinator = BoxCoordinator(hass, entry, client, live)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: BoxConfigEntry) -> bool:
    """Unload both entity platforms for the decoder."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
