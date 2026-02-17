#!/usr/bin/env python3
"""
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

Author:  Reid Surmeier
Client:  Clement Valla
Date:    2026 Feb 16th

Matrix Controller Daemon
Controls LED matrix PSU via relay and manages matrix-led.service
"""

import argparse
import logging
import signal
import sys
import threading
import time
import yaml
from pathlib import Path
from typing import Optional

from .state_machine import StateMachine, State
from .gpio import GPIOController
from .led_service import LEDService
from .ups import UPSController


# Configure logging to journald (stdout)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class MatrixController:
    """Main controller daemon."""
    
    def __init__(self, config_path: str, dry_run: bool = False):
        """
        Initialize matrix controller.
        
        Args:
            config_path: Path to YAML configuration file
            dry_run: If True, log actions instead of executing
        """
        self.dry_run = dry_run
        self.running = True
        self._lock = threading.Lock()  # Protects state transitions from concurrent callbacks
        self.config = self._load_config(config_path)
        
        # Initialize components
        self.state_machine = StateMachine()
        self.gpio = None
        self.led_service = None
        self.ups = None
        
        self._initialize_components()
        
        # Register signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        logger.info("Matrix controller initialized")
    
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Apply safe defaults
            config.setdefault('buttons', {})
            config['buttons'].setdefault('start_pin', 18)
            config['buttons'].setdefault('stop_pin', 19)
            config['buttons'].setdefault('debounce_ms', 80)
            
            config.setdefault('relay', {})
            config['relay'].setdefault('pin', 20)
            config['relay'].setdefault('active_high', True)
            
            config.setdefault('ups', {})
            config['ups'].setdefault('mode', 'disabled')
            config['ups'].setdefault('mains_lost_pin', 21)
            config['ups'].setdefault('edge', 'rising')
            
            config.setdefault('led_service', {})
            config['led_service'].setdefault('name', 'matrix-led.service')
            
            config.setdefault('logging', {})
            config['logging'].setdefault('level', 'INFO')
            
            # Set logging level
            log_level = getattr(logging, config['logging']['level'].upper(), logging.INFO)
            logging.getLogger().setLevel(log_level)
            
            logger.info(f"Configuration loaded from {config_path}")
            return config
            
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML config: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            raise
    
    def _initialize_components(self) -> None:
        """Initialize GPIO, LED service, and UPS components."""
        try:
            # Initialize GPIO controller
            self.gpio = GPIOController(
                start_pin=self.config['buttons']['start_pin'],
                stop_pin=self.config['buttons']['stop_pin'],
                relay_pin=self.config['relay']['pin'],
                relay_active_high=self.config['relay']['active_high'],
                debounce_ms=self.config['buttons']['debounce_ms'] / 1000.0
            )
            
            # Initialize LED service
            self.led_service = LEDService(
                service_name=self.config['led_service']['name'],
                dry_run=self.dry_run
            )
            
            # Initialize UPS controller
            ups_mode = self.config['ups']['mode']
            ups_pin = self.config['ups'].get('mains_lost_pin') if ups_mode == 'gpio' else None
            ups_edge = self.config['ups'].get('edge', 'rising')
            
            self.ups = UPSController(
                mode=ups_mode,
                pin=ups_pin,
                edge=ups_edge,
                callback=self._on_ups_power_loss,
                dry_run=self.dry_run
            )
            
            # Register button callbacks
            self.gpio.register_start_callback(self._on_start_button)
            self.gpio.register_stop_callback(self._on_stop_button)
            
            logger.info("All components initialized")
            
        except Exception as e:
            logger.error(f"Error initializing components: {e}")
            raise
    
    def startup(self) -> None:
        """
        Perform startup sequence:
        1. Force relay OFF
        2. Stop LED service
        3. Ensure state is IDLE
        """
        logger.info("Starting up matrix controller...")
        
        # Force relay OFF
        self.gpio.set_relay(False)
        logger.info("Relay forced OFF")
        
        # Stop LED service (idempotent)
        self.led_service.stop()
        logger.info("LED service stopped (if it was running)")
        
        # Ensure state is IDLE
        if not self.state_machine.is_idle():
            self.state_machine.transition_to_idle()
        
        logger.info("Startup sequence complete - controller in IDLE state")
    
    def _on_start_button(self) -> None:
        """Handle start button press."""
        logger.info("Start button pressed")

        with self._lock:
            if not self.state_machine.is_idle():
                logger.warning(f"Start button ignored - not in IDLE state (current: {self.state_machine.get_state().name})")
                return

            # Transition to RUNNING
            if not self.state_machine.transition_to_running():
                logger.error("Failed to transition to RUNNING state")
                return

            # Turn relay ON
            self.gpio.set_relay(True)

            # Start LED service
            if not self.led_service.start():
                logger.error("Failed to start LED service - reverting to IDLE")
                self.gpio.set_relay(False)
                self.state_machine.transition_to_idle()
                return

            logger.info("System started: relay ON, LED service running")

    def _on_stop_button(self) -> None:
        """Handle stop button press."""
        logger.info("Stop button pressed")

        with self._lock:
            if not self.state_machine.is_running():
                logger.info("Stop button ignored - not in RUNNING state (no-op)")
                return

            # Stop LED service first
            self.led_service.stop()

            # Turn relay OFF
            self.gpio.set_relay(False)

            # Transition to IDLE
            self.state_machine.transition_to_idle()

            logger.info("System stopped: relay OFF, LED service stopped")

    def _on_ups_power_loss(self) -> None:
        """Handle UPS power-loss event."""
        logger.critical("UPS power-loss detected!")

        with self._lock:
            # Transition to EMERGENCY_SHUTDOWN
            self.state_machine.transition_to_emergency_shutdown()

            # Stop LED service
            self.led_service.stop()

            # Ensure relay is OFF
            self.gpio.set_relay(False)

        # Execute shutdown outside lock — this doesn't return
        logger.critical("Executing system shutdown for safe halt...")
        if not self.dry_run:
            import subprocess
            try:
                subprocess.run(["shutdown", "-h", "now"], check=True, timeout=5)
            except Exception as e:
                logger.error(f"Failed to execute shutdown: {e}")
        else:
            logger.info("[DRY RUN] Would execute: shutdown -h now")
    
    def _signal_handler(self, signum, frame) -> None:
        """Handle termination signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    def run(self) -> None:
        """Main daemon loop."""
        logger.info("Matrix controller daemon started")
        
        # Perform startup sequence
        self.startup()
        
        # Main loop - event-driven with watchdog tick
        watchdog_interval = 5.0  # seconds
        last_watchdog = time.time()
        
        while self.running:
            try:
                # Watchdog tick - verify state consistency
                now = time.time()
                if now - last_watchdog >= watchdog_interval:
                    self._watchdog_tick()
                    last_watchdog = now
                
                # Small sleep to prevent CPU spinning
                time.sleep(0.1)
                
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                time.sleep(1)  # Prevent tight error loop
        
        # Cleanup
        self.shutdown()
    
    def _watchdog_tick(self) -> None:
        """Periodic watchdog check for state consistency."""
        with self._lock:
            current_state = self.state_machine.get_state()

            # In RUNNING state, verify service is actually running
            if current_state == State.RUNNING:
                if not self.led_service.is_active():
                    logger.warning("State is RUNNING but LED service is not active - correcting state")
                    self.gpio.set_relay(False)
                    self.state_machine.transition_to_idle()

            # In IDLE state, verify service is stopped and relay is OFF
            elif current_state == State.IDLE:
                if self.led_service.is_active():
                    logger.warning("State is IDLE but LED service is active - stopping service")
                    self.led_service.stop()

                if self.gpio.get_relay():
                    logger.warning("State is IDLE but relay is ON - turning relay OFF")
                    self.gpio.set_relay(False)

            logger.debug(f"Watchdog tick: state={current_state.name}, "
                        f"relay={'ON' if self.gpio.get_relay() else 'OFF'}, "
                        f"service_active={self.led_service.is_active()}")
    
    def shutdown(self) -> None:
        """Cleanup on daemon shutdown."""
        logger.info("Shutting down matrix controller...")
        
        # Stop LED service
        if self.led_service:
            self.led_service.stop()
        
        # Turn relay OFF
        if self.gpio:
            self.gpio.set_relay(False)
        
        # Close GPIO resources
        if self.gpio:
            self.gpio.close()
        
        # Close UPS monitor
        if self.ups:
            self.ups.close()
        
        logger.info("Matrix controller shutdown complete")


def main():
    """Entry point."""
    parser = argparse.ArgumentParser(description="Matrix Controller Daemon")
    parser.add_argument(
        '--config',
        type=str,
        default='/etc/matrix-controller/controller.yaml',
        help='Path to configuration file (default: /etc/matrix-controller/controller.yaml)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry-run mode: log actions instead of executing'
    )
    
    args = parser.parse_args()
    
    # Check if config file exists
    if not Path(args.config).exists():
        logger.error(f"Configuration file not found: {args.config}")
        logger.error("Please create the configuration file or specify a different path with --config")
        sys.exit(1)
    
    try:
        controller = MatrixController(args.config, dry_run=args.dry_run)
        controller.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
