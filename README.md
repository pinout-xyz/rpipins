# Raspberry Pi GPIO Pinout

A beautiful GPIO pinout and pin function guide for the Raspberry Pi with live pin config, drive and level monitoring.

![Example image](https://github.com/pinout-xyz/rpipins/assets/1746967/67f2aa9d-8d3f-4086-84c9-291d7eb11cc2)

[![Build Status](https://img.shields.io/github/actions/workflow/status/pinout-xyz/rpipins/build.yml?branch=main)](https://github.com/pinout-xyz/rpipins/actions/workflows/build.yml)
[![PyPi Package](https://img.shields.io/pypi/v/rpipins.svg)](https://pypi.python.org/pypi/rpipins)
[![Python Versions](https://img.shields.io/pypi/pyversions/rpipins.svg)](https://pypi.python.org/pypi/rpipins)

# Usage

```
usage: rpipins [--...] [--all] or {i2c,spi} [--find <text>]
       --pins          - show physical pin numbers
       --all or {i2c,spi} - pick list of interfaces to show
       --hide-gpio     - hide GPIO pins
       --debug         - show GPIO status
       --light         - melt your eyeballs
       --find "<text>" - highlight pins matching <text>
                         supports regex if you"re feeling sassy!

eg:    rpipins i2c                    - show GPIO and I2C labels
       rpipins                        - basic GPIO pinout
       rpipins --all --find "I2C1"    - highlight any "I2C1" labels
       rpipins --all --find "SPI* SCLK" - highlight any SPI clock pins
```

# Installing

* Just run `python3 -m pip install rpipins`

# Acknowledgements

This project was inspired by GPIO Zero's command-line pinout - https://github.com/gpiozero/gpiozero
