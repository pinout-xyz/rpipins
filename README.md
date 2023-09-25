# Raspberry Pi GPIO Pinout

A beautiful GPIO pinout and pin function guide for the Raspberry Pi.

![Example image](https://raw.githubusercontent.com/pinout-xyz/rpipins/main/example.png)

[![Build Status](https://img.shields.io/github/actions/workflow/status/pinout-xyz/rpipins/build.yml?branch=main)](https://github.com/pinout-xyz/rpipins/actions/workflows/build.yml)
[![PyPi Package](https://img.shields.io/pypi/v/rpipins.svg)](https://pypi.python.org/pypi/rpipins)
[![Python Versions](https://img.shields.io/pypi/pyversions/rpipins.svg)](https://pypi.python.org/pypi/rpipins)

# Usage

```
usage: rpipins [--pins] [--all] or {spi,i2c,uart,pwm}
       --pins - show physical pin numbers
       --all or {spi,i2c,uart,pwm} - pick list of interfaces to show
       --hide-gpio - hide GPIO pins
       --find "<text>" - highlight pins matching <text>

eg:    rpipins i2c  - show GPIO and I2C labels
       rpipins      - basic GPIO pinout
```

# Installing

* Just run `python3 -m pip install rpipins`

# Acknowledgements

This project was inspired by GPIO Zero's command-line pinout - https://github.com/gpiozero/gpiozero
