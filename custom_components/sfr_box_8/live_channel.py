"""Read live channel information from the decoder's UPnP Resources service."""

import asyncio
from xml.etree.ElementTree import ParseError

from aiohttp import ClientError
from aiohttp import ClientSession
from defusedxml.common import DefusedXmlException
from defusedxml.ElementTree import fromstring
from homeassistant.core import HomeAssistant
from yarl import URL

from .client import BoxError
from .const import UPNP_SERVICE
from .upnp import async_find_control_url

_DISCOVERY_RETRY_MIN = 20
_DISCOVERY_RETRY_MAX = 300
_QUERY = f"""<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
<s:Body><u:getUsage xmlns:u="{UPNP_SERVICE}"><from>0</from><duration>30</duration></u:getUsage></s:Body>
</s:Envelope>"""
_HEADERS = {"Content-Type": "text/xml; charset=utf-8", "SOAPAction": f'"{UPNP_SERVICE}#getUsage"'}
_MAX_RESPONSE = 64 * 1024


class LiveChannelClient:
    """Read the single named live channel reported by the decoder."""

    def __init__(self, hass: HomeAssistant, session: ClientSession, host: str, url: URL | None) -> None:
        """Use a manual endpoint or discover one when the decoder is on."""
        self._hass = hass
        self._session = session
        self._host = host
        self._url = url
        self._manual = url is not None
        self._retry_at = 0.0
        self._retry_delay = _DISCOVERY_RETRY_MIN

    async def read(self) -> str | None:
        """Return a channel name when the current usage identifies one."""
        if self._url is None:
            now = asyncio.get_running_loop().time()
            if now < self._retry_at:
                return None
            self._retry_at = now + self._retry_delay
            self._url = await async_find_control_url(self._hass, self._session, self._host)
            if self._url is None:
                self._retry_delay = min(self._retry_delay * 2, _DISCOVERY_RETRY_MAX)
                return None
            self._retry_delay = _DISCOVERY_RETRY_MIN
        try:
            return await self._read_usage(self._url)
        except BoxError:
            if not self._manual:
                self._url = None
                self._retry_at = asyncio.get_running_loop().time() + _DISCOVERY_RETRY_MIN
            raise

    async def _read_usage(self, url: URL) -> str | None:
        try:
            async with asyncio.timeout(3):
                async with self._session.post(url, data=_QUERY, headers=_HEADERS, allow_redirects=False) as response:
                    if response.status != 200:
                        raise BoxError(f"UPnP getUsage a répondu HTTP {response.status}")
                    try:
                        await response.content.readexactly(_MAX_RESPONSE + 1)
                    except asyncio.IncompleteReadError as err:
                        body = err.partial
                    else:
                        raise BoxError("Réponse UPnP trop volumineuse")
            usage = fromstring(body).findtext(".//{*}usage_list")
            if not usage or not usage.strip():
                return None
            channels = {
                item.findtext("{*}description", "").strip()
                for item in fromstring(usage).findall("{*}item")
                if item.findtext("{*}type") == "LIVE"
            }
            if len(channels) == 1:
                return channels.pop() or None
        except (ClientError, OSError, TimeoutError, ParseError, DefusedXmlException) as err:
            raise BoxError("Impossible de lire la chaîne via UPnP") from err
        return None
