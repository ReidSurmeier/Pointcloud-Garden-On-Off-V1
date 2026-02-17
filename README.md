
**Author:** Reid Surmeier
**Client:** Clement Valla
**Date:** 2026 Feb 16th

---

# Matrix Controller

Raspberry Pi 5 daemon that runs an LED matrix. Handles PSU power switching through a relay, starts and stops the rendering service, and shuts down safely when the UPS loses mains power.

Two physical buttons control everything. Start turns the matrix on. Stop turns it off. If someone pulls the wall plug, the UPS keeps the Pi alive long enough to halt cleanly.

## What it does

- Start/stop buttons control the LED matrix PSU and rendering service
- UPS monitors mains power and triggers a safe shutdown if power drops
- State machine keeps track of IDLE, RUNNING, and EMERGENCY_SHUTDOWN
- On boot the relay is always forced OFF and the service is stopped
- Pressing buttons multiple times won't break anything
- Dry-run mode lets you test without touching hardware

## Hardware

| Part | Purpose |
|------|---------|
| Raspberry Pi 5 | Runs the daemon |
| LED Matrix PSU (MEAN WELL LRS-150F) | Powers the LED matrix |
| 2x push buttons (APIELE) | Start and stop |
| UPS HAT (Geekworm X1201) | Battery backup and power-loss detection |
| GPIO Screw Terminal Block Breakout | Clean wiring to Pi header |
| Relay/SSR (LCLCTC Din Rail) | Switches PSU power on and off |
| Blue Sea Systems 5025 fuse block | PSU fuse protection |
| Circuit breaker | Overcurrent protection |

## Wiring

### Buttons

Start button goes between GPIO 18 and GND. Stop button goes between GPIO 19 and GND. Internal pull-ups are enabled so pressing a button pulls the pin low.

### Relay

Relay control wire goes to GPIO 20. Default is active-high, meaning HIGH turns the relay on and LOW turns it off. This is configurable in the YAML if your relay works the other way around.

### UPS HAT

The Geekworm X1201 provides a signal when mains power is lost. Wire that signal to GPIO 21. Default config expects the signal to go HIGH when power is lost (rising edge). Check your specific UPS HAT documentation to confirm which pin it uses and whether the signal is active-high or active-low.

### Power distribution

Terminal blocks and a circuit breaker sit between the MEAN WELL PSU and the LED matrix. The Blue Sea fuse block protects individual runs. The relay sits between the PSU output and the matrix so the daemon can cut power cleanly.

## Getting started

Clone or copy this repo to your Pi 5 and run the installer:

```bash
sudo bash scripts/install.sh
```

This installs Python dependencies, copies the config to `/etc/matrix-controller/controller.yaml`, installs the Python package, and enables the systemd service.

Edit the config to match your wiring:

```bash
sudo nano /etc/matrix-controller/controller.yaml
```

Test with dry-run first (no GPIO, no relay, just logs):

```bash
sudo python3 -m controller.main --config /etc/matrix-controller/controller.yaml --dry-run
```

Start the service for real:

```bash
sudo systemctl start matrix-controller
```

Watch the logs:

```bash
journalctl -u matrix-controller -f
```

## Config

The config lives at `/etc/matrix-controller/controller.yaml`:

```yaml
buttons:
  start_pin: 18
  stop_pin: 19
  debounce_ms: 80

relay:
  pin: 20
  active_high: true

ups:
  mode: "gpio"        # set to "disabled" if no UPS
  mains_lost_pin: 21
  edge: "rising"

led_service:
  name: "matrix-led.service"

logging:
  level: "INFO"
```

Pin numbers are BCM GPIO numbers, not physical pin numbers. Debounce is in milliseconds.

## How it works

### Boot

When the Pi boots, the daemon starts automatically and:

1. Forces relay OFF
2. Stops `matrix-led.service` if it was running
3. Sits in IDLE waiting for a button press

The matrix is always off after a reboot until someone presses start.

### Start button

Only works when idle. Turns the relay on, starts the LED rendering service, moves to RUNNING. If you press it while already running, nothing happens.

### Stop button

Only works when running. Stops the LED service, turns the relay off, goes back to IDLE. If you press it while already idle, nothing happens.

### UPS power loss

Works from any state. If the UPS signals that mains power is gone:

1. Stops the LED service
2. Turns relay off
3. Runs `shutdown -h now`

This is the only thing that actually shuts down the Pi. The stop button just turns off the matrix.

### Watchdog

Every 5 seconds the daemon checks that reality matches the state machine. If the state says RUNNING but the service crashed, it turns the relay off and goes back to IDLE. If the state says IDLE but the relay is somehow on, it forces it off.

## Testing on hardware

### Test the buttons

```bash
python3 -c "
from gpiozero import Button
from gpiozero.pins.lgpio import LGPIOFactory
b = Button(18, pin_factory=LGPIOFactory(), pull_up=True)
print('Press start button...')
b.wait_for_press()
print('Got it')
"
```

### Test the relay

```bash
python3 -c "
from gpiozero import OutputDevice
from gpiozero.pins.lgpio import LGPIOFactory
r = OutputDevice(20, pin_factory=LGPIOFactory(), active_high=True)
r.on()
input('Relay should be ON. Press enter to turn off...')
r.off()
print('Done')
"
```

### Test the full flow

1. Start the service: `sudo systemctl start matrix-controller`
2. Press start button, check relay is on and `matrix-led.service` is running
3. Press stop button, check relay is off and service stopped
4. Reboot, confirm everything comes up in IDLE with relay off

### Test UPS shutdown

Unplug the wall power with the system running. The UPS should keep the Pi alive while it halts. Check the journal after powering back on:

```bash
journalctl -u matrix-controller -b -1
```

You should see the "UPS power-loss detected" log followed by the shutdown sequence.

## Troubleshooting

**Service won't start** -- check that the config file exists at `/etc/matrix-controller/controller.yaml` and look at the logs with `journalctl -u matrix-controller -n 50`. Make sure no other process is using the same GPIO pins.

**Buttons don't do anything** -- double check that the button wires go between the correct GPIO pin and GND. Use the button test script above to verify the hardware works before blaming the daemon.

**Relay clicks but matrix doesn't turn on** -- check the wiring between the relay output and the PSU. Verify `active_high` in the config matches your relay module. Some relays are active-low.

**UPS doesn't trigger shutdown** -- make sure `ups.mode` is set to `"gpio"` and not `"disabled"`. Verify the pin number matches your UPS HAT. Check whether your HAT signal is rising or falling edge on power loss.

**Service keeps restarting** -- the systemd unit is set to `Restart=always` with a 10 second delay. If it crashes on startup (bad config, GPIO conflict), it will keep retrying. Fix the root cause in the logs.

## Project layout

```
matrix-controller/
  src/controller/
    __init__.py          -- package init
    main.py              -- daemon entrypoint and event loop
    state_machine.py     -- IDLE / RUNNING / EMERGENCY_SHUTDOWN states
    gpio.py              -- button and relay GPIO control (lgpio backend)
    led_service.py       -- systemctl wrapper for matrix-led.service
    ups.py               -- UPS power-loss monitoring
  config/
    controller.yaml      -- default config
  systemd/
    matrix-controller.service  -- systemd unit file
  scripts/
    install.sh           -- installer
  README.md
```

## Dependencies

- Python 3.11+
- gpiozero with lgpio backend (Pi 5 requires lgpio, not RPi.GPIO)
- pyyaml
- python3-lgpio (system package, should already be on Raspberry Pi OS Bookworm)

## Safety

The controller always turns the relay off before doing anything else during shutdown or error recovery. On boot the relay is forced off. The watchdog catches state mismatches every 5 seconds.

Test with dry-run mode before connecting live hardware. Verify your UPS wiring carefully since a wrong edge setting could trigger a shutdown when power is fine. Use the fuse block and circuit breaker to protect the PSU and matrix from overcurrent.

---

```
      RSRSRSRSba   RSRSRSRSRS8  RS  RSRSRSRSba,
      RS      "8b  RS           RS  RS      `"8b
      RS      ,8P  RS           RS  RS        `8b
      RSaaaaaa8P'  RSaaaaa      RS  RS         RS
      RS""""RS'    RS"""""      RS  RS         RS
      RS    `8b    RS           RS  RS         8P
      RS     `8b   RS           RS  RS      .a8P
      RS      `8b  RSRSRSRSRS8  RS  RSRSRSRSY"'


       adRSRS8ba   RS        RS  RSRSRSRSba   RSb           dRS  RSRSRSRSRS8  RS  RSRSRSRSRS8  RSRSRSRSba
      d8"     "8b  RS        RS  RS      "8b  RS8b         dRS8  RS           RS  RS           RS      "8b
      Y8,          RS        RS  RS      ,8P  RS`8b       d8'RS  RS           RS  RS           RS      ,8P
      `Y8aaaaa,    RS        RS  RSaaaaaa8P'  RS `8b     d8' RS  RSaaaaa      RS  RSaaaaa      RSaaaaaa8P'
        `"""""8b,  RS        RS  RS""""RS'    RS  `8b   d8'  RS  RS"""""      RS  RS"""""      RS""""RS'
              `8b  RS        RS  RS    `8b    RS   `8b d8'   RS  RS           RS  RS           RS    `8b
      Y8a     a8P  Y8a.    .a8P  RS     `8b   RS    `RS8'    RS  RS           RS  RS           RS     `8b
       "YRSRS8P"    `"YRSRSY"'   RS      `8b  RS     `8'     RS  RSRSRSRSRS8  RS  RSRSRSRSRS8  RS      `8b


       I8,        8        ,8I  RSRSRSRSRSRS  RSRSRSRSRS8
       `8b       d8b       d8'       RS       RS
        "8,     ,8"8,     ,8"        RS       RS
         Y8     8P Y8     8P         RS       RSaaaaa
         `8b   d8' `8b   d8'         RS       RS"""""
          `8a a8'   `8a a8'          RS       RS
      RS8  `8a8'     `8a8'           RS       RS
      RS8   `8'       `8'            RS       RS
```

(graphic design and programming by Reid Surmeier)
