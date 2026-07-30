# SSB Walkie-Talkie with Rig Control

This is the Android companion app for the PC **Station Hub**. It allows you to use your Android device as a remote Walkie-Talkie for your amateur radio station, streaming audio over your local network and controlling the radio via CAT.

## Features
- **Remote Audio Streaming**: Streams high-quality TX and RX audio using low-latency UDP-like sockets (Port 7373).
- **Live Rig Control**: Connects to the Hub's WebSocket API (Port 7375) to display real-time Frequency and Mode directly on your screen.
- **Remote Tuning**: Tap the "TUNE" or "MODE" buttons to instantly change the frequency and mode of your radio from the phone.
- **Hardware PTT Safety**: The PTT button on the app is deeply integrated with the Hub's safety Watchdog. It automatically requests PTT via the API and sends rapid keep-alive signals while held down. If your phone loses connection or crashes, the radio will automatically un-key within 1 second.

## How to use
1. Start the `station_hub.py` script on your PC. It will automatically start listening on Ports 7373 (Legacy Audio) and 7375 (API).
2. Install `ssb-walkie.apk` onto your Android phone.
3. Open the app and enter the local IP address of your PC (e.g., `192.168.1.100`).
4. Tap **CONNECT**. 
5. The Rig Control panel should immediately show your radio's current frequency. If it says "API OFFLINE", check your PC's firewall settings for Port 7375.
6. Press and hold the big **PTT** button to talk!
