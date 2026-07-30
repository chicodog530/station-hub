import struct

YAR1_MAGIC = b'YAR1'
VERSION = 1

# Frame Types
FT_HELLO = 0x01
FT_HELLO_ACK = 0x02
FT_AUDIO_RX = 0x10
FT_AUDIO_TX = 0x11
FT_STATUS = 0x20
FT_ERROR = 0x21
FT_PING = 0x30
FT_PONG = 0x31

def pack_header(frame_type, flags=0, reserved=0, sequence=0, payload_length=0, timestamp=0):
    """
    Packs a YAR1 header.
    Format: 
    0  - 4: Magic 'YAR1'
    4  - 1: Frame Type
    5  - 1: Flags
    6  - 2: Reserved
    8  - 4: Sequence Number (uint32)
    12 - 4: Payload Length (uint32)
    16 - 8: Timestamp/Sample Counter (uint64)
    """
    return struct.pack('>4sBBHIIQ', YAR1_MAGIC, frame_type, flags, reserved, sequence, payload_length, timestamp)

def unpack_header(data):
    """
    Unpacks a YAR1 header (first 24 bytes).
    Returns (magic, frame_type, flags, reserved, sequence, payload_length, timestamp)
    """
    if len(data) < 24:
        raise ValueError("Data too short for header")
    return struct.unpack('>4sBBHIIQ', data[:24])

def pack_hello(mode="modem", sample_rate=48000, channels=1, sample_format="s16le", block_samples=4096):
    payload = f"protocol_version={VERSION}\nmode={mode}\nsample_rate={sample_rate}\nchannels={channels}\nsample_format={sample_format}\npreferred_block_samples={block_samples}".encode('utf-8')
    return pack_header(FT_HELLO, payload_length=len(payload)) + payload

def pack_hello_ack(server_name="YWD-Relay", block_samples=4096):
    payload = f"protocol_version={VERSION}\nsample_rate=48000\nchannels=1\nsample_format=s16le\nblock_samples={block_samples}\nserver_name={server_name}\ncapabilities=audio-rx,audio-tx,sequence,timestamps,status,modem-buffering".encode('utf-8')
    return pack_header(FT_HELLO_ACK, payload_length=len(payload)) + payload

def pack_status(stats_dict):
    payload = "\n".join(f"{k}={v}" for k, v in stats_dict.items()).encode('utf-8')
    return pack_header(FT_STATUS, payload_length=len(payload)) + payload
