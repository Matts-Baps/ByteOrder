import json
import os
import tempfile
from unittest.mock import patch


def _write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f)


def test_load_returns_defaults_when_no_files():
    with tempfile.TemporaryDirectory() as tmp:
        config_path = os.path.join(tmp, "etc", "config.json")
        boot_path = os.path.join(tmp, "boot", "byteorder.json")
        with patch("byteorder_printer.config.CONFIG_PATH", config_path), \
             patch("byteorder_printer.config.BOOT_CONFIG_PATH", boot_path):
            from byteorder_printer.config import load
            cfg = load()
        assert cfg.wifi_ssid is None
        assert cfg.api_base == "https://byteorder.example.com"


def test_boot_config_seeds_config_on_first_boot():
    with tempfile.TemporaryDirectory() as tmp:
        config_path = os.path.join(tmp, "etc", "config.json")
        boot_path = os.path.join(tmp, "boot", "byteorder.json")
        _write_json(boot_path, {
            "wifi_ssid": "MyNetwork",
            "wifi_psk": "secret123",
            "api_base": "https://admin.example.com/api",
        })
        with patch("byteorder_printer.config.CONFIG_PATH", config_path), \
             patch("byteorder_printer.config.BOOT_CONFIG_PATH", boot_path):
            from byteorder_printer import config as cfg_mod
            cfg = cfg_mod.load()
        assert cfg.wifi_ssid == "MyNetwork"
        assert cfg.wifi_psk == "secret123"
        assert cfg.api_base == "https://admin.example.com/api"


def test_boot_config_does_not_override_existing_saved_config():
    with tempfile.TemporaryDirectory() as tmp:
        config_path = os.path.join(tmp, "etc", "config.json")
        boot_path = os.path.join(tmp, "boot", "byteorder.json")
        _write_json(config_path, {
            "wifi_ssid": "SavedNetwork",
            "wifi_psk": "saved_pass",
            "api_base": "https://saved.example.com/api",
        })
        _write_json(boot_path, {
            "wifi_ssid": "BootNetwork",
            "wifi_psk": "boot_pass",
            "api_base": "https://boot.example.com/api",
        })
        with patch("byteorder_printer.config.CONFIG_PATH", config_path), \
             patch("byteorder_printer.config.BOOT_CONFIG_PATH", boot_path):
            from byteorder_printer import config as cfg_mod
            cfg = cfg_mod.load()
        assert cfg.wifi_ssid == "SavedNetwork"


def test_boot_config_ignores_unknown_keys():
    with tempfile.TemporaryDirectory() as tmp:
        config_path = os.path.join(tmp, "etc", "config.json")
        boot_path = os.path.join(tmp, "boot", "byteorder.json")
        _write_json(boot_path, {
            "wifi_ssid": "MyNetwork",
            "unknown_key": "should_be_ignored",
        })
        with patch("byteorder_printer.config.CONFIG_PATH", config_path), \
             patch("byteorder_printer.config.BOOT_CONFIG_PATH", boot_path):
            from byteorder_printer import config as cfg_mod
            cfg = cfg_mod.load()
        assert cfg.wifi_ssid == "MyNetwork"


def test_boot_config_invalid_json_is_ignored():
    with tempfile.TemporaryDirectory() as tmp:
        config_path = os.path.join(tmp, "etc", "config.json")
        boot_path = os.path.join(tmp, "boot", "byteorder.json")
        os.makedirs(os.path.dirname(boot_path), exist_ok=True)
        with open(boot_path, "w") as f:
            f.write("not valid json")
        with patch("byteorder_printer.config.CONFIG_PATH", config_path), \
             patch("byteorder_printer.config.BOOT_CONFIG_PATH", boot_path):
            from byteorder_printer import config as cfg_mod
            cfg = cfg_mod.load()
        assert cfg.wifi_ssid is None
