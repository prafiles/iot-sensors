"""Unit tests for sense-hat-pi.py (Sense HAT -> MQTT publisher)."""
import json
import re

import pytest

from conftest import BOOT_SENSE, sense_hat_pi


@pytest.fixture
def config():
    return {"sensor_settings": {"measurement": "sensehat", "location": "office"}}


def test_module_exposes_expected_api():
    assert callable(sense_hat_pi.get_reading)
    assert callable(sense_hat_pi.read_config)
    assert sense_hat_pi.CONFIG_FILE == "settings.conf"


def test_boot_sequence_runs():
    # Import-time side effects on the module-level SenseHat instance:
    # rotation reset and a startup message.
    assert BOOT_SENSE.rotation == 0
    assert "Starting" in " ".join(BOOT_SENSE.messages)


def test_get_reading_builds_full_payload(fake_sense, config):
    fake_sense.temperature = 20.0
    fake_sense.humidity = 50.0
    fake_sense.pressure = 1010.1234
    fake_sense.acceleration = {"x": 0.12345, "y": -0.5, "z": 0.99999}

    data = sense_hat_pi.get_reading(config)
    record = data[0]
    json.dumps(record)

    assert record["measurement"] == "sensehat"
    assert record["tags"] == {"location": "office"}
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", record["time"])

    fields = record["fields"]
    assert fields["temperature_c"] == 20.0
    assert fields["temperature_f"] == 68.0
    assert fields["humidity"] == 50.0
    assert fields["pressure"] == 1010.123
    assert fields["x"] == 0.1235
    assert fields["y"] == -0.5
    assert fields["z"] == 1.0
    # dew_point = 20 - (100-50)/5 = 10.0
    assert fields["dew_point"] == 10.0
    # Steadman heat index at 68F / 50% RH (golden values).
    assert fields["heat_index_f"] == 77.35
    assert fields["heat_index_c"] == 25.19


def test_get_reading_clamps_high_humidity(fake_sense, config):
    # Documented upstream sense-hat bug workaround: >99 becomes 99.0.
    fake_sense.humidity = 105.0
    fake_sense.temperature = 20.0
    fields = sense_hat_pi.get_reading(config)[0]["fields"]
    assert fields["humidity"] == 99.0
    assert fields["dew_point"] == 19.8
    assert fields["heat_index_f"] == 59.89
    assert fields["heat_index_c"] == 15.49


def test_get_reading_keeps_humidity_just_below_clamp(fake_sense, config):
    fake_sense.humidity = 99.0
    fields = sense_hat_pi.get_reading(config)[0]["fields"]
    assert fields["humidity"] == 99.0


def test_get_reading_never_returns_none(fake_sense, config):
    # Unlike the DHT path, the Sense HAT path always returns a payload.
    assert sense_hat_pi.get_reading(config) is not None


def test_read_config_parses_sections(tmp_path, monkeypatch):
    conf = tmp_path / "settings.conf"
    conf.write_text("[mqtt_settings]\nport = 1883\nusername = root\n")
    monkeypatch.setattr(sense_hat_pi, "CONFIG_FILE", str(conf))
    config = sense_hat_pi.read_config()
    assert config == {"mqtt_settings": {"port": "1883", "username": "root"}}


def test_read_config_missing_file_returns_empty_dict(tmp_path, monkeypatch):
    monkeypatch.setattr(sense_hat_pi, "CONFIG_FILE", str(tmp_path / "nope.conf"))
    assert sense_hat_pi.read_config() == {}
