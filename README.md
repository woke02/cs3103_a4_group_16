# CS3103 Assignment 4 - H-UDP Protocol Implementation

Real-time game networking data is heterogeneous, requiring both high reliability (for critical events like damage) and low latency (for ephemeral updates like player position). This report details H-UDP, a custom transport protocol that provides two logical channels over a single UDP socket to meet these conflicting needs. H-UDP combines a reliable channel using Selective Repeat (SR) ARQ with an unreliable "fire-and-forget" channel, allowing the application to choose the delivery guarantee per-message.

## Project Structure

```bash
cs3103_a4_group_16/
├── demo/                                       # Demo applications
│   ├── app.py                                  # GUI demo application
│   ├── config.py                               # Demo configuration and payload presets
│   ├── example_usage.py                        # Simple command-line demo
│   └── README.md                               # Demo application documentation
├── network_emulation/
│   ├── graphs/                                 # Experiment graphs (png files)
│   ├── results/                                # Experiment results (json files)
│   ├── draw_graphs.py                          # Results visualization script
│   ├── linux_netem_simulation.sh               # Network emulation script (Linux)
│   ├── README.md                               # Experiment documentation
│   ├── run_simulation.bat                      # Network emulation script (Windows)
│   └── windows_clumsy_guide.md                 # Clumsy setup guide (Windows)
├── packet_tracking/                            # Runtime tracking files (auto-created)
├── reports/                                    # Supporting documentation
│   ├── AHTP-Assignment4-miniProject.pdf        # Assignment Requirements
│   ├── CS3103 Assignment 4 Report Group 16.pdf # Final report
├── src/                                        # Protocol implementation
│   ├── game_net_api.py                         # Main GameNetAPI class
│   └── protocol/
│       ├── packet.py                           # Packet encoding/decoding
│       ├── sr_sender.py                        # Selective Repeat sender
│       ├── sr_receiver.py                      # Selective Repeat receiver
│       ├── unreliable_sender.py                # Unreliable sender
│       └── unreliable_receiver.py              # Unreliable receiver
├── .gitignore                                  # Git ignore file
└── README.md                                   # This file
```

## Demo Applications

<https://github.com/user-attachments/assets/73b572a5-46ee-4767-bf69-7d327c124d57>

## Authors

Group 16 - CS3103 AY2024/25
