"""Self-healing knowledge CLI.

In this repository, "self-healing" means:
1. detect inconsistent or duplicated knowledge,
2. write review findings,
3. let a human owner approve any correction.

It intentionally does not scan user-global folders and does not edit source
documents automatically.
"""

from __future__ import annotations

import sys

from auto_grill import main as auto_grill_main


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if not args or args[0].startswith("-"):
        args = ["scan"] + args
    return auto_grill_main(args)


if __name__ == "__main__":
    sys.exit(main())
