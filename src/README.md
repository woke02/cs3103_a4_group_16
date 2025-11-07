# GameNetAPI Specification

The GameNetAPI provides a high-level interface between the application and the H-UDP transport layer. It hides low-level details such as packet encoding, acknowledgments, retransmissions, buffering, and performance tracking, while exposing a simple API for sending and receiving game data over reliable and unreliable channels.

The API operates in two modes: sender and receiver. In both cases, it uses a single UDP socket bound to a local port and internally multiplexes traffic based on the ChannelType field in the packet header.

In sender mode, the GameNetAPI constructs:

- a Selective Repeat (SR) sender for the reliable channel, and
- an unreliable sender for the unreliable channel.

A background thread listens for incoming ACK packets and forwards them to the SR sender, which updates its sliding window and retransmission logic accordingly. The application calls `send(data, reliable=True)`; if reliable is true, the payload is passed to the SR sender, otherwise it is sent via the unreliable sender. Each sent packet is recorded in an internal dictionary and persisted to `packet_tracking/sent_packets.json` with fields such as timestamp, reliability flag, and acknowledgment status.

In receiver mode, the GameNetAPI constructs:

- an SR receiver for reliable packets, and
- an unreliable receiver for unreliable packets.

A background thread continuously reads from the UDP socket, decodes incoming DATA packets, and dispatches them based on the ChannelType. Reliable packets are passed to the SR receiver, which handles acknowledgments, buffering, reordering, and skip logic before delivery. Unreliable packets are delivered immediately. Both receivers report successfully delivered packets to the GameNetAPI through a callback, which enqueues them in a thread-safe delivery queue and logs per-packet metadata (timestamp, reliability, latency) in `packet_tracking/received_packets.json`.

The main public methods exposed by the GameNetAPI are:

- `send(data, reliable=True)`: Sends an application payload over the reliable or unreliable channel (sender mode only) and returns the assigned sequence number.
- `receive(timeout=None)`: Retrieves the next delivered packet from the internal queue (receiver mode only), or returns None if the timeout expires.
- `get_delivery_stats()`: Aggregates tracking data from the global JSON files and returns summary statistics, including total sent/received counts, per-channel delivery ratios, and a list of lost packets identified by sequence number and reliability.
- `clear_tracking_data()`: Deletes existing tracking files and clears in-memory logs to start a fresh measurement run.
- `close()`: Gracefully shuts down background threads, saves final tracking data, closes the underlying socket, and releases resources.

By encapsulating both channels behind a unified interface and automatically maintaining measurement logs, the GameNetAPI allows game developers to use H-UDP as a drop-in transport layer while still obtaining detailed reliability and performance metrics for evaluation.

## Design Choices & Trade-offs

### Selective Repeat over Go-Back-N

**Decision:** Selective Repeat ARQ with window size 32.

**Rationale:**

- Only retransmits lost packets (not entire window)
- Better bandwidth efficiency for sporadic losses (WiFi, mobile)
- Receiver complexity justified by performance gains

**Trade-off:**

- Pros: Higher throughput, especially in high-latency networks
- Cons: More complex receiver (buffering + reordering logic)

### Dual-Channel Architecture

**Decision:** Separate reliable (SR) and unreliable (fire-and-forget) channels.

**Rationale:**

- Flexibility: Application chooses delivery guarantee per-message
- Performance: Unreliable channel has ~0ms protocol overhead
- Game-appropriate:
  - Damage events $\to$ reliable (critical)
  - Position updates $\to$ unreliable (ephemeral, high-frequency)

**Trade-off:**

- Pros: Optimal performance for heterogeneous data
- Cons: Slightly more complex API (but simplified by `send(reliable=True/False)`)

### Reordering Buffer Strategy

**Decision:** Receiver maintains dynamic out-of-order buffer with timeout-based skip.

**Rationale:**

- Selective Repeat requirement: Must buffer packets beyond gaps
- In-order delivery when possible: Minimizes application-layer reordering
- Skip prevents blocking: Bounded latency via 200ms timeout

**Trade-off:**

- Pros: In-order delivery improves application logic
- Cons: Memory overhead (max 32 packets $\times$ 1.4KB = 45KB)

### JSON Payload Encoding

**Decision:** Game data encoded as JSON strings.

**Rationale:**

- Human-readable for debugging
- Easy to extend with new fields
- Built-in Python support

**Trade-off:**

- Pros: Flexibility and debuggability
- Cons: Larger than binary (but acceptable for demonstration purposes)
