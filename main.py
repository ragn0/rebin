import argparse
import json
import os
import sys
from typing import List

from lib.core import run_local, run_remote
from lib.replay import replay_session


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="CTF Helper & Test Harness (pwntools)"
    )

    sub = parser.add_subparsers(dest="cmd", required=True)

    p_local = sub.add_parser("run-local", help="Esegui un binario locale")
    p_local.add_argument("binary", help="Percorso al binario locale")
    p_local.add_argument(
        "--args",
        nargs=argparse.REMAINDER,
        help="Argomenti passati al binario dopo --",
        default=[],
    )
    p_local.add_argument(
        "--send",
        action="append",
        help="Linea da inviare al processo (può essere ripetuto)",
        default=[],
    )
    p_local.add_argument(
        "--session-out",
        help="Path file session JSON di output",
        default=None,
    )
    p_local.add_argument("--timeout", type=float, default=5.0)

    p_remote = sub.add_parser("run-remote", help="Connettiti a un servizio remoto")
    p_remote.add_argument("host", help="Host (allowlist: localhost/127.0.0.1 di default)")
    p_remote.add_argument("port", type=int, help="Porta")
    p_remote.add_argument(
        "--send",
        action="append",
        help="Linea da inviare al servizio (può essere ripetuto)",
        default=[],
    )
    p_remote.add_argument(
        "--session-out",
        help="Path file session JSON di output",
        default=None,
    )
    p_remote.add_argument("--timeout", type=float, default=5.0)

    p_replay = sub.add_parser("replay", help="Rigioca una sessione salvata")
    p_replay.add_argument("session", help="Path al file di sessione JSON")
    p_replay.add_argument("--timeout", type=float, default=5.0)

    p_show = sub.add_parser("show-log", help="Mostra un log di sessione")
    p_show.add_argument("session", help="Path al file di sessione JSON")

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.cmd == "run-local":
        session_path = run_local(
            binary=args.binary,
            bin_args=args.args,
            lines_to_send=args.send,
            timeout_s=args.timeout,
            session_out=args.session_out,
        )
        print(session_path)
        return 0

    if args.cmd == "run-remote":
        session_path = run_remote(
            host=args.host,
            port=args.port,
            lines_to_send=args.send,
            timeout_s=args.timeout,
            session_out=args.session_out,
        )
        print(session_path)
        return 0

    if args.cmd == "replay":
        ok = replay_session(args.session, timeout_s=args.timeout)
        print("REPLAY:", "OK" if ok else "FAIL")
        return 0 if ok else 2

    if args.cmd == "show-log":
        with open(args.session, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())


