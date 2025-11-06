## Test cases

### TC1. Ideal network (baseline)
- **Loss:** 0%
- **Delay:** 0ms
- **Jitter:** 0ms

### TC2. Low-latency wired
- **Loss:** 0.1%
- **Delay:** 5ms
- **Jitter:** 1ms

### TC3. WiFi
- **Loss:** 1%
- **Delay:** 20ms
- **Jitter:** 4ms

### TC4. 4G mobile
- **Loss:** 2%
- **Delay:** 50ms
- **Jitter:** 10ms

### TC5. Congested network
- **Loss:** 5%
- **Delay:** 100ms
- **Jitter:** 20ms

### TC6. High loss
- **Loss:** 50%
- **Delay:** 20ms
- **Jitter:** 4ms

### TC7. High delay
- **Loss:** 1%
- **Delay:** 200ms
- **Jitter:** 4ms

### TC8. High jitter
- **Loss:** 1%
- **Delay:** 20ms
- **Jitter:** 50ms


## Run tests

### Linux

**Requirements**:
- Linux kernel with netem support
- iproute2 package installed
- Root/sudo privileges

**Usage**:
- `sudo ./linux_netem_simulation.sh tcx`, `tcx` e.g. `tc1`
- `sudo ./linux_netem_simulation reset`

### Windows

See [windows_clumsy_guide.md](./windows_clumsy_guide.md)
