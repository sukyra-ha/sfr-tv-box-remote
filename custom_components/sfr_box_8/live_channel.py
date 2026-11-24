"""Read live channel information from the decoder's UPnP Resources service."""

import asyncio
from xml.etree.ElementTree import ParseError

from aiohttp import ClientError
from aiohttp import ClientSession
from defusedxml.common import DefusedXmlException
from defusedxml.ElementTree import fromstring
from yarl import URL

from .client import BoxError

_SERVICE = "urn:neufboxtv-org:service:Resources:1"
_QUERY = f"""<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
<s:Body><u:getUsage xmlns:u="{_SERVICE}"><from>0</from><duration>30</duration></u:getUsage></s:Body>
</s:Envelope>"""
_HEADERS = {"Content-Type": "text/xml; charset=utf-8", "SOAPAction": f'"{_SERVICE}#getUsage"'}
_MAX_RESPONSE = 64 * 1024


def validate_control_url(value: str, host: str) -> URL:
    """Accept a Resources control endpoint on the configured decoder."""
    url = URL(value)
    if (
        url.scheme != "http"
        or url.host != host
        or url.user is not None
        or url.query_string
        or url.fragment
        or not url.path.endswith("/Resources/control")
        or url.port is None
        or not 1 <= url.port <= 65535
    ):
        raise ValueError("Invalid UPnP control URL")
    return url


class LiveChannelClient:
    """Read the single named live channel reported by the decoder."""

    def __init__(self, session: ClientSession, url: URL) -> None:
        """Use the supplied UPnP control endpoint."""
        self._session = session
        self._url = url

    async def read(self) -> str | None:
        """Return a channel name when the current usage identifies one."""
        try:
            async with asyncio.timeout(3):
                async with self._session.post(self._url, data=_QUERY, headers=_HEADERS, allow_redirects=False) as response:
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
