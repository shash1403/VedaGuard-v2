"""
Register another minor on an **existing** VedaGuard app (TestNet).

Calls (as **admin** = ``DEPLOYER``):
  1. ``onboard_minor(parent, birth_date, principal_commitment)`` → new SBT ASA id
  2. Opt-in **parent** to that ASA
  3. ``distribute_and_freeze_sbt`` → SBT frozen in parent's wallet

The React dashboard does **not** include a parent-facing onboard flow yet; this is the
supported path for extra minors on the same deployment.

Prerequisites
-------------
- ``vedaguard/.env.testnet`` with TestNet Algod + ``DEPLOYER_MNEMONIC`` (app creator / admin).
- ``DEPLOYER`` must have ALGO for fees.
- ``parent`` must match the guardian wallet that will hold the SBT (often same as deployer).

Usage (from ``vedaguard/``)::

    poetry run python scripts/onboard_minor_existing_app_testnet.py

    poetry run python scripts/onboard_minor_existing_app_testnet.py \\
      --parent 5A4AGOMELMPHQCYHY34VSRHWREINAL6TPBC2K5TEYTHAIBF4H5ZJZVWYEY \\
      --birth-date 1200000000

Then point ``veda-ui/.env`` ``VITE_CONSENT_ASSET_ID`` at the printed **sbt_id** (and sync) if
this wallet should drive **Grant Access** for that child.
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


def _parse_veda_ui_app_id() -> int | None:
    p = _ROOT / "veda-ui" / ".env"
    if not p.is_file():
        return None
    for line in p.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("VITE_VEDAGUARD_APP_ID="):
            v = s.split("=", 1)[1].strip().strip('"').strip("'")
            try:
                return int(v)
            except ValueError:
                return None
    return None


def main() -> None:
    import algokit_utils

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--app-id", type=int, default=None, help="VedaGuard app id (default: veda-ui/.env)")
    ap.add_argument(
        "--parent",
        metavar="ADDR",
        default="",
        help="Guardian / parent Algorand address (default: DEPLOYER address)",
    )
    ap.add_argument(
        "--birth-date",
        type=int,
        default=1_100_000_000,
        help="Unix birth timestamp stored on-chain (default: 1100000000, demo adult)",
    )
    ap.add_argument(
        "--commitment-hex",
        default="",
        help="64 hex chars = 32-byte principal_commitment; default demo pattern if omitted",
    )
    args = ap.parse_args()

    _load_env()

    app_id = args.app_id if args.app_id is not None else _parse_veda_ui_app_id()
    if not app_id:
        raise SystemExit("Set --app-id or VITE_VEDAGUARD_APP_ID in veda-ui/.env")

    algorand = algokit_utils.AlgorandClient.from_environment()
    deployer = algorand.account.from_environment("DEPLOYER")
    parent = args.parent.strip() or deployer.address

    if args.commitment_hex.strip():
        raw = bytes.fromhex(args.commitment_hex.strip())
        if len(raw) != 32:
            raise SystemExit("--commitment-hex must decode to exactly 32 bytes")
        commitment = raw
    else:
        commitment = bytes(range(32))

    _fee = algokit_utils.AlgoAmount(micro_algo=500_000)
    _inner = algokit_utils.CommonAppCallParams(max_fee=_fee)
    _cover: algokit_utils.SendParams = {"cover_app_call_inner_transaction_fees": True}

    from smart_contracts.artifacts.veda_guard.veda_guard_client import (
        DistributeAndFreezeSbtArgs,
        OnboardMinorArgs,
        VedaGuardClient,
    )

    app = VedaGuardClient(
        algorand=algorand,
        app_id=app_id,
        default_sender=deployer.address,
    )

    print(f"app_id={app_id}  parent(guardian)={parent}  birth_date={args.birth_date}")
    r = app.send.onboard_minor(
        args=OnboardMinorArgs(
            parent=parent,
            birth_date=args.birth_date,
            principal_commitment=commitment,
        ),
        params=_inner,
        send_params=_cover,
    )
    sbt_id = int(r.abi_return)
    print(f"Minted SBT ASA id: {sbt_id}")

    algorand.asset.bulk_opt_in(parent, [sbt_id])
    print(f"Opted in {parent[:8]}… to ASA {sbt_id}")

    app.send.distribute_and_freeze_sbt(
        args=DistributeAndFreezeSbtArgs(sbt=sbt_id, holder=parent),
        params=_inner,
        send_params=_cover,
    )
    print("distribute_and_freeze_sbt OK — SBT is in parent wallet (frozen).")
    print()
    print("Next: update veda-ui for this child’s consent card:")
    print(f"  poetry run python scripts/sync_veda_ui_env.py --app-id {app_id} --sbt-id {sbt_id}")


if __name__ == "__main__":
    main()
