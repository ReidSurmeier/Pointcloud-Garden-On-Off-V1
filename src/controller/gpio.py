"""
 ____  _____ ___ ____    ____  _   _ ____  __  __ _____ ___ _____ ____
|  _ \\| ____|_ _|  _ \\  / ___|| | | |  _ \\|  \\/  | ____|_ _| ____|  _ \\
| |_) |  _|  | || | | | \\___ \\| | | | |_) | |\\/| |  _|  | ||  _| | |_) |
|  _ <| |___ | || |_| |  ___) | |_| |  _ <| |  | | |___ | || |___|  _ <
|_| \\_\\_____|___|____/  |____/ \\___/|_| \\_\\_|  |_|_____|___|_____|_| \\_\\

Author:  Reid Surmeier
Client:  Clement Valla
Date:    2026 Feb 16th

GPIO abstraction layer for buttons and relay control.
Uses gpiozero with lgpio backend for Raspberry Pi 5 compatibility.
"""

import logging
from typing import Optional, Callable
from gpiozero import Button, OutputDevice
from gpiozero.pins.lgpio import LGPIOFactory

logger = logging.getLogger(__name__)

# Shared factory — one lgpio handle for the entire process
_shared_factory: Optional[LGPIOFactory] = None


def get_factory() -> LGPIOFactory:
    """Return a shared LGPIOFactory instance (one handle to /dev/gpiochip4)."""
    global _shared_factory
    if _shared_factory is None:
        _shared_factory = LGPIOFactory()
    return _shared_factory


class GPIOController:
    """Manages GPIO pins for buttons and relay using gpiozero with lgpio backend."""

    def __init__(self, start_pin: int, stop_pin: int, relay_pin: int,
                 relay_active_high: bool = True, debounce_ms: float = 0.08):
        """
        Initialize GPIO controller.

        Args:
            start_pin: GPIO pin number for start button
            stop_pin: GPIO pin number for stop button
            relay_pin: GPIO pin number for relay control
            relay_active_high: True if HIGH = relay ON, False if LOW = relay ON
            debounce_ms: Debounce time in seconds (default 80ms = 0.08s)
        """
        self.factory = get_factory()
        self.relay_active_high = relay_active_high
        
        # Initialize buttons with pull-up (pressed = connect to GND)
        # gpiozero Button defaults to pull_up=True, active_state=False (LOW when pressed)
        self.start_button = Button(
            start_pin, 
            pin_factory=self.factory,
            pull_up=True,
            bounce_time=debounce_ms
        )
        
        self.stop_button = Button(
            stop_pin,
            pin_factory=self.factory,
            pull_up=True,
            bounce_time=debounce_ms
        )
        
        # Initialize relay output
        # OutputDevice defaults to active_high=True
        self.relay = OutputDevice(
            relay_pin,
            pin_factory=self.factory,
            active_high=relay_active_high,
            initial_value=False  # Start with relay OFF
        )
        
        logger.info(f"GPIO initialized: start={start_pin}, stop={stop_pin}, "
                   f"relay={relay_pin} (active_high={relay_active_high})")
    
    def set_relay(self, state: bool) -> None:
        """
        Set relay state.
        
        Args:
            state: True to turn relay ON, False to turn relay OFF
        """
        self.relay.value = state
        logger.info(f"Relay set to {'ON' if state else 'OFF'}")
    
    def get_relay(self) -> bool:
        """Get current relay state."""
        return self.relay.value
    
    def register_start_callback(self, callback: Callable[[], None]) -> None:
        """Register callback for start button press."""
        self.start_button.when_pressed = callback
        logger.debug("Start button callback registered")
    
    def register_stop_callback(self, callback: Callable[[], None]) -> None:
        """Register callback for stop button press."""
        self.stop_button.when_pressed = callback
        logger.debug("Stop button callback registered")
    
    def close(self) -> None:
        """Clean up GPIO resources."""
        if hasattr(self, 'relay'):
            self.relay.close()
        if hasattr(self, 'start_button'):
            self.start_button.close()
        if hasattr(self, 'stop_button'):
            self.stop_button.close()
        logger.debug("GPIO resources closed")


class UPSMonitor:
    """Monitors UPS power-loss signal via GPIO."""
    
    def __init__(self, pin: int, edge: str = "rising", 
                 callback: Optional[Callable[[], None]] = None):
        """
        Initialize UPS monitor.
        
        Args:
            pin: GPIO pin number for UPS mains-lost signal
            edge: "rising" or "falling" edge to trigger shutdown
            callback: Function to call when power loss detected
        """
        self.factory = get_factory()
        self.edge = edge
        self.callback = callback
        
        # Create button-like device to monitor GPIO
        # For rising edge (mains lost = HIGH), we want active_state=True
        # For falling edge (mains lost = LOW), we want active_state=False
        active_state = (edge == "rising")
        
        self.ups_signal = Button(
            pin,
            pin_factory=self.factory,
            pull_up=(edge == "falling"),  # Pull-up if we're watching for falling edge
            active_state=active_state,
            bounce_time=0.3  # 300ms debounce to prevent false UPS triggers from noise
        )
        
        if callback:
            self.ups_signal.when_pressed = callback
        
        logger.info(f"UPS monitor initialized: pin={pin}, edge={edge}")
    
    def close(self) -> None:
        """Clean up GPIO resources."""
        if hasattr(self, 'ups_signal'):
            self.ups_signal.close()
        logger.debug("UPS monitor closed")
