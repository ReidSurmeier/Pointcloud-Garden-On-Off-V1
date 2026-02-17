"""
 ____  _____ ___ ____    ____  _   _ ____  __  __ _____ ___ _____ ____
|  _ \\| ____|_ _|  _ \\  / ___|| | | |  _ \\|  \\/  | ____|_ _| ____|  _ \\
| |_) |  _|  | || | | | \\___ \\| | | | |_) | |\\/| |  _|  | ||  _| | |_) |
|  _ <| |___ | || |_| |  ___) | |_| |  _ <| |  | | |___ | || |___|  _ <
|_| \\_\\_____|___|____/  |____/ \\___/|_| \\_\\_|  |_|_____|___|_____|_| \\_\\

Author:  Reid Surmeier
Client:  Clement Valla
Date:    2026 Feb 16th

UPS monitoring module for power-loss detection.
"""

import logging
from typing import Optional, Callable
from .gpio import UPSMonitor

logger = logging.getLogger(__name__)


class UPSController:
    """Manages UPS power-loss monitoring."""
    
    def __init__(self, mode: str = "disabled", pin: Optional[int] = None,
                 edge: str = "rising", callback: Optional[Callable[[], None]] = None,
                 dry_run: bool = False):
        """
        Initialize UPS controller.
        
        Args:
            mode: "disabled" or "gpio"
            pin: GPIO pin number (required if mode="gpio")
            edge: "rising" or "falling" edge to trigger shutdown
            callback: Function to call when power loss detected
            dry_run: If True, log actions instead of executing
        """
        self.mode = mode
        self.dry_run = dry_run
        self.monitor: Optional[UPSMonitor] = None
        
        if mode == "gpio":
            if pin is None:
                raise ValueError("UPS pin must be specified when mode='gpio'")
            
            self.monitor = UPSMonitor(pin, edge, callback)
            logger.info(f"UPS monitoring enabled: pin={pin}, edge={edge}")
        elif mode == "disabled":
            logger.info("UPS monitoring disabled")
        else:
            raise ValueError(f"Invalid UPS mode: {mode}. Must be 'disabled' or 'gpio'")
    
    def close(self) -> None:
        """Clean up UPS monitoring resources."""
        if self.monitor:
            self.monitor.close()
        logger.debug("UPS controller closed")
