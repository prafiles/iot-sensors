"""Shared fixtures for the iot-sensors test suite.

The production modules import hardware-only packages (Adafruit_DHT, sense_hat)
that are not installable in CI, so we register stub modules in sys.modules
before loading the real modules via importlib (their filenames contain
hyphens, so they cannot be imported with a plain ``import``).
"""
import importlib.util
import os
import sys
import types

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)


class _FakeAdafruitDHT(types.ModuleType):
    def __init__(self):
        super().__init__("Adafruit_DHT")
        self.DHT11 = 11
        self.DHT22 = 22
        self.AM2302 = 23

    def read_retry(self, sensor, pin):
        return (None, None)


class _FakeSenseHat:
    """Stand-in for sense_hat.SenseHat with settable sensor values."""

    def __init__(self):
        self.humidity = 50.0
        self.pressure = 1010.0
        self.temperature = 20.0
        self.acceleration = {"x": 0.0, "y": 0.0, "z": 1.0}
        self.rotation = None
        self.messages = []

    def set_rotation(self, angle):
        self.rotation = angle

    def show_message(self, *args, **kwargs):
        self.messages.append(args[0] if args else "")

    def get_humidity(self):
        return self.humidity

    def get_pressure(self):
        return self.pressure

    def get_temperature(self):
        return self.temperature

    def get_accelerometer_raw(self):
        return dict(self.acceleration)

    def get_events(self):
        return []


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(REPO_ROOT, filename))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _install_stubs():
    sys.modules.setdefault("Adafruit_DHT", _FakeAdafruitDHT())
    sense_hat_stub = types.ModuleType("sense_hat")
    sense_hat_stub.SenseHat = _FakeSenseHat
    sys.modules.setdefault("sense_hat", sense_hat_stub)


_install_stubs()

sensor_iot = _load("sensor_iot", "sensor-iot.py")
sense_hat_pi = _load("sense_hat_pi", "sense-hat-pi.py")

# The instance the module created at import time (records boot side effects).
BOOT_SENSE = sense_hat_pi.sense


@pytest.fixture
def fake_sense(monkeypatch):
    """Replace the module-level SenseHat instance with a fresh fake."""
    fake = _FakeSenseHat()
    monkeypatch.setattr(sense_hat_pi, "sense", fake)
    return fake
