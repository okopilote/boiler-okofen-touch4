from okopilote.devices.common.abstract import AbstractTemperatureSensor

from .touch import Touch


def from_conf(conf):
    return AmbiantSensor(url=conf.get("url"), password=conf.get("password"))


class AmbiantSensor(AbstractTemperatureSensor):

    def __init__(self, url, password):
        self._touch = Touch(url, password, readonly=True)

    @property
    def temperature(self):
        # Refresh then return value
        self._touch.load_data("room_t")
        return self._touch.room_t
