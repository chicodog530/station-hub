# Station Hub

Station Hub is the core infrastructure for your Amateur Radio network. It wraps Hamlib `rigctld` and your OS audio system into a unified, network-accessible API.

Instead of writing complex rig control logic into every app you build, simply connect your apps to the Station Hub over TCP/IP or WebSockets.

## Getting Started

1. Double click `run.bat` (or run `python station_hub.py`).
2. The Hub will automatically manage the bundled `rigctld.exe`, hook the audio streams, and start its network listeners!

## Developer Documentation
If you want to build a new interface (like a web dashboard or an iOS app) or write a custom modem, refer to the Developer Docs:
- [Architecture](docs/ARCHITECTURE.md)
- [WebSocket API Reference](docs/API_REFERENCE.md)
- [Audio Protocols](docs/PROTOCOLS.md)
