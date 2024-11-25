#!/usr/bin/env python3
import logging
from configparser import ConfigParser
from okopilote.boilers.okofen.touch4 import get_boiler_from_conf

logging.basicConfig(level=logging.INFO)

url = "http://localhost:3938"
password = "mypass123"

pellog = logging.getLogger("Touch4")
pellog.setLevel(logging.DEBUG)

conf = ConfigParser()
conf.add_section("boiler")
conf.set("boiler", "url", url)
conf.set("boiler", "password", password)
conf.set("boiler", "readonly", "no")
b = get_boiler_from_conf(conf["boiler"])
b.acquire()
print(f"acquire: {b.touch._data.keys()}")
for m in ["accept_control", "generating_heat", "delivering_heat", "heat_available"]:
    print(f"{m}:", getattr(b, m))
b.force_heating()
# b.release_heating()
