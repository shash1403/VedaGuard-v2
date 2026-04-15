"""
Opt the **child / adult** account into the VedaGuard SBT on TestNet (signed by that account).

Use when Pera opt-in is awkward and preflight reports:
``Child … has no indexer row for ASA … — opt in Pera first``.

Prerequisites
-------------
1. ``vedaguard/.env.testnet`` with TestNet ``ALGOD_SERVER`` and::

       HANDOFF_CHILD_MNEMONIC="25 words for the child wallet (must match the address you pass to UI handoff)"

2. That account funded with a little TestNet ALGO (fee + min balance).

3. SBT ASA id: from ``veda-ui/.env`` ``VITE_CONSENT_ASSET_ID`` or ``--sbt-id``.

Run from ``vedaguard/``::

    poetry run python scripts/opt_in_child_to_sbt_testnet.py

    poetry run python scripts/opt_in_child_to_sbt_testnet.py --sbt-id 758774204
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


def _load_env() -> None:
    if load_dotenv is None:
        return
    for name in (".env.testnet", ".env"):
        p = _ROOT / name
        if p.is_file():
            load_dotenv(p)


def _parse_veda_ui_sbt() -> int | None:
    p = _ROOT / "veda-ui" / ".env"
    if not p.is_file():
        return None
    for line in p.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("VITE_CONSENT_ASSET_ID="):
            v = s.split("=", 1)[1].strip().strip('"').strip("'")
            try:
                return int(v)
            except ValueError:
                return None
    return None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sbt-id", type=int, default=None, help="ASA id (default: veda-ui/.env)")
    args = ap.parse_args()

    _load_env()

    if not os.environ.get("HANDOFF_CHILD_MNEMONIC", "").strip():
        raise SystemExit(
            "Set HANDOFF_CHILD_MNEMONIC in .env.testnet (25-word mnemonic for the child/adult wallet).",
        )

    sbt_id = args.sbt_id
    if sbt_id is None:
        parsed = _parse_veda_ui_sbt()
        if parsed is None:
            raise SystemExit("Pass --sbt-id or set VITE_CONSENT_ASSET_ID in veda-ui/.env")
        sbt_id = parsed

    from algokit_utils import AlgorandClient

    algorand = AlgorandClient.from_environment()
    child = algorand.account.from_environment("HANDOFF_CHILD")

    print(f"Child address: {child.address}")
    print(f"Opting in to ASA {sbt_id} …")
    algorand.asset.bulk_opt_in(child.address, [sbt_id])
    print("OK. Re-run: poetry run python scripts/demo_preflight_testnet.py --child", child.address)


if __name__ == "__main__":
    main()
