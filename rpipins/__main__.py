#!/usr/bin/env python3
import os
import re
import stat
import subprocess
import sys
import time

try:
    import gpiod
except ImportError:
    gpiod = None

import rich
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

"""
rpipins, by @gadgetoid

Support me:
https://ko-fi.com/gadgetoid
https://github.com/sponsors/Gadgetoid
https://www.patreon.com/gadgetoid

Shout-out to Raspberry Pi Spy for having almost this exact idea first:
https://www.raspberrypi-spy.co.uk/2022/12/pi-pico-pinout-display-on-the-command-line/
"""

__version__ = "1.0.0"

PINOUT = [line.split("|") for line in """
         |          |       |  |┏━━━┓|  |       |          |
         |          |3v3    |1 |┃▣ ◎┃|2 |5v     |          |
         |I2C1 SDA  |GPIO 2 |3 |┃◎ ◎┃|4 |5v     |          |
         |I2C1 SCL  |GPIO 3 |5 |┃◎ ◎┃|6 |Ground |          |
         |          |GPIO 4 |7 |┃◎ ◎┃|8 |GPIO 14|          |
         |          |Ground |9 |┃◎ ◎┃|10|GPIO 15|          |
SPI1 CE1 |          |GPIO 17|11|┃◎ ◎┃|12|GPIO 18|          |SPI1 CE0
         |          |GPIO 27|13|┃◎ ◎┃|14|Ground |          |
         |          |GPIO 22|15|┃◎ ◎┃|16|GPIO 23|          |
         |          |3v3    |17|┃◎ ◎┃|18|GPIO 24|          |
SPI0 MOSI|          |GPIO 10|19|┃◎ ◎┃|20|Ground |          |
SPI0 MISO|          |GPIO 9 |21|┃◎ ◎┃|22|GPIO 25|          |
SPI0 SCLK|          |GPIO 11|23|┃◎ ◎┃|24|GPIO 8 |          |SPI0 CE0
         |          |Ground |25|┃◎ ◎┃|26|GPIO 7 |          |SPI0 CE1
         |EEPROM SDA|GPIO 0 |27|┃◎ ◎┃|28|GPIO 1 |EEPROM SCL|
         |          |GPIO 5 |29|┃◎ ◎┃|30|Ground |          |
         |          |GPIO 6 |31|┃◎ ◎┃|32|GPIO 12|          |
         |          |GPIO 13|33|┃◎ ◎┃|34|Ground |          |
SPI1 MISO|          |GPIO 19|35|┃◎ ◎┃|36|GPIO 16|          |SPI1 CE2
         |          |GPIO 26|37|┃◎ ◎┃|38|GPIO 20|          |SPI1 MOSI
         |          |Ground |39|┃◎ ◎┃|40|GPIO 21|          |SPI1 SCLK
         |          |       |  |┗━━━┛|  |       |          |
""".splitlines()[1:]]

NUM_COLS = len(PINOUT[0])
LEFT_COLS_END = int(NUM_COLS / 2)
RIGHT_COLS_START = LEFT_COLS_END + 1

LEFT_PINS = [[col.strip() for col in reversed(row[0:LEFT_COLS_END])] for row in PINOUT]
RIGHT_PINS = [[col.strip() for col in row[RIGHT_COLS_START:]] for row in PINOUT]
DIAGRAM = [row[LEFT_COLS_END] for row in PINOUT]

COLS = ["pins", "gpio", "i2c", "spi"]
DEBUG_COLS = ["consumer", "alt_func", "mode", "drive", "pull", "state"]
NUM_DEBUG_COLS = len(DEBUG_COLS)
NUM_GPIOS = 28

# String-constants taken from:
#   https://github.com/raspberrypi/utils/blob/master/pinctrl/gpiolib.c#L40
#   https://github.com/raspberrypi/utils/blob/master/pinctrl/pinctrl.c#L121
PINCTRL_REGEX = re.compile(r"^\s?(\d+): (a\d|\?\?|ip|op|gp|no) (dl|dh|\-\-|  ) (pn|pd|pu|\-\-) \| (lo|hi|\-\-) // (?:\w+/)?GPIO(\d+) = (\w+|\-)$")


# Add empty slots for the GPIO debug data
for n in range(len(LEFT_PINS)):
    LEFT_PINS[n] += [""] * NUM_DEBUG_COLS
    RIGHT_PINS[n] += [""] * NUM_DEBUG_COLS


def get_gpio_char_device():
    for num in (4, 0):
        try:
            gpiochip_path = f"/dev/gpiochip{num}"
            if stat.S_ISCHR(os.stat(gpiochip_path).st_mode):
                return gpiochip_path
        except FileNotFoundError:
            continue
    return None


def get_current_pin_states(chip):
    if chip is not None:
        if hasattr(gpiod, "chip"):
            gpio_user = [line.consumer for line in gpiod.line_iter(chip) if line.offset < NUM_GPIOS]
        elif hasattr(gpiod, "Chip"):
            gpio_user = [line.consumer() for line in gpiod.LineIter(chip) if line.offset() < NUM_GPIOS]
    else:
        gpio_user = [""] * NUM_GPIOS

    try:
        pinstate = subprocess.Popen(["pinctrl", "get", f"0-{NUM_GPIOS-1}"], stdout=subprocess.PIPE)
        states = list()
        for n, line in enumerate(pinstate.stdout.readlines()):
            m = PINCTRL_REGEX.match(line.decode("utf8"))
            if not m:
                raise Exception(f"Unexpected value in pinctrl output: {line}")
            gpio1 = int(m.group(1))
            mode = m.group(2)
            drive = m.group(3)
            pull = m.group(4)
            state = m.group(5)
            gpio2 = int(m.group(6))
            mode_name = m.group(7)
            assert gpio1 == gpio2 == n
            if mode == "no":
                mode = "--"
            if drive == "  ":
                drive = "--"
            if pull == "pn":
                pull = "--"
            alt_func = ""
            if re.match(r"a\d", mode):
                alt_func = mode_name
            consumer = gpio_user[n] or ""
            states.append([consumer, alt_func, mode, drive, pull, state])
    except FileNotFoundError:
        return [["--"] * NUM_DEBUG_COLS] * NUM_GPIOS

    return states


def gpio_add_line_state(gpio_states, row):
    gpio = row[1]
    if "GPIO" not in gpio:
        return
    gpio = int(gpio[5:])
    changed = row[-NUM_DEBUG_COLS:] != gpio_states[gpio]
    row[-NUM_DEBUG_COLS:] = gpio_states[gpio]
    return changed


def gpio_update_line_states(chip):
    gpio_states = get_current_pin_states(chip)
    changed = False

    for row in LEFT_PINS:
        changed = gpio_add_line_state(gpio_states, row) or changed

    for row in RIGHT_PINS:
        changed = gpio_add_line_state(gpio_states, row) or changed

    return changed


ROWS = len(LEFT_PINS)
COL_PIN_NUMS = 0
COL_GPIO = 1

THEME = {
    "gpio": "#859900",
    "pins": "#333333",
    "spi": "#d33682",
    "i2c": "#268bd2",
    "uart": "#6c71c4",
    "pwm": "#666666",
    "panel": "#ffffff on #000000",
    "panel_light": "#000000 on #fdf6e3",
    "diagram": "#555555",
    "consumer": "#989898",
    "alt_func": "#989898",
    "mode": "#989898",
    "drive": "#989898",
    "pull": "#989898",
    "state": "#989898",
    "power": "#dc322f",
    "ground": "#005b66",
    "hat": "#df8f8e",
    "highlight": "bold #dc322f on white",
    "highlight_row": "bold {fg} on #444444"
}


def usage(error=None):
    error = f"\n[red]Error: {error}[/]\n" if error else ""
    rich.print(f"""
[#859900]rpipins[/] [#2aa198]v{__version__}[/] - a beautiful GPIO pinout and pin function guide for the Raspberry Pi Computer
{error}
usage: rpipins [--...] [--all] or {{{",".join(COLS[2:])}}} [--find <text>]
       --pins          - show physical pin numbers
       --all or {{{",".join(COLS[2:])}}} - pick list of interfaces to show
       --hide-gpio     - hide GPIO pins
       --debug         - show GPIO status
       --light         - melt your eyeballs
       --find "<text>" - highlight pins matching <text>
                         supports regex if you"re feeling sassy!

eg:    rpipins i2c                    - show GPIO and I2C labels
       rpipins                        - basic GPIO pinout
       rpipins --all --find "I2C1"    - highlight any "I2C1" labels
       rpipins --all --find "SPI* SCLK" - highlight any SPI clock pins

web:   https://pinout.xyz
bugs:  https://github.com/pinout-xyz/rpipins
""")
    sys.exit(1 if error else 0)


def gpio_style(pin):
    if pin in (6, 9, 14, 20, 25, 30, 34, 39): return "ground"
    if pin in (1, 2, 4, 17): return "power"
    if pin in (27, 28): return "hat"
    return "gpio"


def styled(label, style, fg=None):
    style = THEME[style]
    style = style.format(fg=fg)
    return f"[{style}]{label}[/]"


def search(pin, highlight):
    if not highlight:
        return False
    highlight = re.compile(highlight, re.I)
    # Match search term against pin label
    return re.search(highlight, pin) is not None


def build_pins(pins, show_indexes, highlight=None):
    # Find all labels including the highlight word
    search_highlight = [search(pin, highlight) for pin in pins]
    # See if any non-visble labels match
    has_hidden_results = True in [index not in show_indexes and value
                                  for index, value in enumerate(search_highlight)]
    # Get the phyical pin for special case GPIO highlighting
    physical_pin_number = int(pins[COL_PIN_NUMS]) if pins[COL_PIN_NUMS] != "" else None
    # Iterate through the visible labels
    for i in show_indexes:
        label = pins[i]
        if search_highlight[i]:
            yield styled(label, "highlight")
        elif i == COL_GPIO:  # GPn / VSYS etc
            # Special case for styling power, ground, GPn, run, etc
            style = gpio_style(physical_pin_number)
            # Highlight for a non-visible search result
            if has_hidden_results:
                yield styled(label, "highlight_row", fg=THEME[style])
            else:
                yield styled(label, style)
        else:
            # Table column styles will catch the rest
            yield label


def build_row(row, show_indexes, highlight=None):
    for pin in build_pins(LEFT_PINS[row], show_indexes, highlight):
        yield pin + " "
    diagram = list(DIAGRAM[row])
    if LEFT_PINS[row][-1] == "hi":
        diagram[1] = styled(diagram[1], "power")
    if RIGHT_PINS[row][-1] == "hi":
        diagram[3] = styled(diagram[3], "power")
    yield " " + "".join(diagram)
    # We can"t reverse a generator
    for pin in reversed(list(build_pins(RIGHT_PINS[row], show_indexes, highlight))):
        yield " " + pin


def rpipins(opts):
    show_indexes = []
    grid = Table.grid(expand=True)

    for label in reversed(opts.show):
        grid.add_column(justify="left", style=THEME[label], no_wrap=True)
        show_indexes.append((COLS + DEBUG_COLS).index(label))

    if opts.show_gpio:
        grid.add_column(justify="right", style=THEME["gpio"], no_wrap=True)
        show_indexes.append(COL_GPIO)

    if opts.show_pins:
        grid.add_column(justify="right", style=THEME["pins"], no_wrap=True)
        show_indexes.append(COL_PIN_NUMS)

    grid.add_column(no_wrap=True, style=THEME["diagram"])

    if opts.show_pins:
        grid.add_column(justify="left", style=THEME["pins"], no_wrap=True)

    if opts.show_gpio:
        grid.add_column(justify="left", style=THEME["gpio"], no_wrap=True)

    for label in opts.show:
        grid.add_column(justify="left", style=THEME[label], no_wrap=True)

    for i in range(ROWS):
        grid.add_row(*build_row(i, show_indexes, highlight=opts.find))

    layout = Table.grid(expand=True)
    layout.add_row(grid)
    layout.add_row("@gadgetoid\nhttps://pinout.xyz")
    if opts.live:
        layout.add_row("Ctrl+C to exit!")

    return Panel(
        layout,
        title="Raspberry Pi Pinout",
        expand=False,
        style=THEME["panel_light"] if opts.light_mode else THEME["panel"])


class Options():
    def __init__(self, argv):
        self.name = argv.pop(0)

        if "--help" in argv:
            usage()

        if "--version" in argv:
            print(f"{__version__}")
            sys.exit(0)

        self.fps = 60

        self.all = "--all" in argv
        self.debug = "--debug" in argv
        self.show_pins = "--pins" in argv
        self.show_gpio = "--hide-gpio" not in argv
        self.light_mode = "--light" in argv
        self.live = "--live" in argv
        self.find = None

        if "--find" in argv:
            index = argv.index("--find") + 1
            if index >= len(argv) or argv[index].startswith("--"):
                usage("--find needs something to find.")
            self.find = argv.pop(index)

        # Assume any non -- args are labels
        self.show = [self.valid_label(arg) for arg in argv if not arg.startswith("--")]

        if self.show == [] and self.all:
            self.show = COLS[2:]
        elif self.all:
            usage("Please use either --all or a list of interfaces.")

        if self.debug:
            self.show += DEBUG_COLS

    def valid_label(self, label):
        if label not in COLS[2:]:
            usage(f"Invalid interface \"{label}\".")
        return label


def main():
    #rich.print(rpipins(Options(sys.argv)))
    options = Options(sys.argv)

    chip = None
    device = get_gpio_char_device()
    if device is not None:
        if hasattr(gpiod, "chip"):
            chip = gpiod.chip(device)
        elif hasattr(gpiod, "Chip"):
            chip = gpiod.Chip(device)

    gpio_update_line_states(chip)

    if options.live:
        with Live(rpipins(options), auto_refresh=True) as live:
            try:
                while True:
                    if gpio_update_line_states(chip):
                        live.update(rpipins(options), refresh=True)
                    time.sleep(1.0 / options.fps)
            except KeyboardInterrupt:
                options.live = False
                live.update(rpipins(options), refresh=True)
                return 0
    else:
        rich.print(rpipins(options))


if __name__ == "__main__":
    main()
