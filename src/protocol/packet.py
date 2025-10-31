import struct
import time

CHANNEL_RELIABLE = 0x00
CHANNEL_UNRELIABLE = 0x01
PACKET_TYPE_ACK = 0x02

MAX_PAYLOAD_SIZE = 1391
MAX_SEQ_NUM = 65536


def encode_data_packet(channel_type, seq_no, payload):
    if isinstance(payload, str):
        payload = payload.encode('utf-8')
    
    if len(payload) > MAX_PAYLOAD_SIZE:
        raise ValueError(f"Payload too large: {len(payload)} > {MAX_PAYLOAD_SIZE}")
    
    timestamp = int(time.time() * 1000) & 0xFFFFFFFF
    
    header = struct.pack('!BHIH', 
                        channel_type,
                        seq_no & 0xFFFF,
                        timestamp,
                        len(payload))
    
    return header + payload


def decode_data_packet(packet_bytes):
    if len(packet_bytes) < 9:
        raise ValueError("Packet too short")
    
    channel_type, seq_no, timestamp, payload_len = struct.unpack('!BHIH', packet_bytes[:9])
    
    payload = packet_bytes[9:9+payload_len]
    
    if len(payload) != payload_len:
        raise ValueError("Payload length mismatch")
    
    return {
        'channel_type': channel_type,
        'seq_no': seq_no,
        'timestamp': timestamp,
        'payload': payload
    }


def encode_ack_packet(ack_no, timestamp):
    return struct.pack('!BHI',
                      PACKET_TYPE_ACK,
                      ack_no & 0xFFFF,
                      timestamp & 0xFFFFFFFF)


def decode_ack_packet(packet_bytes):
    if len(packet_bytes) < 7:
        raise ValueError("ACK packet too short")
    
    packet_type, ack_no, timestamp = struct.unpack('!BHI', packet_bytes[:7])
    
    if packet_type != PACKET_TYPE_ACK:
        raise ValueError("Not an ACK packet")
    
    return {
        'ack_no': ack_no,
        'timestamp': timestamp
    }


def is_ack_packet(packet_bytes):
    return len(packet_bytes) >= 1 and packet_bytes[0] == PACKET_TYPE_ACK


def get_current_timestamp():
    return int(time.time() * 1000) & 0xFFFFFFFF
