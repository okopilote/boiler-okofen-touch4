import logging
from time import sleep

from okopilote.devices.common.abstract import AbstractBoiler

from .touch import Touch, OpMode

logger = logging.getLogger(__name__)


def from_conf(conf):
    conf.setdefault("readonly", "no")
    conf.setdefault("room_t_set_max", "22.0")
    return Boiler(
        url=conf.get("url"),
        password=conf.get("password"),
        readonly=conf.getboolean("readonly"),
        room_t_set_max=conf.getfloat("room_t_set_max"),
    )


class Boiler(AbstractBoiler):

    def __init__(self, url, password, readonly=False, room_t_set_max=22.0):
        self.touch = Touch(url, password, readonly=readonly)
        self.room_t_set_max = room_t_set_max
        # Backup Pelletronic op mode and temperature setpoint to be able
        # to restore those values after enforcing
        self.bk_op_mode = None
        self.force_op_mode = None
        self.bk_room_t_set = None
        self.force_room_t_set = None

    def acquire(self):
        self.touch.load_data()

    @property
    def accept_control(self):
        """Is the boiler set up to be controlled?"""
        if self.touch.hc_op_mode in [OpMode.AUTO, OpMode.HEATING]:
            return True
        else:
            sleep(1)
            self.acquire()
            if self.touch.hc_op_mode in [OpMode.AUTO, OpMode.HEATING]:
                return True
            else:
                return False

    @property
    def ambiant_temperature(self):
        """Ambiant temperature mesured by the boiler’s sensor"""
        return self.touch.room_t

    @property
    def delivering_heat(self):
        """Is the heating circuit devilering heat?"""
        return self.touch.hc_pumping

    def force_heating(self, delta=0.0):
        """
        Force heating room by setting the heating circuit operation mode to
        "heating" and by rising the temperature set high enough + delta.
        """

        self._force_hc_op_mode()
        self._force_room_setpoint(delta)

    @property
    def generating_heat(self):
        """Is the boiler generating heat?"""
        return self.touch.boiler_fired

    @property
    def heat_available(self):
        """Is hot water available without ignit fire?"""
        if self.touch.boiler_fired or self.touch.boiler_flow_t > max(
            70, self.touch.boiler_flow_t_set
        ):
            return True
        else:
            return False

    def release_heating(self):
        """
        Restore the Pelletronic operation mode and temperature set to their
        values before the enforcement.
        """

        self._release_hc_op_mode()
        self._release_room_setpoint()

    def does_accept_ctrl(self):
        """DEPRECATED- Kept for backward compatibility."""
        return self.accept_control

    def is_heat_avail(self):
        """DEPRECATED- Kept for backward compatibility."""
        return self.heat_available

    def is_gen_heat(self):
        """DEPRECATED- Kept for backward compatibility."""
        return self.generating_heat

    def is_deliv_heat(self):
        """DEPRECATED- Kept for backward compatibility."""
        return self.delivering_heat

    def _force_hc_op_mode(self):
        """Switch heating circuit operation mode to heating mode."""
        if self.touch.hc_op_mode is not OpMode.HEATING:
            logger.info(
                "Force Pelletronic op mode from "
                + f"{self.touch.hc_op_mode.name} to {OpMode.HEATING.name}"
            )
            # Backup op mode as it will be restored when releasing heating
            self.bk_op_mode = self.touch.hc_op_mode
            self.force_op_mode = OpMode.HEATING
            self.touch.hc_op_mode = OpMode.HEATING
            logger.debug(
                f"force_op_mode={self.force_op_mode}, bk_op_mode="
                + f"{self.bk_op_mode}"
            )

    def _force_room_setpoint(self, offset):
        """Rise room temperature setpoint to have it heated."""
        previous_force_t = self.force_room_t_set
        previous_room_t_set = self.touch.room_t_set
        # Rise living temperature setpoint to switch on the heating system
        # (bigger rise) or to keep it heating (smaller rise). To decide on, we
        # look at the flow temperature setpoint of the heating circuit.
        shift = max(offset, 0.3 if self.touch.hc_flow_t_set > 20 else 1.2)
        logger.debug(f"shift={shift}")
        # self.force_room_t_set = round(min(self.touch.room_t + shift,
        #                                  self.room_t_set_max), 1)
        self.force_room_t_set = self._round_t(
            min(self.touch.room_t + shift, self.room_t_set_max)
        )
        # if self.force_room_t_set != round(self.touch.room_t_set, 1):
        if self.force_room_t_set != self._round_t(self.touch.room_t_set):
            logger.info(
                "Change living temperature set from "
                + f"{self.touch.room_t_set}°C to {self.force_room_t_set}°C"
                + f"(T_living={self.touch.room_t}°C)"
            )
            if self.force_room_t_set == self.room_t_set_max:
                logger.warning("Room t setpoint is risen to its maximum")
            self.touch.room_t_set = self.force_room_t_set
            logger.debug(f"force_room_t_set={self.force_room_t_set}")
        # Backup temperature setpoint except when it's value comes from a
        # previous forcing.
        if self.force_room_t_set is not None and previous_room_t_set not in [
            self.force_room_t_set,
            previous_force_t,
            self.bk_room_t_set,
        ]:
            # self.bk_room_t_set = round(previous_room_t_set, 1)
            self.bk_room_t_set = self._round_t(previous_room_t_set)
            logger.debug(f"bk_room_t_set={self.bk_room_t_set}")

    def _release_hc_op_mode(self):
        """Revert operation mode to its value before being forced."""
        if self.bk_op_mode is not None and self.touch.hc_op_mode is self.force_op_mode:
            logger.info(f"Restore op mode to {self.bk_op_mode.name}")
            self.touch.hc_op_mode = self.bk_op_mode
            # Erase backup values
            self.bk_op_mode, self.force_op_mode = None, None

    def _release_room_setpoint(self):
        """Restore temperature set to its value before being forced."""
        # The code for restoring the setpoint that was set before forcing heat is
        # buggy, so we just restore a fixed value.
        self.touch.room_t_set = 16.0
        # if (self.bk_room_t_set is not None and round(self.touch.room_t_set, 1)
        #        == round(self.force_room_t_set, 1)):
        if self.bk_room_t_set is not None and self._round_t(
            self.touch.room_t_set
        ) == self._round_t(self.force_room_t_set):
            logger.info(f"Restore living t set to {self.bk_room_t_set}°C")
            self.touch.room_t_set = self.bk_room_t_set
            # Erase backup values
            self.bk_room_t_set, self.force_room_t_set = None, None

    def _round_t(self, value):
        """Round value at the same precision than Touch room temperature."""
        return self.touch.room_t_set_round(value)
