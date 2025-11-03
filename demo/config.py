"""
Configuration Module

This module contains all configuration parameters for the H-UDP demo application,
including network settings, logging configuration, and game-relevant payload presets.
"""

import logging
import json

# ============================================================================
# NETWORK CONFIGURATION
# ============================================================================

# Default ports for sender and receiver
SENDER_PORT = 5000
RECEIVER_PORT = 6000

# Default host (localhost for testing)
HOST = 'localhost'

# Default protocol timeout parameters (in seconds)
SENDER_TIMEOUT = 0.200   # Retry interval for reliable packets
RECEIVER_TIMEOUT = 0.200  # Skip timeout for missing packets

# Default packet sending interval (in seconds)
PACKET_INTERVAL_SEC = 0.5  # Send a packet every 500ms

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

# Default log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL = logging.INFO

# Default log file paths
SENDER_LOG_FILE = 'sender.log'
RECEIVER_LOG_FILE = 'receiver.log'

# ============================================================================
# GAME-RELEVANT PAYLOAD PRESETS
# ============================================================================

# Preset payloads for different game scenarios
# Key: Display name, Value: Payload content (will be JSON-encoded)
PAYLOAD_PRESETS = {
    # Unreliable payload examples
    "Player Position Update": {
        "type": "position_update",
        "player_id": "player_123",
        "x": 150.5,
        "y": 200.3,
        "z": 10.0,
        "timestamp": 1234567890,
        "description": "Unreliable - High frequency, position updates can be dropped"
    },
    "Voice Chat Packet": {
        "type": "voice_data",
        "player_id": "player_123",
        "audio_chunk": "base64_encoded_audio_data_here",
        "sequence": 4521,
        "channel": "team",
        "timestamp": 1234567890,
        "description": "Unreliable - Low latency priority, some loss acceptable"
    },
    "Animation State": {
        "type": "animation",
        "player_id": "player_123",
        "animation": "running",
        "speed": 1.5,
        "timestamp": 1234567890,
        "description": "Unreliable - Visual only, can tolerate loss"
    },

    # Reliable payload examples
    "Player Health Update": {
        "type": "health_update",
        "player_id": "player_123",
        "health": 75,
        "max_health": 100,
        "timestamp": 1234567890,
        "description": "Reliable - Critical game state must be delivered"
    },
    "Chat Message": {
        "type": "chat",
        "player_id": "player_123",
        "player_name": "CoolGamer",
        "message": "Hello team!",
        "channel": "team",
        "timestamp": 1234567890,
        "description": "Reliable - Chat messages must be delivered"
    },
    "Game State Sync": {
        "type": "game_state",
        "round_number": 5,
        "time_remaining": 120,
        "players_alive": 8,
        "game_phase": "combat",
        "timestamp": 1234567890,
        "description": "Reliable - Must not be lost or game becomes desynced"
    },

    # Allows user to input custom payload
    "Custom": ""
}

# ============================================================================
# PAYLOAD RELIABILITY RULES
# ============================================================================

# Rules for determining if a payload type should be sent reliably
# These are suggestions - users can override in the UI
RELIABLE_TYPES = {
    "health_update",
    "chat",
    "game_state",
}

UNRELIABLE_TYPES = {
    "position_update",
    "voice_data",
    "animation",
}


def get_suggested_reliability(payload_text):
    """
    Analyzes a payload and suggests whether it should be sent reliably.

    Args:
        payload_text (str): The payload content (JSON string or plain text)

    Returns:
        bool: True if should be sent reliably, False for unreliable
    """
    try:
        # Try to parse as JSON
        payload_data = json.loads(payload_text)
        payload_type = payload_data.get("type", "")

        if payload_type in RELIABLE_TYPES:
            return True
        elif payload_type in UNRELIABLE_TYPES:
            return False
        else:
            # Default to reliable if unknown
            return True
    except (json.JSONDecodeError, AttributeError):
        # If not JSON or error, default to reliable for safety
        return True

# ============================================================================
# UI CONFIGURATION
# ============================================================================


# Window dimensions
WINDOW_WIDTH = 900
WINDOW_HEIGHT = 1000

# Color scheme for log levels
LOG_COLORS = {
    "INFO": "white",
    "WARNING": "orange",
    "ERROR": "red",
    "DEBUG": "cyan",
}
