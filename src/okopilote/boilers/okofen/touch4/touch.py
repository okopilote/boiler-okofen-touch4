import logging
import math
import re
import requests
from enum import Enum
from urllib.parse import urljoin
from time import sleep

try:
    from requests.exceptions import JSONDecodeError
except ImportError:
    from json.decoder import JSONDecodeError

logger = logging.getLogger(__name__)


class TouchError(Exception):
    """Generic parent exception for Pelletronic errors."""


class OpMode(Enum):
    """Constants for operation modes."""

    OFF = 0
    AUTO = 1
    HEATING = 2
    SET_BACK = 3


class Touch:
    """
    Interface for the Pelletronic Touch v4, Oekofen JSON Interface V4.00b.
    """

    def __init__(self, url, password, readonly=False):
        self.api_url = url.rstrip("/") + "/" + password + "/"
        self.readonly = readonly
        self._meta = {}
        self._data = {}
        self._session = requests.Session()
        # Query and store meta data
        self._load_meta()

    def _request_touch(self, res, to_json=True, _allow_recursion=True):
        """
        Send a request to the Pelletronic Touch and return the JSON response.
        res may be a URL or a requests.PreparedRequest object.
        """

        if isinstance(res, requests.PreparedRequest):
            r = self._session.send(res, timeout=(10, 40))
        else:
            r = self._session.get(urljoin(self.api_url, res), timeout=(10, 40))
        # Touch enforces some delay before each request
        if r.status_code == requests.codes.unauthorized and _allow_recursion:
            m = re.match("Wait at least ([0-9]+)ms during requests", r.text)
            if m:
                delay = float(m.group(1)) / 1000
                logger.debug(f"Touch wants us to wait {delay}s")
                sleep(delay)
            else:
                logger.warning("Touch rejected us. Wait 4s and retry")
                sleep(4)
            return self._request_touch(res, _allow_recursion=False)
        r.raise_for_status()
        if to_json:
            try:
                return r.json()
            except JSONDecodeError:
                raise TouchError(
                    "Not a JSON response. Wrong password or "
                    + f"setting name? Response: {r.text}"
                )
        else:
            return r.text

    def _load_meta(self):
        """Query meta data from Touch and store them."""

        logger.debug("Load meta data from Touch")
        req = requests.Request("GET", urljoin(self.api_url, "all") + "?")

        # Meta data are queried by ending URL paths with "?" but the char is
        # stripped by several modules like urllib and requests. So we need a
        # hack to restore the "?" before requests send the HTTP packet.
        class MyPreparedRequest(requests.PreparedRequest):
            @property
            def path_url(self):
                path_url = super().path_url
                try:
                    if self.url[-1] == "?" and path_url[-1] != "?":
                        path_url += "?"
                except IndexError:
                    pass
                return path_url

        # Normally a prepared request is created by calling req.prepare() but
        # we need to use our custom class.
        prep = MyPreparedRequest()
        prep.prepare(
            method=req.method,
            url=req.url,
            headers=req.headers,
            files=req.files,
            data=req.data,
            json=req.json,
            params=req.params,
            auth=req.auth,
            cookies=req.cookies,
            hooks=req.hooks,
        )
        # Restore the "?" in the prepared request
        try:
            if req.url[-1] == "?":
                prep.url += "?"
        except IndexError:
            pass
        # Eventually send the request (and get JSON response)
        data = self._request_touch(prep)
        self._meta.update(data)

    def _get(self, device, attr):
        """Return a Touch setting value from cache."""

        try:
            value = self._data[device][attr]
            meta = self._meta[device][attr]
        except KeyError:
            raise TouchError(f'"{device}.{attr}" not found in cache/meta')
        # If a factor exist, apply it to value
        try:
            return value * meta["factor"]
        except KeyError:
            return value

    def _set(self, device, attr, value):
        """Set a Touch setting value."""

        try:
            meta = self._meta[device][attr]
        except KeyError:
            raise TouchError(f'"{device}.{attr}" not found in meta')
        try:
            raw_value = round(value / meta["factor"])
        except KeyError:
            raw_value = int(value)
        request = f"{device}.{attr}={raw_value}"
        logger.info(f"Set {request}")
        if not self.readonly:
            result = self._request_touch(request, to_json=False)
            # Touch put the request in the body response
            if result != request:
                raise TouchError(f"Unknown response to write request: {result}")
        else:
            logger.warning(f"Cant’t set {request}: read only mode")
        self._data[device][attr] = raw_value

    def _round(self, dev, attr, value):
        """Round value with the same precision as the attribute."""
        try:
            factor = self._meta[dev][attr]["factor"]
        except KeyError:
            logging.warning(f"Rounding is irrelevant for {dev}.{attr}")
            return value
        else:
            return round(value, -math.floor(math.log10(factor)))

    def load_data(self, attribute="all"):
        """Query attribute or all data from Touch and and cache them."""

        logger.debug(f"Load {attribute} data from Touch")
        if attribute == "all":
            q = "all"
        else:
            # Look for Touch device and device attribute in dynamic properties
            for name, device, attr in self._dyn_props:
                if name == attribute:
                    q = f"{device}.{attr}"
                    break
            else:
                raise ValueError(
                    f"Touch object has no loadable attribute '{attribute}'"
                )

        data = self._request_touch(q)
        self._data.update(data)

    @property
    def boiler_fired(self):
        """Wether boiler fire is on or off."""
        return self._get("pe1", "L_state") in [1, 2, 3, 4]

    @property
    def hc_op_mode(self):
        """Operation mode of the heating system."""
        return OpMode(self._get("hk1", "mode_auto"))

    @hc_op_mode.setter
    def hc_op_mode(self, mode):
        self._set("hk1", "mode_auto", mode.value)

    @property
    def hc_pumping(self):
        """Wether the water circulator of the heating circuit is running."""
        return self._get("hk1", "L_pump") == 1

    #
    # Dynamically create float properties and their round functions
    #
    # List of (property name, Touch device, device attribute, doc)
    _dyn_props = [
        ("boiler_flow_t", "pe1", "L_temp_act", "Boiler circuit temperature."),
        (
            "boiler_flow_t_set",
            "pe1",
            "L_temp_set",
            "Boiler circuit temperature" + " setpoint.",
        ),
        ("hc_flow_t", "hk1", "L_flowtemp_act", "Heating circuit temperature."),
        (
            "hc_flow_t_set",
            "hk1",
            "L_flowtemp_set",
            "Heating circuit temperature" + " setpoint.",
        ),
        ("room_t", "hk1", "L_roomtemp_act", "Room temperature."),
        ("room_t_set", "hk1", "temp_heat", "Room temperature setpoint."),
        (
            "room_t_set_override",
            "hk1",
            "remote_override",
            "Room temperature " + "setpoint override.",
        ),
    ]
    for name, dev, attr, doc in _dyn_props:
        # Define getter
        exec("def fget(self):\n" + f'    return self._get("{dev}", "{attr}")')
        # Define setter except for read only properties
        if attr[0:2] == "L_":
            fset = None
        else:
            exec(
                "def fset(self, value):\n" + f'    self._set("{dev}", "{attr}", value)'
            )
        # Create property attribute
        exec(f"{name} = property(fget, fset, None, doc)")
        # Create a round function returning the same precision as the attribute
        exec(
            "def fround(self, value):\n"
            + f'    return self._round("{dev}", "{attr}", value)'
        )
        exec(f"{name}_round = fround")

    # @property
    # def room_t(self):
    #    """ Temperature of the room. """
    #    return self._get('hk1', 'L_roomtemp_act')
    #
    # @property
    # def room_t_set(self):
    #    """ Temperature setpoint of the room. """
    #    return self._get('hk1', 'temp_heat')
    #
    # @room_t_set.setter
    # def room_t_set(self, value):
    #    self._set('hk1', 'temp_heat', value)
    #
    # @property
    # def boiler_flow_t(self):
    #    """ Temperature of the flow in the boiler circuit. """
    #    return self._get('pe1', 'L_temp_act')
    #
    # @property
    # def boiler_flow_t_set(self):
    #    """ Temperature setpoint of the flow in the boiler circuit. """
    #    return self._get('pe1', 'L_temp_set')
    #
    # @property
    # def hc_flow_t(self):
    #    """ Temperature of the flow in the heating circuit. """
    #    return self._get('hk1', 'L_flowtemp_act')
    #
    # @property
    # def hc_flow_t_set(self):
    #    """ Temperature setpoint of the flow in the heating circuit. """
    #    return self._get('hk1', 'L_flowtemp_set')
    #
    # @property
    # def room_t_set_override(self):
    #    """ Override of the temperature setpoint of the room. """
    #    return self._get('hk1', 'remote_override')
    #
    # @room_t_set_override.setter
    # def room_t_set_override(self, value):
    #    self._set('hk1', 'remote_override', value)
