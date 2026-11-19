# QubeSat ground station uplink (PlutoSky)

Sends encrypted FSK commands to the satellite from a laptop with a PlutoSky
(ADALM-Pluto compatible SDR). The satellite's LoRa beacons are received
separately, by the LILYGO TinyGS station.

| File | What it does |
| --- | --- |
| `commands.py` | Builds command packets, byte-for-byte the same as `NewCode/Comms.py` |
| `fsk.py` | Frames and modulates them to match the satellite's SX127x FSK receiver |
| `pluto_uplink.py` | Command-line tool that transmits with the PlutoSky |
| `../NewCode/fsk_listen_test.py` | Satellite-side bench test: prints and checks received commands |

## Radio settings

433.0 MHz, 2-FSK, 9600 bps, ±25 kHz deviation, 8-byte `AA` preamble,
sync word `2D D4`, variable length, CRC-16 CCITT (seed `1D0F`, inverted),
no whitening. These must match `NewCode/DualModeRadio.py`.

## Setup

```sh
pip install pyadi-iio numpy cryptography
```

Plug the PlutoSky into the laptop by USB. It appears at `ip:192.168.2.1`.

## Use

```sh
cd groundstation
python3 pluto_uplink.py state IDLE --dry-run    # build and self-check, no radio
python3 pluto_uplink.py state IDLE              # send 10 times at -40 dB
python3 pluto_uplink.py config 50 10 3
python3 pluto_uplink.py lora 60                 # ask for a 60 s LoRa window
python3 pluto_uplink.py fsk                     # return the satellite to FSK
```

Options: `--attenuation -40` (0 is loudest, -89.75 quietest), `--repeat 10`,
`--interval 0.5`, `--uri ip:192.168.2.1`.

## AES key

Commands are encrypted with the key in `_AES_KEY` in `NewCode/Comms.py`,
currently the all-zero placeholder. Set the real key with
`export QUBESAT_AES_KEY=<32 hex characters>`. Never commit the real key.

## Bench test

1. Put `NewCode/fsk_listen_test.py` on the PyCubed as `code.py`, with
   `Comms.py` and `DualModeRadio.py`. Burn wires disconnected.
2. Open the PyCubed serial output: `screen /dev/tty.usbmodem101 115200`.
3. Run `python3 pluto_uplink.py state IDLE`.
4. Pass: the PyCubed prints `VALID SET_STATE args: [1]`.

Transmitting on 433 MHz needs a licensed amateur operator.

## Tests

```sh
python3 -m unittest unit_tests.test_groundstation -v
```
