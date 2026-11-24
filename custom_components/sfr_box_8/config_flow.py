"""Configure one SFR Box 8 TV per address and port."""

import ipaddress
import re

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.const import CONF_NAME
from homeassistant.const import CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import TextSelector
from homeassistant.helpers.selector import TextSelectorConfig

from .channels import channels_from_text
from .client import BoxClient
from .client import BoxError
from .const import CONF_CHANNELS
from .const import CONF_UPNP_URL
from .const import DEFAULT_CHANNELS
from .const import DEFAULT_NAME
from .const import DEFAULT_PORT
from .const import DOMAIN
from .live_channel import validate_control_url

_HOST_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")


def normalize_host(host: str) -> str:
    """Normalize an IP address or DNS name without accepting a URL."""
    host = host.strip().lower().removesuffix(".")
    try:
        return str(ipaddress.ip_address(host))
    except ValueError:
        if len(host) > 253 or not all(_HOST_LABEL.fullmatch(label) for label in host.split(".")):
            raise ValueError("Invalid host") from None
        return host


class SFRBoxConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Set up the integration from the Home Assistant UI."""

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Return the options flow for a decoder."""
        return SFRBoxOptionsFlow()

    async def async_step_user(self, user_input=None):
        """Validate a new decoder and create its entry."""
        errors = {}
        if user_input is not None:
            try:
                host = normalize_host(user_input[CONF_HOST])
            except ValueError:
                errors[CONF_HOST] = "invalid_host"
            else:
                name = user_input[CONF_NAME].strip()
                port = user_input[CONF_PORT]
                if not name:
                    errors[CONF_NAME] = "invalid_name"
                else:
                    await self.async_set_unique_id(f"[{host}]:{port}")
                    self._abort_if_unique_id_configured()
                    client = BoxClient(async_get_clientsession(self.hass), host, port)
                    try:
                        await client.status()
                    except BoxError:
                        errors["base"] = "cannot_connect"
                    else:
                        return self.async_create_entry(
                            title=name,
                            data={CONF_HOST: host, CONF_PORT: port},
                        )

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(schema, user_input),
            errors=errors,
        )


class SFRBoxOptionsFlow(config_entries.OptionsFlowWithReload):
    """Configure the list of favorites shown by the media player."""

    async def async_step_init(self, user_input=None):
        """Validate favorites and the optional UPnP endpoint."""
        errors = {}
        if user_input is not None:
            try:
                channels_from_text(user_input[CONF_CHANNELS])
            except ValueError:
                errors[CONF_CHANNELS] = "invalid_channels"
            upnp_url = user_input.get(CONF_UPNP_URL, "").strip()
            if upnp_url:
                try:
                    validate_control_url(upnp_url, self.config_entry.data[CONF_HOST])
                except ValueError:
                    errors[CONF_UPNP_URL] = "invalid_upnp_url"
            if not errors:
                return self.async_create_entry(title="", data={**user_input, CONF_UPNP_URL: upnp_url})

        defaults = {
            CONF_CHANNELS: self.config_entry.options.get(CONF_CHANNELS, DEFAULT_CHANNELS),
            CONF_UPNP_URL: self.config_entry.options.get(CONF_UPNP_URL, ""),
        }
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Required(CONF_CHANNELS, default=""): TextSelector(TextSelectorConfig(multiline=True)),
                        vol.Optional(CONF_UPNP_URL): str,
                    }
                ),
                user_input if user_input is not None else defaults,
            ),
            errors=errors,
        )
