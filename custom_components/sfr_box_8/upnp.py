"""Find the UPnP Resources endpoint advertised by one configured decoder."""

import asyncio
import socket
from contextlib import aclosing
from ipaddress import IPv4Address
from xml.etree.ElementTree import ParseError

from aiohttp import ClientError
from aiohttp import ClientSession
from defusedxml.common import DefusedXmlException
from defusedxml.ElementTree import fromstring
from homeassistant.core import HomeAssistant
from yarl import URL

from .const import UPNP_SERVICE

_MULTICAST = "239.255.255.250"
_SSDP_PORT = 1900
_SSDP_TIMEOUT = 2
_ROOT_DEVICE = "upnp:rootdevice"
_MAX_DESCRIPTION = 64 * 1024


def validate_control_url(value: str, host: str) -> URL:
    """Accept a Resources control endpoint on the configured decoder."""
    url = URL(value)
    if (
        not _local_url(url, host)
        or url.query_string
        or url.fragment
        or not url.path.endswith("/Resources/control")
        or url.port is None
        or not 1 <= url.port <= 65535
    ):
        raise ValueError("Invalid UPnP control URL")
    return url


def _local_url(url: URL, host: str) -> bool:
    return url.scheme == "http" and url.host == host and url.user is None


async def _resolve_ipv4(host: str) -> str:
    try:
        return str(IPv4Address(host))
    except ValueError:
        pass
    addresses = await asyncio.get_running_loop().getaddrinfo(host, None, family=socket.AF_INET, type=socket.SOCK_DGRAM)
    return addresses[0][4][0]


async def _search_locations(ip: str):
    """Yield SSDP locations from the decoder during a bounded broadcast."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + _SSDP_TIMEOUT
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
        client.setblocking(False)
        for address in (ip, _MULTICAST):
            query = (
                f'M-SEARCH * HTTP/1.1\r\nHOST: {address}:{_SSDP_PORT}\r\nMAN: "ssdp:discover"\r\nMX: 1\r\nST: ssdp:all\r\n\r\n'
            )
            try:
                await loop.sock_sendto(client, query.encode("ascii"), (address, _SSDP_PORT))
            except OSError:
                continue
        while loop.time() < deadline:
            try:
                async with asyncio.timeout_at(deadline):
                    packet, peer = await loop.sock_recvfrom(client, 8192)
            except (OSError, TimeoutError):
                return
            if peer[0] != ip:
                continue
            for line in packet.decode("latin-1").splitlines():
                name, _, value = line.partition(":")
                if name.casefold() == "location":
                    yield value.strip()


async def _description_control(session: ClientSession, location: str, ip: str, host: str) -> URL | None:
    try:
        description = URL(location)
        if not _local_url(description, ip):
            return None
        async with asyncio.timeout(1):
            async with session.get(description, allow_redirects=False) as response:
                if response.status != 200:
                    return None
                try:
                    await response.content.readexactly(_MAX_DESCRIPTION + 1)
                except asyncio.IncompleteReadError as err:
                    body = err.partial
                else:
                    return None
        for service in fromstring(body).findall(".//{*}service"):
            if service.findtext("{*}serviceType") != UPNP_SERVICE:
                continue
            control = description.join(URL(service.findtext("{*}controlURL") or ""))
            validate_control_url(str(control), ip)
            return validate_control_url(str(control.with_host(host)), host)
    except (ClientError, OSError, TimeoutError, ValueError, ParseError, DefusedXmlException):
        return None
    return None


async def async_find_control_url(hass: HomeAssistant, session: ClientSession, host: str) -> URL | None:
    """Read the decoder's advertised endpoint without changing its state."""
    try:
        async with asyncio.timeout(4):
            ip = await _resolve_ipv4(host)
            seen = set()
            if "ssdp" in hass.config.components:
                from homeassistant.components import ssdp

                for target in (UPNP_SERVICE, _ROOT_DEVICE):
                    for item in await ssdp.async_get_discovery_info_by_st(hass, target):
                        location = item.ssdp_location
                        if not location or location in seen:
                            continue
                        seen.add(location)
                        if endpoint := await _description_control(session, location, ip, host):
                            return endpoint
            # Close the discovery socket promptly when a valid response is found.
            async with aclosing(_search_locations(ip)) as results:
                async for location in results:
                    if location in seen:
                        continue
                    seen.add(location)
                    if endpoint := await _description_control(session, location, ip, host):
                        return endpoint
    except (OSError, TimeoutError):
        return None
    return None
