from __future__ import annotations

import argparse
import sys
from pathlib import Path

from guif.host_gateway import DEFAULT_MAX_BODY_BYTES, serve_gateway


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="guif-gateway",
        description="Run the authenticated GUIF Production Host Gateway",
    )
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--max-body-mb",
        type=int,
        default=DEFAULT_MAX_BODY_BYTES // (1024 * 1024),
        help="Maximum callback body size in MiB",
    )
    parser.add_argument(
        "--allow-remote",
        action="store_true",
        help="Allow a non-loopback bind; requires --tls-cert and --tls-key",
    )
    parser.add_argument("--tls-cert", type=Path)
    parser.add_argument("--tls-key", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.max_body_mb < 1 or args.max_body_mb > 1024:
        print("ERROR: --max-body-mb must be between 1 and 1024", file=sys.stderr)
        return 2
    try:
        serve_gateway(
            args.workspace.resolve(),
            host=args.host,
            port=args.port,
            max_body_bytes=args.max_body_mb * 1024 * 1024,
            allow_remote=args.allow_remote,
            tls_cert=args.tls_cert.resolve() if args.tls_cert else None,
            tls_key=args.tls_key.resolve() if args.tls_key else None,
        )
    except (FileNotFoundError, RuntimeError, ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
