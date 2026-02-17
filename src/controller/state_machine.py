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
