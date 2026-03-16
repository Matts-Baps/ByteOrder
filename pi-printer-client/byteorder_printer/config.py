import json
import os
from dataclasses import dataclass, asdict
from typing import Optional

CONFIG_PATH = os.environ.get("BYTEORDER_CONFIG", "/etc/byteorder-printer/config.json")
BOOT_CONFIG_PATH = os.environ.get("BYTEORDER_BOOT_CONFIG", "/boot/firmware/byteorder.json")


@dataclass
class Config:
    api_base: str = "https://byteorder.example.com"
    mac_address: str = ""
    kitchen_id: Optional[str] = None
    wifi_ssid: Optional[str] = None
    wifi_psk: Optional[str] = None


def load() -> Config:
    """Load config from disk.

    If the main config file exists, use it (saved credentials take priority).
    Otherwise, seed from /boot/firmware/byteorder.json if present — allows
    pre-provisioning WiFi credentials before first boot without going through
    the AP setup portal.
    """
    try:
        with open(CONFIG_PATH) as f:
            data = json.load(f)
        return Config(**{k: v for k, v in data.items() if k in Config.__dataclass_fields__})
    except (FileNotFoundError, json.JSONDecodeError, TypeError):
        pass

    try:
        with open(BOOT_CONFIG_PATH) as f:
            data = json.load(f)
        return Config(**{k: v for k, v in data.items() if k in Config.__dataclass_fields__})
    except (FileNotFoundError, json.JSONDecodeError, TypeError):
        pass

    return Config()


def save(cfg: Config) -> None:
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(asdict(cfg), f, indent=2)
