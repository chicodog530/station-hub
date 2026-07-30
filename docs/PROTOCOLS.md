# Protocols

## Legacy Audio Relay (Port 7373)
The Legacy server is a raw TCP socket. When a client connects, the Hub instantly begins streaming raw, uncompressed 16-bit PCM Audio (`48000 Hz, 1 Channel, int16`).
Any bytes sent *by* the client to the server are interpreted identically and piped directly to the radio's audio output stream.
- **Pros:** Incredibly simple. Just `netcat` to port 7373 and pipe audio.
- **Cons:** No metadata, no drop-detection, latency builds up if network buffers lag.

## YAR1 Audio Protocol (Port 7374)
YWD Audio Relay (YAR1) is a framed chunk protocol designed for modern modems.
It prefixes chunks of audio with sequence numbers to track latency and drop out-of-order packets.

### Handshake
1. Client connects via TCP.
2. Client sends a `HELLO` packet (`0x00`).
3. Server responds with a `HELLO_ACK` (`0x01`).
4. Bi-directional audio stream begins.

### Audio Frames (`0x02`)
Both client and server wrap PCM audio in this frame:
- `Type` (1 byte): `0x02`
- `Sequence` (4 bytes, unsigned int): Increments for every chunk.
- `Length` (2 bytes, unsigned short): Number of audio bytes to follow.
- `Payload` (N bytes): Raw 16-bit PCM audio data.

Clients should discard any packets with a sequence number lower than the highest received.
