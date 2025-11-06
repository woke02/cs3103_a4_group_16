#!/bin/bash

set -e  # Exit on error

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Error: This script must be run as root (use sudo)"
    exit 1
fi

INTERFACE="${INTERFACE:-lo}"  # loopback for local testing

echo "Using network interface: $INTERFACE"
echo "Note: Set INTERFACE environment variable to change (e.g., INTERFACE=eth0)"
echo ""

# Function to reset network to normal
reset_network() {
    echo "Resetting network to normal conditions..."
    tc qdisc del dev $INTERFACE root 2>/dev/null || true
    echo "Network reset complete!"
    tc qdisc show dev $INTERFACE
}

scenario_tc1() {
    echo "Applying: TC1 - Ideal network (baseline)"
    echo "  Loss: 0%, Delay: 0ms, Jitter: 0ms"
    reset_network
}

scenario_tc2() {
    echo "Applying: TC2 - Low-latency wired"
    echo "  Loss: 0.1%, Delay: 5ms, Jitter: 1ms"
    tc qdisc add dev $INTERFACE root netem \
        loss 0.1% \
        delay 5ms 1ms \
        limit 1000
}

scenario_tc3() {
    echo "Applying: TC3 - WiFi"
    echo "  Loss: 1%, Delay: 20ms, Jitter: 4ms"
    tc qdisc add dev $INTERFACE root netem \
        loss 1% \
        delay 20ms 4ms \
        limit 1000
}

scenario_tc4() {
    echo "Applying: TC4 - 4G mobile"
    echo "  Loss: 2%, Delay: 50ms, Jitter: 10ms"
    tc qdisc add dev $INTERFACE root netem \
        loss 2% \
        delay 50ms 10ms \
        limit 1000
}

scenario_tc5() {
    echo "Applying: TC5 - Congested network"
    echo "  Loss: 5%, Delay: 100ms, Jitter: 20ms"
    tc qdisc add dev $INTERFACE root netem \
        loss 5% \
        delay 100ms 20ms \
        limit 1000
}

scenario_tc6() {
    echo "Applying: TC6 - High loss"
    echo "  Loss: 50%, Delay: 20ms, Jitter: 4ms"
    tc qdisc add dev $INTERFACE root netem \
        loss 50% \
        delay 20ms 4ms \
        limit 1000
}

scenario_tc7() {
    echo "Applying: TC7 - High delay"
    echo "  Loss: 1%, Delay: 200ms, Jitter: 4ms"
    tc qdisc add dev $INTERFACE root netem \
        loss 1% \
        delay 200ms 4ms \
        limit 1000
}

scenario_tc8() {
    echo "Applying: TC8 - High jitter"
    echo "  Loss: 1%, Delay: 20ms, Jitter: 50ms"
    tc qdisc add dev $INTERFACE root netem \
        loss 1% \
        delay 20ms 50ms \
        limit 1000
}

# Main script logic
case "$1" in
    tc1)
        scenario_tc1
        ;;
    tc2)
        scenario_tc2
        ;;
    tc3)
        scenario_tc3
        ;;
    tc4)
        scenario_tc4
        ;;
    tc5)
        scenario_tc5
        ;;
    tc6)
        scenario_tc6
        ;;
    tc7)
        scenario_tc7
        ;;
    tc8)
        scenario_tc8
        ;;
    reset)
        reset_network
        ;;
    *)
        echo "Error: Unknown scenario '$1'"
        exit 1
        ;;
esac

echo ""
echo "Done!"
echo "Remember to run 'sudo ./linux_netem_simulation.sh reset' when finished testing"
