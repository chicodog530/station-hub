# Architecture

Station Hub is designed as a centralized audio and control orchestrator for Amateur Radio transceivers. 
Instead of writing complex serial port and audio logic in every single application (e.g. your Android app, your Modems, your Web interfaces), those applications simply connect to the Station Hub over standard TCP/IP.

## Components

1. **Audio Engine (`hub.core.audio_engine`)**
   - Directly hooks into the OS sound system using `sounddevice` (`PortAudio`).
   - Runs an automatic background hot-plug thread. If the radio's USB sound card disappears (e.g., radio is powered off), it waits patiently. When the radio is powered on, it automatically detects the card and resumes the audio streams.
   - It acts as a fan-out distributor for RX audio (sending one microphone stream to multiple clients) and an exclusive muxer for TX audio.

2. **Rig Controller (`hub.core.rig_controller`)**
   - Manages CAT control through `rigctld` (Hamlib).
   - Manages the lifecycle of `rigctld.exe`. If the radio is powered off, it deliberately force-kills `rigctld.exe` to prevent it from locking up the COM port. 
   - When a Power ON command is received, it bypasses Hamlib, opens a raw serial connection, sends hardware wakeup pulses (`PS1;`), waits 5 seconds for the radio to boot, and seamlessly spins `rigctld.exe` back up.

3. **PTT Watchdog (`hub.core.ptt_watchdog`)**
   - A critical safety feature. If a connected application crashes while holding PTT, the radio could be stuck transmitting indefinitely. The Watchdog requires clients to send periodic "keepalive" packets during TX. If a keepalive is missed, it automatically drops the radio back to RX.

4. **Servers (`hub.servers.*`)**
   - **Legacy Server**: A raw TCP socket sending uncompressed 16-bit PCM audio. Used by older desktop apps.
   - **YAR1 Server**: The modern YWD Audio Relay Protocol, used by the latest modems.
   - **API Server**: A WebSocket server broadcasting state (frequency, mode, SWR) and accepting control commands. Ideal for web and mobile interfaces.
