"""Minimal operator CLI for bootstrap diagnostics."""

import argparse
import json

from packages.foundation.settings import get_settings


def main() -> None:
    parser = argparse.ArgumentParser(prog="narratopro")
    parser.add_argument("command", choices=["doctor", "settings"])
    args = parser.parse_args()
    settings = get_settings()
    if args.command == "doctor":
        print("NarratoPro bootstrap is healthy")
    else:
        print(json.dumps(settings.public_summary(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
