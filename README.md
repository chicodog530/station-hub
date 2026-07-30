# Station Hub

Station Hub is the core infrastructure for your Amateur Radio network. It wraps Hamlib `rigctld` and your OS audio system into a unified, network-accessible API.

Instead of writing complex rig control logic into every app you build, simply connect your apps to the Station Hub over TCP/IP or WebSockets.

## Installation

To set up the Station Hub on a new computer, you don't need to be a programmer!

1. Simply double-click `install.bat`.
2. The script will automatically check if you have Python installed. If you don't, it will invisibly download and install Python 3.11 for you.
3. It will then automatically install all the required audio and control libraries.

## Running the Hub

Once installed, simply double-click `run.bat`.
The Hub will automatically manage the bundled `rigctld.exe` engine, hook into your OS audio streams, and start its network listeners!

## Installing the Android Walkie-Talkie App

This repository includes a pre-built Android application (`ssb-walkie.apk`) that connects to the Station Hub over your local Wi-Fi.

To install it on your phone:
1. Connect your Android phone to your PC using a USB cable.
2. On your PC, copy the `ssb-walkie.apk` file from this folder.
3. Open your phone in Windows File Explorer and paste the `.apk` file into your phone's **Downloads** folder.
4. On your phone, open your File Manager app, navigate to Downloads, and tap on `ssb-walkie.apk`.
5. *Note: Your phone may warn you about installing unknown apps. Tap "Settings" on the popup and enable "Allow from this source", then go back and tap Install again.*

## Developer Documentation
If you want to build a new interface (like a web dashboard or an iOS app) or write a custom modem, refer to the Developer Docs:
- [Architecture](docs/ARCHITECTURE.md)
- [WebSocket API Reference](docs/API_REFERENCE.md)
- [Audio Protocols](docs/PROTOCOLS.md)
