# Annex A4: Comms (Tyler, Jonathan)

Draft for STAC-AIT-ITP-001 Rev 2, Part A. This file mirrors the annex in the
ITP Google Doc; the ITP is the controlling copy. Items marked **TBD** are unknown
or need a decision (red in the ITP). The shared sections of the ITP (execution
record, general safety, common initial configuration, return to safe, anomaly
log, closure) apply and are not repeated here.

**Scope:** verifies the PyCubed radio initializes with the flight settings, sends
the beacon in both modes (LoRa and FSK) at a usable signal level, and receives and
verifies an encrypted ground command sent from the PlutoSky ground station.
Requirements: REQ-COM-001, REQ-COM-002 (mapping of each test case to an ID **TBD**
against AD-07). Scripts, all on branch `tinygs`: `NewCode/Comms.py` (probe mode),
`NewCode/lora_bench_test.py`, `NewCode/fsk_bench_test.py`,
`NewCode/fsk_listen_test.py`, `groundstation/pluto_uplink.py`. Range
(REQ-COM-003) is outside this annex.

**Equipment:**

- PyCubed v05, HopeRF radio on Radio 1, 433 MHz antenna on the Radio 1 connector
- LILYGO T3 V1.6.1 433 MHz running TinyGS (station STAC1), with antenna, USB to a laptop for serial output
- PlutoSky SDR with a 433 MHz antenna on TX1, plugged directly into a laptop (no USB-C hub), with libiio 0.26, `pylibiio==0.25`, `pyadi-iio`
- Optional: 30–40 dB SMA attenuator and coax, for a cabled (non-radiating) setup
- Laptop(s) with the repo on `tinygs` and a serial terminal at 115200 baud

## A4.1 Known pitfalls

- 433 MHz is in the 70 cm amateur band: any over-the-air transmission (PyCubed or PlutoSky) needs a licensed control operator present. The cabled setup with an attenuator avoids radiating; confirm it with the licensee.
- Never transmit without an antenna or attenuated load on the PyCubed Radio 1 or PlutoSky TX1.
- Always put a test script on the board as `code.py` before power-on. With no `code.py`, `main.py` runs and can load the FSM.
- The board may still hold old files: an old `code.py` sent `PYCUBED TEST` at 437.42 MHz, 20 dBm, and an old `Comms.py` imported `StateCodeGenerator` (needs `enum`, missing in CircuitPython). Copy `Comms.py` and `DualModeRadio.py` from `tinygs` before every run.
- Desktop tests don't catch CircuitPython differences: `str.ljust()` crashed every beacon until PR #5. A pass on the laptop is not a pass on the board.
- `pycubed_rfm9x.send()` adds a 4-byte header. Send with `Comms.send_raw()`, or packets are 20 bytes instead of 16.
- The sync word is register 0x39 = 0x12, not `radio.node` (that is an address filter).
- `Comms.py` falls back to XOR if `aesio` is missing. Never build ground commands with `Comms.py` on a laptop; use `groundstation/commands.py`.
- One PyCubed dropped off USB with repeated `transaction error` and never mounted `CIRCUITPY`. Use a board that mounts; report the other to EPS.
- PlutoSky: no connection through a USB-C hub. Plug it straight into the laptop and wait ~60 s for `ping 192.168.2.1`. `No route to host` means it is rebooting.
- macOS: Homebrew has no libiio. Install the v0.26 package, `brew install libusb libserialport`, and pin `pylibiio==0.25` (1.0 needs libiio 1.x).
- The TinyGS website does not log packets from an unregistered satellite. Use the LILYGO serial output as the record.
- Set TinyGS Auto Tune to Disabled before a test, or the station retunes to a passing satellite.

## A4.2 Initial configuration (after section 5)

| Step | Action | Expected value | Measured value | Remarks |
| --- | --- | --- | --- | --- |
| A4.2.1 | On the laptop, from the repo root on `tinygs`, run `python3 -m unittest unit_tests.test_newcode_comms unit_tests.test_dual_mode_radio unit_tests.test_groundstation` | `Ran 26 tests`, `OK` | | |
| A4.2.2 | Supply OFF. Check the burn wire outputs | 0 nichrome connected on JP11/JP12 | | |
| A4.2.3 | Attach the 433 MHz antenna to the Radio 1 connector, or the attenuated cable | Connector seated; 0 open RF outputs | | |
| A4.2.4 | Copy `NewCode/Comms.py` and `NewCode/DualModeRadio.py` to the top level of `CIRCUITPY` | Both files present; git hash recorded in section 0 | | |
| A4.2.5 | List `CIRCUITPY/lib` | `pycubed.py` and `pycubed_rfm9x.py` present | | |
| A4.2.6 | Power the LILYGO; open the STAC1 station page | Status Online; Radio Status Ready | | |
| A4.2.7 | Edit Station → Test Mode ON, save | Test mode: ON | | |
| A4.2.8 | Operate → Auto Tune Disabled, save | Auto tuning: OFF | | |
| A4.2.9 | Open the LILYGO serial terminal at 115200, start logging | Log file named per section 0 | | |
| A4.2.10 | Plug the PlutoSky directly into its laptop, wait 60 s, run `ping -c 2 192.168.2.1` | 2 of 2 replies, 0 % loss | | |
| A4.2.11 | Run `python3 -c "import adi; s = adi.Pluto('ip:192.168.2.1'); print('Connected, tx_lo =', s.tx_lo)"` | `Connected, tx_lo =` followed by a number | | |
| A4.2.12 | From `groundstation/`, run `python3 pluto_uplink.py state IDLE --dry-run` | `Self-check: OK` | | |
| A4.2.13 | Place the PyCubed and LILYGO/PlutoSky antennas apart | 2.0 m ± 0.5 m (**TBD**), or cabled through 30 dB ± 3 dB | | |

### TC-A4-01 Radio init: REQ-COM-001

Uses the `probe` mode built into `Comms.py`: it configures Radio 1 and prints the settings without transmitting.

| Step | Action / Command | Expected value | Measured value | Remarks |
| --- | --- | --- | --- | --- |
| 1.1 | Copy `NewCode/Comms.py` to `CIRCUITPY` a second time, named `code.py` | Board restarts; console prints `Radio initialized.` | | |
| 1.2 | Read `Frequency (MHz)` | 433.0 ± 0.001 | | |
| 1.3 | Read `TX power (dBm)` | 5 | | |
| 1.4 | Read `BW` | 125000 | | |
| 1.5 | Read `SF` | 7 | | |
| 1.6 | Read `CR` | 5 | | |
| 1.7 | Read `CRC` | True | | |
| 1.8 | Read the last console line | `Probe complete. Radio1 is alive and configurable.`; 0 `[ERROR]` lines | | |
| 1.9 | Read the supply current with the radio idle | 0.25 A ± 0.05 (**TBD**, from A1 step 1.1) | | |

### TC-A4-02 LoRa beacon and RSSI: REQ-COM-001

The PyCubed sends 20 beacons, 3 s apart, at 5 dBm. Reference run on 11/11/2026: 20 of 20 received, about −23 dBm RSSI, 9 dB SNR.

| Step | Action / Command | Expected value | Measured value | Remarks |
| --- | --- | --- | --- | --- |
| 2.1 | Operate → Manual Tuning: `STAC-test`, LoRa, 433.0 MHz, BW 125 kHz, SF 7, CR 5, sync word 18, preamble 8, CRC on; save | Listening: `STAC-test` | | |
| 2.2 | Copy `NewCode/lora_bench_test.py` to `CIRCUITPY` as `code.py` | `TX 0 ok` printed 10 s ± 1 s after restart | | |
| 2.3 | Read the first packet on the PyCubed console | `d0535441432020011ce84100000000ee` | | |
| 2.4 | Count `ok` lines when `Done.` prints | 20 of 20 `ok`, 0 `TIMEOUT` | | |
| 2.5 | Count packets in the LILYGO log | ≥ 19 of 20 (**TBD** packet success) | | |
| 2.6 | Read each received packet length | 16 bytes | | |
| 2.7 | Compare received bytes with the PyCubed console | 100 % of received packets identical | | |
| 2.8 | Read RSSI on the LILYGO for each packet; record min and max | −23 dBm ± 10 dB at A4.2.13 spacing (**TBD**) | | |
| 2.9 | Read SNR on the LILYGO; record the minimum | ≥ 5 dB (**TBD**) | | |
| 2.10 | Count CRC errors in the LILYGO log | 0 | | |
| 2.11 | Min bus V on the supply during the run | ≥ 6.0 V, no reset | | |

### TC-A4-03 FSK beacon: REQ-COM-001

The PyCubed switches to FSK and sends 20 beacons, 3 s apart. Each frame on air is a length byte (0x10) followed by the 16-byte beacon. Not yet run on hardware; TinyGS FSK framing compatibility is **TBD**.

| Step | Action / Command | Expected value | Measured value | Remarks |
| --- | --- | --- | --- | --- |
| 3.1 | Operate → Manual Tuning: `STAC-test`, FSK, 433.0 MHz, bitrate 9.6 kbps, deviation 25 kHz, RX bandwidth 100 kHz (**TBD**: nearest TinyGS option), sync word `2D D4`, preamble 8, CRC on; save | Listening: `STAC-test`, mode FSK | | |
| 3.2 | Copy `NewCode/fsk_bench_test.py` to `CIRCUITPY` as `code.py` | `Switched to FSK.` then `FSK TX 0 ok` 10 s ± 1 s after restart | | |
| 3.3 | Count `ok` lines when `Done.` prints | 20 of 20 `ok`, 0 `FAILED` | | |
| 3.4 | Count packets in the LILYGO log | ≥ 19 of 20 (**TBD** packet success) | | |
| 3.5 | Compare received bytes with the PyCubed console | 16-byte payload starting `D0 53 54 41`, identical to the console (length byte shown or not: **TBD**) | | |
| 3.6 | Read RSSI on the LILYGO; record min and max | Within 10 dB of the step 2.8 values (**TBD**) | | |
| 3.7 | Count CRC errors in the LILYGO log | 0 | | |

### TC-A4-04 Ground command reception and ACK: REQ-COM-002

The PlutoSky sends encrypted FSK commands (433.0 MHz, 9600 bps, ±25 kHz, sync `2D D4`). `fsk_listen_test.py` decrypts and checks each one and prints what it would do, without changing the saved state. Licensed operator present unless cabled. The current FSW sends no ACK, so steps 4.8–4.9 are **TBD** until one is defined.

| Step | Action / Command | Expected value | Measured value | Remarks |
| --- | --- | --- | --- | --- |
| 4.1 | Copy `NewCode/fsk_listen_test.py` to `CIRCUITPY` as `code.py` | `Listening on FSK. Send commands from the ground station now.` | | |
| 4.2 | From `groundstation/`, run `python3 pluto_uplink.py state IDLE` | Ground prints `Command bytes: c0af4131b7833047944ee22365ab6cbb88`, `sent 1` to `sent 10` | | |
| 4.3 | Count `RX` lines on the PyCubed | ≥ 9 of 10 (**TBD** packet success), each `17 bytes: c0af4131b7833047944ee22365ab6cbb88` | | |
| 4.4 | Read the line after each `RX` | `VALID SET_STATE args: [1]`; 0 `FAILED` lines | | |
| 4.5 | Run `python3 pluto_uplink.py config 50 10 3` | `VALID SET_CONFIG args: [50, 10, 3]` | | |
| 4.6 | Run `python3 pluto_uplink.py lora 60` | `VALID SET_MODULATION args: [0, 60]` | | |
| 4.7 | Run `QUBESAT_AES_KEY=11111111111111111111111111111111 python3 pluto_uplink.py state IDLE` (wrong key) | `decrypt FAILED` on every `RX`; 0 `VALID` | | |
| 4.8 | Send `state SCIENCE` to the full FSW, then read the next beacon's state byte (byte 7) | State byte = 3 (**TBD**: ACK method) | | |
| 4.9 | Time from last command sent to ACK received | ≤ **TBD** s | | |

## A4.3 Traceability

| Requirement (AD-07) | Annex A4 case | Part B |
| --- | --- | --- |
| REQ-COM-001 (**TBD**: confirm wording) | TC-A4-01, TC-A4-02, TC-A4-03 | TC-B04 (B4.3) |
| REQ-COM-002 (**TBD**: confirm wording) | TC-A4-04 | TC-B04 (B4.3), TC-B06 (B6.2) |
| REQ-COM-003 (range) | N/A | Field range test (tasks 23–24), outside ITP |

**Open TBDs for section 9 (owners Tyler, Jonathan):**

- Packet success threshold (draft: ≥ 19 of 20 beacons, ≥ 9 of 10 commands)
- RSSI and SNR tolerance at bench spacing, and the bench spacing itself
- TinyGS FSK settings and whether its FSK framing matches the PyCubed's
- Command ACK: method (draft: beacon state byte) and maximum ACK time; current FSW has no ACK
- Idle current with the radio on
- Whether the cabled setup is accepted instead of over-the-air with a licensed operator
