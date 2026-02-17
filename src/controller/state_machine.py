"""
 ____  _____ ___ ____    ____  _   _ ____  __  __ _____ ___ _____ ____
|  _ \\| ____|_ _|  _ \\  / ___|| | | |  _ \\|  \\/  | ____|_ _| ____|  _ \\
| |_) |  _|  | || | | | \\___ \\| | | | |_) | |\\/| |  _|  | ||  _| | |_) |
|  _ <| |___ | || |_| |  ___) | |_| |  _ <| |  | | |___ | || |___|  _ <
|_| \\_\\_____|___|____/  |____/ \\___/|_| \\_\\_|  |_|_____|___|_____|_| \\_\\

Author:  Reid Surmeier
Client:  Clement Valla
Date:    2026 Feb 16th

State machine for matrix controller.
States: IDLE, RUNNING, EMERGENCY_SHUTDOWN
"""

import logging
from enum import Enum, auto

logger = logging.getLogger(__name__)


class State(Enum):
    """Controller states."""
    IDLE = auto()
    RUNNING = auto()
    EMERGENCY_SHUTDOWN = auto()


class StateMachine:
    """Manages controller state transitions."""
    
    def __init__(self):
        """Initialize state machine in IDLE state."""
        self.state = State.IDLE
        logger.info(f"State machine initialized: state={self.state.name}")
    
    def transition_to_idle(self) -> bool:
        """
        Transition to IDLE state.
        
        Returns:
            True if transition successful, False if invalid
        """
        if self.state == State.EMERGENCY_SHUTDOWN:
            logger.warning("Cannot transition from EMERGENCY_SHUTDOWN to IDLE")
            return False
        
        old_state = self.state
        self.state = State.IDLE
        logger.info(f"State transition: {old_state.name} -> {self.state.name}")
        return True
    
    def transition_to_running(self) -> bool:
        """
        Transition to RUNNING state.
        
        Returns:
            True if transition successful, False if invalid
        """
        if self.state != State.IDLE:
            logger.warning(f"Cannot transition to RUNNING from {self.state.name}")
            return False
        
        old_state = self.state
        self.state = State.RUNNING
        logger.info(f"State transition: {old_state.name} -> {self.state.name}")
        return True
    
    def transition_to_emergency_shutdown(self) -> bool:
        """
        Transition to EMERGENCY_SHUTDOWN state.
        Can be called from any state.
        
        Returns:
            True if transition successful
        """
        old_state = self.state
        self.state = State.EMERGENCY_SHUTDOWN
        logger.warning(f"State transition: {old_state.name} -> {self.state.name}")
        return True
    
    def is_idle(self) -> bool:
        """Check if currently in IDLE state."""
        return self.state == State.IDLE
    
    def is_running(self) -> bool:
        """Check if currently in RUNNING state."""
        return self.state == State.RUNNING
    
    def is_emergency_shutdown(self) -> bool:
        """Check if currently in EMERGENCY_SHUTDOWN state."""
        return self.state == State.EMERGENCY_SHUTDOWN
    
    def get_state(self) -> State:
        """Get current state."""
        return self.state
