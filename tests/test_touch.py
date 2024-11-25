#!/usr/bin/env python3
import logging
from time import sleep
from okopilote.boilers.okofen.touch4.touch import Touch, OpMode

logging.basicConfig(level=logging.INFO)

url = "http://localhost:3938"
password = "mypass123"

pellog = logging.getLogger("Touch4")
pellog.setLevel(logging.DEBUG)

p = Touch(url, password, readonly=False)
p.load_data()
for attr in [
    "boiler_fired",
    "boiler_flow_t",
    "boiler_flow_t_set",
    "hc_flow_t",
    "hc_flow_t_set",
    "hc_pumping",
    "hc_op_mode",
    "room_t",
    "room_t_set",
    "room_t_set_override",
]:
    print(attr, "=", getattr(p, attr))

# p.readonly = False
print("temp_heat:", p._data["hk1"]["temp_heat"])
p.room_t_set -= 0.1
print("temp_heat:", p._data["hk1"]["temp_heat"])
print("Set operation mode to HEATING")
p.hc_op_mode = OpMode.HEATING
sleep(2)
print("Set operation mode to SET_BACK")
p.hc_op_mode = OpMode.SET_BACK
sleep(2)
print("Set operation mode to OFF")
p.hc_op_mode = OpMode.OFF
sleep(2)
print("Set operation mode to AUTO")
p.hc_op_mode = OpMode.AUTO
