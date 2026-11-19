"""QubeSat ground station uplink: send FSK commands to the satellite with a PlutoSky (ADALM-Pluto).

Examples:
    python3 pluto_uplink.py state IDLE
    python3 pluto_uplink.py config 50 10 3
    python3 pluto_uplink.py lora 60          # ask the satellite for a 60 s LoRa window
    python3 pluto_uplink.py state IDLE --dry-run   # build and self-check, no radio

Requires: pip install pyadi-iio numpy cryptography
The Pluto is reached at ip:192.168.2.1 over USB by default.

Transmitting on 433 MHz needs a licensed amateur operator. Start with high
attenuation (the default -40 dB) on the bench.
"""

import argparse
import time

import numpy as np

import commands
import fsk

FREQ_HZ = 433_000_000
SAMPLE_RATE = 960_000          # 100 samples per bit at 9600 bps
RF_BANDWIDTH = 200_000         # the narrowest the PlutoSky supports
SILENCE_S = 0.02


def build_packet(args):
    if args.command == "state":
        return commands.build_state_command(args.state)
    if args.command == "config":
        return commands.build_config_command(args.rx_ticks, args.tx_packets, args.cadence)
    if args.command == "lora":
        return commands.build_modulation_command(commands.LORA, args.seconds)
    if args.command == "fsk":
        return commands.build_modulation_command(commands.FSK)
    raise ValueError(args.command)


def burst(packet):
    """Frame and modulate one packet, with a little silence before and after."""
    iq = fsk.modulate(fsk.build_frame(packet), SAMPLE_RATE, amplitude=0.5)
    gap = np.zeros(int(SILENCE_S * SAMPLE_RATE), dtype=np.complex64)
    return np.concatenate([gap, iq, gap])


def open_pluto(uri, attenuation_db):
    import adi  # pyadi-iio; imported here so --dry-run works without it

    sdr = adi.Pluto(uri)
    sdr.sample_rate = SAMPLE_RATE
    sdr.tx_rf_bandwidth = RF_BANDWIDTH
    sdr.tx_lo = FREQ_HZ
    sdr.tx_hardwaregain_chan0 = attenuation_db
    sdr.tx_cyclic_buffer = False
    return sdr


def main():
    options = argparse.ArgumentParser(add_help=False)
    options.add_argument("--uri", default="ip:192.168.2.1")
    options.add_argument("--attenuation", type=float, default=-40.0,
                         help="TX gain in dB, 0 (loudest) to -89.75 (quietest)")
    options.add_argument("--repeat", type=int, default=10,
                         help="times to send; the satellite ignores duplicates")
    options.add_argument("--interval", type=float, default=0.5, help="seconds between sends")
    options.add_argument("--dry-run", action="store_true", help="build and self-check only")

    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("state", parents=[options], help="change the satellite's FSM state")
    p.add_argument("state", choices=sorted(commands.STATES))
    p = sub.add_parser("config", parents=[options], help="change the satellite's comms schedule")
    p.add_argument("rx_ticks", type=int)
    p.add_argument("tx_packets", type=int)
    p.add_argument("cadence", type=int)
    p = sub.add_parser("lora", parents=[options], help="open a LoRa window on the satellite")
    p.add_argument("seconds", type=int, nargs="?", default=60)
    sub.add_parser("fsk", parents=[options], help="return the satellite to FSK now")
    args = parser.parse_args()

    if not -89.75 <= args.attenuation <= 0:
        parser.error("--attenuation must be between -89.75 and 0")

    packet = build_packet(args)
    samples = burst(packet)
    decoded = fsk.demodulate(samples, SAMPLE_RATE)
    print("Command bytes:", packet.hex())
    print("Frame bytes:  ", fsk.build_frame(packet).hex())
    print("Self-check:   ", "OK" if decoded == packet else "FAILED")
    if decoded != packet:
        raise SystemExit("Modulated signal did not decode; not transmitting.")
    if commands.load_key() == commands.DEFAULT_KEY:
        print("Note: using the all-zero placeholder AES key (matches the current satellite code).")
    if args.dry_run:
        return

    sdr = open_pluto(args.uri, args.attenuation)
    scaled = samples * 2 ** 14     # Pluto expects samples in the -2^14..2^14 range
    print("Transmitting at %.3f MHz, %.2f dB, %d times..." % (
        FREQ_HZ / 1e6, args.attenuation, args.repeat))
    try:
        for i in range(args.repeat):
            sdr.tx(scaled)
            print("  sent", i + 1)
            time.sleep(args.interval)
    finally:
        sdr.tx_destroy_buffer()
    print("Done.")


if __name__ == "__main__":
    main()
