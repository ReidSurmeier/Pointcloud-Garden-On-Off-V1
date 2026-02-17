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
