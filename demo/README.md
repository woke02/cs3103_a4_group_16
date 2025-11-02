# H-UDP Demo Applications

This directory contains demo applications for testing the H-UDP protocol.

## Quick Start

### GUI Demo (Recommended)

The GUI provides full control and visualization of the protocol:

```bash
# Terminal 1 - Receiver
python3 demo/app.py

# Terminal 2 - Sender
python3 demo/app.py
```

**Features:**

- Role selection (sender/receiver)
- Configurable network parameters (ports, remote host, timeouts)
- Different game-relevant payload presets
- Auto-reliability based on payload type
- Real-time statistics and logging
- Log export functionality

### Command-Line Demo

For quick testing without GUI:

```bash
# Terminal 1 - Receiver
python3 demo/example_usage.py receiver

# Terminal 2 - Sender
python3 demo/example_usage.py sender
```

This sends 3 sample packets and displays the results.

## Files

- **`app.py`** - Full-featured GUI application with tkinter
- **`example_usage.py`** - Simple command-line demo
- **`config.py`** - Default configuration and payload presets

## Network Configuration

The GUI now allows configuring network parameters directly during initialization:

### Configurable Parameters

- **Local Port**: Port to bind on this machine (default: 5000 for sender, 6000 for receiver)
- **Remote Host**: Target hostname/IP for sender (default: localhost)
- **Remote Port**: Target port for sender (default: 6000)
- **Sender Timeout**: Retry interval for reliable packets in milliseconds (default: 200ms)
- **Receiver Timeout**: Skip timeout for missing packets in milliseconds (default: 450ms)
- **Log Level**: Logging verbosity level - DEBUG, INFO, WARNING, or ERROR (default: INFO)

**Important**: All configuration fields are **locked after initialization** to ensure consistency during the session.

### Default Configuration (in `config.py`)

- Network ports (default: 5000 sender, 6000 receiver)
- Protocol timeouts (sender: 200ms, receiver: 450ms)
- Packet sending interval (default: 500ms)
- Payload presets

## Troubleshooting

### Port Already in Use

```bash
lsof -ti:5000 | xargs kill -9
lsof -ti:6000 | xargs kill -9
```

### Import Errors

Make sure you're running from the project root directory:

```bash
cd /path/to/cs3103_a4_group_16
python3 demo/app.py
```

### Tkinter Not Available

```bash
# macOS (usually included)
brew install python-tk

# Ubuntu/Debian
sudo apt-get install python3-tk
```

## Usage Tips

1. **Always start the receiver first** before starting the sender
2. **Configure network parameters before clicking Initialize** - they cannot be changed after
3. **For sender role**:
   - Remote host and port fields are enabled to specify the receiver's address
   - Sender timeout field is enabled (used for retry intervals)
   - Receiver timeout field is disabled (not used by sender)
4. **For receiver role**:
   - Remote fields are disabled (receiver learns sender address from incoming packets)
   - Receiver timeout field is enabled (used for skip logic)
   - Sender timeout field is disabled (not used by receiver)
5. **Use Auto reliability mode** to see both reliable and unreliable channels
6. **Try different payload presets** to see various game networking scenarios
7. **Start/Stop buttons** control packet transmission for the sender (i.e., should stop sending before changing test scenarios)
8. **Monitor the logs** to understand protocol behavior (ACKs, retransmissions, buffering)
9. **Full Log** is always saved to the log file specified before initialization
10. **Clear & Save Logs** buttons help log management for different scenarios during testing (i.e., changing payload types)
11. **Timeout values**: Receiver timeout should be > Sender timeout × 2 to accommodate retries
