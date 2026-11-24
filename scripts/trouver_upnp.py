"""Afficher l’adresse UPnP d’un décodeur SFR connu sur le réseau local."""

import argparse
import socket
import time
from urllib.parse import urljoin
from urllib.parse import urlsplit
from urllib.parse import urlunsplit
from urllib.request import HTTPRedirectHandler
from urllib.request import ProxyHandler
from urllib.request import build_opener
from xml.etree import ElementTree as ET

SERVICE = "urn:neufboxtv-org:service:Resources:1"
MULTICAST = "239.255.255.250"
MAX_DESCRIPTION = 65536


class NoRedirects(HTTPRedirectHandler):
    """Keep discovery requests on the advertised decoder."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        """Decline HTTP redirects."""
        return None


def locations(ip):
    """Collecter uniquement les annonces du décodeur demandé."""
    found = set()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(0.4)
        for dest in (ip, MULTICAST):
            query = f'M-SEARCH * HTTP/1.1\r\nHOST: {dest}:1900\r\nMAN: "ssdp:discover"\r\nMX: 1\r\nST: ssdp:all\r\n\r\n'
            try:
                sock.sendto(query.encode("ascii"), (dest, 1900))
            except OSError:
                continue

        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            try:
                packet, peer = sock.recvfrom(8192)
            except TimeoutError:
                continue
            if peer[0] != ip:
                continue
            for line in packet.decode("latin-1").splitlines():
                name, _, value = line.partition(":")
                if name.lower() == "location":
                    found.add(value.strip())
    return sorted(found)


def decoder_url(value, ip):
    """Check that the advertised URL belongs to the decoder."""
    url = urlsplit(value)
    return url.scheme == "http" and url.hostname == ip and url.username is None


def locate_control(host):
    """Find the UPnP Resources control URL."""
    ip = socket.gethostbyname(host)
    opener = build_opener(ProxyHandler({}), NoRedirects())
    for location in locations(ip):
        try:
            if not decoder_url(location, ip):
                continue
            with opener.open(location, timeout=2) as response:
                document = response.read(MAX_DESCRIPTION + 1)
            if len(document) > MAX_DESCRIPTION:
                continue
            device = ET.fromstring(document)
            for service in device.findall(".//{*}service"):
                if service.findtext("{*}serviceType") != SERVICE:
                    continue
                control = urljoin(location, service.findtext("{*}controlURL") or "")
                url = urlsplit(control)
                if decoder_url(control, ip) and url.path.endswith("/Resources/control"):
                    address = f"{host}:{url.port}" if url.port else host
                    return urlunsplit((url.scheme, address, url.path, "", ""))
        except (OSError, ValueError, ET.ParseError):
            continue
    return None


def main():
    """Print the control URL for the requested decoder."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("hote", help="Adresse IPv4 ou nom DNS configuré dans Home Assistant")
    args = parser.parse_args()
    try:
        control = locate_control(args.hote.strip().lower().removesuffix("."))
    except OSError as err:
        parser.exit(1, f"Recherche UPnP impossible. {err}\n")
    if not control:
        parser.exit(1, "Service UPnP introuvable. Vérifiez l’adresse et le réseau local.\n")
    print(control)


if __name__ == "__main__":
    main()
