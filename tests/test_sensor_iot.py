"""Unit tests for sensor-iot.py (DHT22 -> MQTT publisher)."""
import json
import re

import pytest

from conftest import sensor_iot


@pytest.fixture
def config():
    return {
        "sensor_settings": {
            "sensor": "DHT22",
            "sensor_gpio_pin": "4",
            "measurement": "dht22",
            "location": "lobby",
        }
    }


def test_module_exposes_expected_api():
    assert callable(sensor_iot.get_reading)
    assert callable(sensor_iot.read_config)
    assert sensor_iot.CONFIG_FILE == "settings.conf"


def test_get_reading_builds_full_payload(monkeypatch, config):
    monkeypatch.setattr(sensor_iot.Adafruit_DHT, "read_retry",
                        lambda sensor, pin: (60.0, 25.0), raising=True)
    data = sensor_iot.get_reading(config)

    assert isinstance(data, list) and len(data) == 1
    record = data[0]
    assert record["measurement"] == "dht22"
    assert record["tags"] == {"location": "lobby"}
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", record["time"])
    # Payload must be JSON-serializable the way main() publishes it.
    json.dumps(record)

    fields = record["fields"]
    assert fields["temperature_c"] == 25.0
    assert fields["temperature_f"] == 77.0
    assert fields["humidity"] == 60.0
    # dew_point = 25 - (100-60)/5 = 17.0
    assert fields["dew_point"] == 17.0
    # Steadman heat index at 77F / 60% RH (golden values).
    assert fields["heat_index_f"] == 78.78
    assert fields["heat_index_c"] == 25.99


def test_get_reading_rounds_to_two_decimals(monkeypatch, config):
    monkeypatch.setattr(sensor_iot.Adafruit_DHT, "read_retry",
                        lambda sensor, pin: (45.678, 21.234), raising=True)
    fields = sensor_iot.get_reading(config)[0]["fields"]
    assert fields["temperature_c"] == 21.23
    assert fields["humidity"] == 45.68


def test_get_reading_passes_sensor_and_pin(monkeypatch, config):
    seen = {}

    def spy(sensor, pin):
        seen["sensor"] = sensor
        seen["pin"] = pin
        return (50.0, 20.0)

    monkeypatch.setattr(sensor_iot.Adafruit_DHT, "read_retry", spy, raising=True)
    sensor_iot.get_reading(config)
    assert seen == {"sensor": sensor_iot.Adafruit_DHT.DHT22, "pin": "4"}


@pytest.mark.parametrize("humidity", [None, -1.0, 100.5, 101])
def test_get_reading_rejects_bad_humidity(monkeypatch, config, humidity):
    monkeypatch.setattr(sensor_iot.Adafruit_DHT, "read_retry",
                        lambda sensor, pin: (humidity, 20.0), raising=True)
    assert sensor_iot.get_reading(config) is None


def test_get_reading_accepts_boundary_values(monkeypatch, config):
    monkeypatch.setattr(sensor_iot.Adafruit_DHT, "read_retry",
                        lambda sensor, pin: (100.0, 20.0), raising=True)
    assert sensor_iot.get_reading(config) is not None


def test_read_config_parses_sections(tmp_path, monkeypatch):
    conf = tmp_path / "settings.conf"
    conf.write_text(
        "[sensor_settings]\n"
        "measurement = dht22\n"
        "location = lobby\n"
        "[mqtt_settings]\n"
        "broker_address = 10.0.4.6\n"
        "port = 1883\n"
    )
    monkeypatch.setattr(sensor_iot, "CONFIG_FILE", str(conf))
    config = sensor_iot.read_config()
    assert config["sensor_settings"]["measurement"] == "dht22"
    assert config["sensor_settings"]["location"] == "lobby"
    assert config["mqtt_settings"]["broker_address"] == "10.0.4.6"
    assert config["mqtt_settings"]["port"] == "1883"


def test_read_config_missing_file_returns_empty_dict(tmp_path, monkeypatch):
    monkeypatch.setattr(sensor_iot, "CONFIG_FILE", str(tmp_path / "nope.conf"))
    assert sensor_iot.read_config() == {}
