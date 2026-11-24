"""Verify UPnP discovery without contacting real devices."""

from io import BytesIO
from socket import gaierror

import pytest

from scripts import trouver_upnp

IP = "192.0.2.10"
LOCATION = f"http://{IP}:49153/description.xml"
CONTROL_PATH = "/devices/test/Resources/control"


class FakeSocket:
    """Return SSDP replies from the test decoder and an unrelated host."""

    def __init__(self):
        """Prepare one unrelated packet, one malformed packet and a valid reply."""
        self.sent = []
        self.replies = iter(
            [
                (b"LOCATION: http://192.0.2.20/unrelated", ("192.0.2.20", 1900)),
                (b"NO-LOCATION: ignore", (IP, 1900)),
                (f"LOCATION: {LOCATION}\r\n".encode(), (IP, 1900)),
            ],
        )

    def __enter__(self):
        """Simulate opening a socket."""
        return self

    def __exit__(self, *args):
        """Simulate closing a socket."""

    def settimeout(self, _seconds):
        """Accept the discovery timeout."""

    def sendto(self, packet, destination):
        """Record search attempts and simulate unavailable unicast."""
        self.sent.append((packet, destination))
        if destination[0] == IP:
            raise OSError("unicast unavailable")

    def recvfrom(self, _size):
        """Read a reply or simulate a receive timeout."""
        try:
            return next(self.replies)
        except StopIteration as err:
            raise TimeoutError from err


def test_locations_checks_packet_sender(monkeypatch):
    """Keep the requested decoder's advertised description."""
    sock = FakeSocket()
    monkeypatch.setattr(trouver_upnp.socket, "socket", lambda *_: sock)
    times = iter((0, 0, 0, 0, 0, 4))
    monkeypatch.setattr(trouver_upnp.time, "monotonic", lambda: next(times))
    assert trouver_upnp.locations(IP) == [LOCATION]
    assert [destination for _, destination in sock.sent] == [(IP, 1900), (trouver_upnp.MULTICAST, 1900)]


class DescriptionServer:
    """Serve a UPnP device description for the fake decoder."""

    def __init__(self, document):
        """Store the XML response and track requests."""
        self.document = document
        self.requests = []

    def open(self, url, *, timeout):
        """Return the configured response as a binary stream."""
        self.requests.append((url, timeout))
        return BytesIO(self.document)


@pytest.mark.parametrize(
    ("control_path", "expected"),
    [
        (CONTROL_PATH, f"http://decoder.example.com:49153{CONTROL_PATH}"),
        (f"http://192.0.2.20{CONTROL_PATH}", None),
    ],
)
def test_locate_control_uses_configured_hostname(monkeypatch, control_path, expected):
    """Reject remote control endpoints and preserve the configured DNS name."""
    description = (
        "<root><serviceList><service><serviceType>"
        f"{trouver_upnp.SERVICE}</serviceType><controlURL>{control_path}</controlURL>"
        "</service></serviceList></root>"
    ).encode()
    server = DescriptionServer(description)
    monkeypatch.setattr(trouver_upnp.socket, "gethostbyname", lambda _: IP)
    monkeypatch.setattr(trouver_upnp, "locations", lambda _: ["http://192.0.2.20/description.xml", LOCATION])
    monkeypatch.setattr(trouver_upnp, "build_opener", lambda *_: server)
    assert trouver_upnp.locate_control("decoder.example.com") == expected
    assert server.requests == [(LOCATION, 2)]


def test_locate_control_ignores_invalid_xml(monkeypatch):
    """Continue when an SSDP response points to a non-XML resource."""
    monkeypatch.setattr(trouver_upnp.socket, "gethostbyname", lambda _: IP)
    monkeypatch.setattr(trouver_upnp, "locations", lambda _: [LOCATION])
    monkeypatch.setattr(trouver_upnp, "build_opener", lambda *_: DescriptionServer(b"not XML"))
    assert trouver_upnp.locate_control(IP) is None


def test_main_prints_control_url(monkeypatch, capsys):
    """Print only the usable URL after normalizing the hostname."""
    result = f"http://{IP}:49153{CONTROL_PATH}"
    monkeypatch.setattr("sys.argv", ["trouver_upnp.py", " Decoder.EXAMPLE.Com. "])

    def locate(host):
        assert host == "decoder.example.com"
        return result

    monkeypatch.setattr(trouver_upnp, "locate_control", locate)
    trouver_upnp.main()
    assert capsys.readouterr().out == result + "\n"


@pytest.mark.parametrize("error", [None, gaierror("unknown hostname")])
def test_main_reports_discovery_failure(monkeypatch, capsys, error):
    """Report failed discovery with a nonzero exit code."""
    monkeypatch.setattr("sys.argv", ["trouver_upnp.py", IP])

    def locate(_host):
        if error:
            raise error
        return None

    monkeypatch.setattr(trouver_upnp, "locate_control", locate)
    with pytest.raises(SystemExit) as outcome:
        trouver_upnp.main()
    assert outcome.value.code == 1
    assert "UPnP" in capsys.readouterr().err
