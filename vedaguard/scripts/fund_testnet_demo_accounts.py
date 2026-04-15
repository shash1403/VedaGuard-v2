"""
Fund TestNet ALGO for VedaGuard demo accounts via the AlgoKit Dispenser API.

Legal intent: TestNet-only automation so guardians and child wallets can be
funded without the browser faucet (CI / repeatable demos). No mainnet use.

Prerequisites
-------------
1. Create an access token (one-time)::

       algokit dispenser login --ci

   Export it (do not commit)::

       export ALGOKIT_DISPENSER_ACCESS_TOKEN="..."

   Or add ``ALGOKIT_DISPENSER_ACCESS_TOKEN`` to ``.env.testnet`` (gitignored).

2. Run from ``vedaguard/``::

       poetry run python scripts/fund_testnet_demo_accounts.py

   Optional: fund existing Pera addresses instead of generating new keys::

       poetry run python scripts/fund_testnet_demo_accounts.py \\
         --guardian-address ADDR1 --child-address ADDR2

Amounts are in **whole ALGO** (converted to microAlgos for the API). The
dispenser enforces per-token limits; reduce ``--algo-per-account`` if the API
returns a limit error.

Reference: https://dev.algorand.co/concepts/accounts/funding/
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from algokit_utils import AlgorandClient
from algokit_utils.clients.dispenser_api_client import TestNetDispenserApiClient
import algosdk.mnemonic

_ROOT = Path(__file__).resolve().parents[1]

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


def _micro_algo_from_whole(algo: float) -> int:
    if algo <= 0:
        raise SystemExit("--algo-per-account must be positive")
    return int(round(algo * 1_000_000))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("Prerequisites")[0].strip())
    parser.add_argument(
        "--algo-per-account",
        type=float,
        default=5.0,
        help="Whole ALGO to request per account from the dispenser (default: 5).",
    )
    parser.add_argument(
        "--guardian-address",
        metavar="ADDR",
        default="",
        help="If set with --child-address, fund these addresses only (no new keys).",
    )
    parser.add_argument(
        "--child-address",
        metavar="ADDR",
        default="",
        help="Second address when using --guardian-address.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate accounts and print mnemonics only; do not call the dispenser.",
    )
    args = parser.parse_args()

    _load_env()

    if not args.dry_run and not os.environ.get("ALGOKIT_DISPENSER_ACCESS_TOKEN"):
        raise SystemExit(
            "Set ALGOKIT_DISPENSER_ACCESS_TOKEN (e.g. from `algokit dispenser login --ci`) "
            "or add it to .env.testnet. Use --dry-run to only generate keys."
        )

    g_addr = args.guardian_address.strip()
    c_addr = args.child_address.strip()
    if (g_addr or c_addr) and not (g_addr and c_addr):
        raise SystemExit("Provide both --guardian-address and --child-address, or neither.")

    amount_micro = _micro_algo_from_whole(args.algo_per_account)

    client = AlgorandClient.testnet()

    if g_addr and c_addr:
        guardian_addr, child_addr = g_addr, c_addr
        print("Using existing addresses (no mnemonics printed).")
        print(f"  Guardian: {guardian_addr}")
        print(f"  Child:    {child_addr}")
    else:
        g_acct = client.account.random()
        c_acct = client.account.random()
        guardian_addr = g_acct.address
        child_addr = c_acct.address
        g_phrase = algosdk.mnemonic.from_private_key(g_acct.private_key)
        c_phrase = algosdk.mnemonic.from_private_key(c_acct.private_key)

        print("Generated two TestNet accounts — store mnemonics offline; never commit them.")
        print()
        print("Guardian / parent (connect in Pera on TestNet, import with mnemonic):")
        print(f"  Address:   {guardian_addr}")
        print(f"  Mnemonic:  {g_phrase}")
        print()
        print("Adult child (second Pera account):")
        print(f"  Address:   {child_addr}")
        print(f"  Mnemonic:  {c_phrase}")
        print()

    if args.dry_run:
        print("--dry-run: skipping dispenser funding.")
        return

    dispenser = TestNetDispenserApiClient()
    for label, addr in (("Guardian", guardian_addr), ("Child", child_addr)):
        try:
            res = dispenser.fund(address=addr, amount=amount_micro)
            print(
                f"Funded {label} {addr[:8]}… with {res.amount} µALGO (tx {res.tx_id}).",
            )
        except Exception as e:
            raise SystemExit(f"Dispenser failed for {label} ({addr}): {e}") from e

    print()
    print("Next: import mnemonics into Pera (TestNet), or use addresses above with your dapp.")


if __name__ == "__main__":
    main()
