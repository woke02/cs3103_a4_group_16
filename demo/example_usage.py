"""
Example API Usage

This script demonstrates basic usage of the H-UDP GameNetAPI
without the GUI. Useful for testing and understanding the API.
"""

import time
import json
import sys
import os

# Add parent directory to path to import src
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from src.game_net_api import GameNetAPI

def example_sender():
    """Example sender that sends a few packets and exits."""
    print("=" * 60)
    print("SENDER EXAMPLE")
    print("=" * 60)
    
    # Initialize sender
    sender = GameNetAPI(
        role='sender',
        local_port=5000,
        remote_addr=('localhost', 6000),
        sender_timeout=0.200,
        receiver_timeout=0.450
    )
    
    print("\nSender initialized. Sending packets...\n")
    
    # Example payloads
    payloads = [
        {
            "type": "position_update",
            "player_id": "player_123",
            "x": 100.5,
            "y": 200.3,
            "z": 10.0
        },
        {
            "type": "health_update",
            "player_id": "player_123",
            "health": 75,
            "max_health": 100
        },
        {
            "type": "chat",
            "player_id": "player_123",
            "message": "Hello, world!",
            "channel": "global"
        }
    ]
    
    for i, payload_dict in enumerate(payloads):
        # Determine reliability based on type
        is_reliable = payload_dict.get("type") in ["health_update", "chat"]
        
        # Encode as JSON
        payload_json = json.dumps(payload_dict)
        payload_bytes = payload_json.encode('utf-8')
        
        # Send
        seq_no = sender.send(payload_bytes, reliable=is_reliable)
        print(f"[{i+1}] Sent seq={seq_no}, reliable={is_reliable}, "
              f"type={payload_dict['type']}")
        
        time.sleep(0.5)  # Wait 500ms between packets
    
    print("\nWaiting 2 seconds for ACKs...\n")
    time.sleep(2)
    
    # Close
    sender.close()
    print("Sender closed.")


def example_receiver():
    """Example receiver that listens for a few packets and exits."""
    print("=" * 60)
    print("RECEIVER EXAMPLE")
    print("=" * 60)
    
    # Initialize receiver
    receiver = GameNetAPI(
        role='receiver',
        local_port=6000,
        sender_timeout=0.200,
        receiver_timeout=0.450
    )
    
    print("\nReceiver initialized. Waiting for packets...\n")
    
    # Receive packets for 5 seconds
    start_time = time.time()
    packet_count = 0
    
    while time.time() - start_time < 5:
        packet = receiver.receive(timeout=1.0)
        
        if packet:
            packet_count += 1
            
            # Extract information
            seq_no = packet['seq_no']
            payload = packet['payload']
            latency = packet['latency']
            channel = packet['channel']
            
            # Try to decode as JSON
            try:
                payload_str = payload.decode('utf-8')
                payload_dict = json.loads(payload_str)
                payload_type = payload_dict.get('type', 'unknown')
            except (UnicodeDecodeError, json.JSONDecodeError):
                payload_type = 'binary'
            
            print(f"[{packet_count}] Received seq={seq_no}, channel={channel}, "
                  f"latency={latency}ms, type={payload_type}")
    
    # Close
    receiver.close()
    print(f"\nReceiver closed. Received {packet_count} packets.")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2 or sys.argv[1] not in ['sender', 'receiver']:
        print("Usage: python3 demo/example_usage.py [sender|receiver]")
        print()
        print("Run in two terminals:")
        print("  Terminal 1: python3 demo/example_usage.py receiver")
        print("  Terminal 2: python3 demo/example_usage.py sender")
        sys.exit(1)
    
    role = sys.argv[1]
    
    if role == 'sender':
        example_sender()
    else:
        example_receiver()
