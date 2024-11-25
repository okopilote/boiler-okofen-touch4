# okofen-pelletronic-touch4

`okopilote-boilers-okofen-touch4` is a module for the Okopilote controller software.
It enables the control of an Okofen boiler fitted with a Pellotronic Touch v4.

## Table of Contents

- [Installation](#installation)
- [Usage](#Usage)
- [License](#license)

## Installation

### FUTUR: install packages from PyPi

```console
# Install the module along with the controller as an optional dependency:
pip install okopilote-controller[okofen-touch4]

# Or install it separately
pip install okopilote-boilers-okofen-touch4
```

### PRESENT: build and install packages

Install package and its requirements from distribution files:

```console
pip install okopilote_boilers_okofen_touch4-a.b.c-py3-none-any.wh
pip install okopilote_devices_common-d.e.f-py3-none-any.whl
```

## Usage

In the controller configuration file, section `boiler`, set the module and its
parameters:

```ini
[boiler]
module = okofen.pelletronic.touch4

# URL and password of the Pelletronic Touch4 API server (mandatory)
url = http://PELLE.TOUCH.IP.ADDRESS:3938
password = pelletouchpassword

# Optional: prevent module from modifying Touch4 setting. Default to no
#readonly = yes

# Optional: when enforcing heating, do not set temperature set point above this
# value, in °C. Default to 22.0°C.
#room_t_set_max = 24.0
```

## License

`okopilote-boilers-okofen-touch4` is distributed under the terms of the
[MIT](https://spdx.org/licenses/MIT.html) license.
