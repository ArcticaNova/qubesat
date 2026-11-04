# FSK uplink by default, LoRa downlink for TinyGS

The FSM already calls `CommsManager.update()`, so no state-code changes are needed.
Copy `DualModeRadio.py` alongside `Comms.py` when updating the board.
`configure_radio()` prepares the LoRa hardware profile; `CommsManager` immediately
switches the satellite to FSK for ground-station uplink reception.

During normal operation, the existing RX/TX schedule listens in FSK for `rx_ticks`,
then switches to LoRa for the TX window. The FSM queues TinyGS telemetry using its
existing cadence. When queues drain or `tx_packet_count` is reached, the satellite
returns to FSK. A LoRa timeout also forces FSK after at most 60 seconds by default.
The deadline is checked by `update()`; keep calling it. Queued packets survive
mode switches. STOP disables scheduled downlinks while FSK reception remains active.

## Satellite usage

```python
from Comms import FSK, LORA

# CommsManager starts in FSK automatically.
comms.send_fsk(b'\xA0configuration status')  # optional, maximum 63 bytes
comms.set_modulation(LORA, duration_s=60)   # temporary LoRa window
comms.set_modulation(FSK)                  # immediate return to uplink listening
```

A LoRa window ends when its timeout expires or a TX window finishes, whichever
comes first. Repeated LoRa requests do not extend the deadline. Startup mode is
not persisted to NVM: each normal startup returns to FSK. The low-level
`DualModeRadio` adapter still starts in LoRa because it wraps the prepared driver;
use `set_modulation(FSK)` when using it directly on a ground transceiver.

## Ground-command sequence

1. Send existing `build_config_command(...)` or `build_state_command(...)`
   packets using the FSK profile below. Transmit application bytes directly,
   without a RadioHead header. With `DualModeRadio`, use `set_modulation(FSK)`
   and `send_packet(packet)` on the ground transceiver.
2. To request a LoRa window, send `build_modulation_command(LORA, duration_s=60)`
   over FSK. Retune any receiver intended to communicate in that window to LoRa.
3. Wait for automatic FSK return, or send `build_modulation_command(FSK)` in the
   current LoRa mode using `send_raw()`, then retune your uplink transceiver to FSK.

TinyGS does not automatically request a switch in this implementation. Scheduled
LoRa downlinks let TinyGS receive telemetry; an FSK ground command opens an explicit
LoRa window. There is no switch acknowledgement or control of TinyGS station settings.
A single radio cannot listen for FSK uplinks while it is transmitting/listening in
LoRa. Coordinate windows and retry ground commands during FSK listening periods.
The command duration field now applies to LoRa; FSK commands use zero. Update any
ground command builder together with the satellite code.

## Matching receiver profiles

| Parameter | LoRa | FSK |
| --- | --- | --- |
| Frequency | 433 MHz | 433 MHz |
| Bandwidth | 125 kHz | 100 kHz RX; 125 kHz AFC |
| Spreading factor / coding rate | SF7 / 4/5 | Not applicable |
| Bitrate / frequency deviation | Not applicable | 9.6 kbps / 25 kHz |
| Preamble | 8 symbols | 8 bytes |
| Sync | 0x12 | 0x2D, 0xD4 |
| Packet format | Existing LoRa format | Variable length; length byte then 1–63 application bytes |
| CRC | Enabled | Enabled, CCITT |
| Whitening / Manchester / address filtering | Existing LoRa format | Disabled |

TinyGS supports tuning one receiver between these profiles; it must be tuned to
the satellite's current mode. This code changes the satellite, not TinyGS firmware
or its station configuration. Existing TinyGS beacons remain 16-byte LoRa packets.
Custom FSK application downlinks require a matching decoder. Use your uplink-capable
ground transceiver to send configuration commands; receiver support alone does
not provide an uplink.

TinyGS tuning reference:
https://github.com/tinygs/tinyGS/wiki/Radio-Tuning-Guide
SX127x register and framing reference:
https://jgromes.github.io/RadioLib/_s_x127x_8h_source.html

## Validation

Run from the repository root:

```sh
python3 -m unittest unit_tests.test_newcode_comms unit_tests.test_dual_mode_radio -v
```

Desktop tests cover command dispatch, FSK FIFO framing/CRC rejection, LoRa register
restoration, LoRa timeout in STOP, FSK startup reception, scheduled LoRa downlinks, queue retention and AES write-into buffers.
They do not validate RF performance or TinyGS decoding. Before using on hardware,
bench-test both directions with matching FSK settings, early and timed FSK return,
and the original TinyGS beacon decoding. The existing command key/protocol remains
unchanged; this does not add replay protection or a new authentication scheme.
