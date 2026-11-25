"""Configuration and STB8 key names."""

DOMAIN = "sfr_box_8"
DEFAULT_NAME = "SFR Box 8"
DEFAULT_PORT = 7682
CONF_CHANNELS = "channels"
CONF_UPNP_URL = "upnp_url"
UPNP_SERVICE = "urn:neufboxtv-org:service:Resources:1"
DEFAULT_CHANNELS = "\n".join(str(number) for number in range(1, 10))

# STB8 key mapping adapted from GehDoc/sfr-tv-box-remote (MIT).
KEYS = {
    "VOL_UP": "volUp",
    "VOL_DOWN": "volDown",
    "CHAN_UP": "channelUp",
    "CHAN_DOWN": "channelDown",
    "HOME": "home",
    "BACK": "back",
    "POWER": "power",
    "FFWD": "fastForward",
    "REWIND": "fastBackward",
    "PLAY_PAUSE": "playPause",
    "STOP": "stop",
    "RECORD": "record",
    "MUTE": "mute",
    "UP": "up",
    "LEFT": "left",
    "RIGHT": "right",
    "DOWN": "down",
    "OK": "ok",
    **{f"NUM_{digit}": digit for digit in "0123456789"},
}
