# WebSocket API Reference

The Station Hub runs a WebSocket API server on port `7375` (by default).
It broadcasts the current state of the radio to all connected clients and accepts JSON commands.

## Broadcast State
The Hub pushes this `radio_state` packet to all connected clients whenever any parameter changes:

```json
{
  "type": "radio_state",
  "frequency_hz": 14328160,
  "mode": "USB",
  "ptt": false,
  "rf_power": 0.5,
  "swr": 1.1,
  "alc": 0.2,
  "tuning": false
}
```

## Client Commands
Send these JSON packets to control the radio:

### Set Frequency
```json
{
  "type": "set_frequency",
  "frequency_hz": 7200000
}
```

### Set Mode
```json
{
  "type": "set_mode",
  "mode": "LSB"
}
```

### Set RF Power
`power` is a float between 0.0 and 1.0 (0% to 100%).
```json
{
  "type": "set_rf_power",
  "power": 0.75
}
```

### Set Band (Band Macro)
```json
{
  "type": "set_band",
  "band_code": "BS05;"
}
```
*Note: Uses Yaesu BS index commands (e.g. BS05 is 20m).*

### Trigger Auto-Tuner
```json
{
  "type": "set_tune",
  "enable": true
}
```

### Toggle Radio Power
```json
{
  "type": "set_power",
  "on": true
}
```

### Push-to-Talk (PTT) Sequence
To initiate transmission, you must request PTT ON, and then send a `ptt_keepalive` packet every 200ms. If the Hub does not receive a keepalive for 0.5 seconds, it automatically drops TX to prevent stuck transmitters.

```json
{
  "type": "ptt_request_on"
}
```
*(Send this every 200ms during TX):*
```json
{
  "type": "ptt_keepalive"
}
```
*(To stop TX):*
```json
{
  "type": "ptt_request_off"
}
```
