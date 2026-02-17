"""
 ____  _____ ___ ____    ____  _   _ ____  __  __ _____ ___ _____ ____
|  _ \\| ____|_ _|  _ \\  / ___|| | | |  _ \\|  \\/  | ____|_ _| ____|  _ \\
| |_) |  _|  | || | | | \\___ \\| | | | |_) | |\\/| |  _|  | ||  _| | |_) |
|  _ <| |___ | || |_| |  ___) | |_| |  _ <| |  | | |___ | || |___|  _ <
|_| \\_\\_____|___|____/  |____/ \\___/|_| \\_\\_|  |_|_____|___|_____|_| \\_\\

Author:  Reid Surmeier
Client:  Clement Valla
Date:    2026 Feb 16th

Systemd service control wrapper for matrix-led.service.
"""

import logging
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)


class LEDService:
    """Manages systemd service for LED matrix rendering."""
    
    def __init__(self, service_name: str = "matrix-led.service", dry_run: bool = False):
        """
        Initialize LED service controller.
        
        Args:
            service_name: Name of systemd service
            dry_run: If True, log actions instead of executing
        """
        self.service_name = service_name
        self.dry_run = dry_run
        logger.info(f"LED service controller initialized: {service_name} (dry_run={dry_run})")
    
    def start(self) -> bool:
        """
        Start the LED service.
        
        Returns:
            True if successful, False otherwise
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would start service: {self.service_name}")
            return True
        
        try:
            result = subprocess.run(
                ["systemctl", "start", self.service_name],
                check=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            logger.info(f"Service {self.service_name} started successfully")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to start service {self.service_name}: {e.stderr}")
            return False
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout starting service {self.service_name}")
            return False
    
    def stop(self) -> bool:
        """
        Stop the LED service.
        
        Returns:
            True if successful, False otherwise
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would stop service: {self.service_name}")
            return True
        
        try:
            result = subprocess.run(
                ["systemctl", "stop", self.service_name],
                check=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            logger.info(f"Service {self.service_name} stopped successfully")
            return True
        except subprocess.CalledProcessError as e:
            # Service might not be running or not loaded - that's OK for stop
            if "not loaded" in e.stderr.lower() or "not found" in e.stderr.lower():
                logger.warning(f"Service {self.service_name} not found or not loaded")
                return True  # Not loaded = already stopped, treat as success
            else:
                logger.error(f"Failed to stop service {self.service_name}: {e.stderr}")
            return False
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout stopping service {self.service_name}")
            return False
    
    def is_active(self) -> bool:
        """
        Check if service is currently active.
        
        Returns:
            True if service is active, False otherwise
        """
        if self.dry_run:
            # In dry-run, assume service state is tracked elsewhere
            return False
        
        try:
            result = subprocess.run(
                ["systemctl", "is-active", self.service_name],
                check=False,
                capture_output=True,
                text=True,
                timeout=5
            )
            is_active = (result.returncode == 0 and result.stdout.strip() == "active")
            logger.debug(f"Service {self.service_name} is_active={is_active}")
            return is_active
        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout checking service {self.service_name} status")
            return False
        except Exception as e:
            logger.error(f"Error checking service status: {e}")
            return False
