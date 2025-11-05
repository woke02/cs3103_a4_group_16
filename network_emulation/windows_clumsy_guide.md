# Windows Clumsy simulation guide

Clumsy operates at the WinDivert driver level to intercept and manipulate network packets.

## Installation

1. Download Clumsy
2. Run as Administrator
3. Allow it in firewall / antivirus software


## Setup

1. **Filter:**
   - Default: all packets
   - Examples:
     ```
     udp and (ip.DstAddr == 127.0.0.1 or ip.SrcAddr == 127.0.0.1)
     udp.DstPort == 6000 or udp.SrcPort == 6000
     ```

2. **Checkboxes:**
   - **Lag**: Add delay to packets
   - **Drop**: Drop packets (loss)
   - **Throttle**: Limit bandwidth
   - **Duplicate**: Duplicate packets
   - **Out of order**: Reorder packets
   - **Tamper**: Corrupt packet data (not suitable for our case)

3. "Start" to begin emulation, "Stop" to disable
