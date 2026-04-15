"""
Automate TestNet e2e: Dispenser funding + optional VedaGuard deploy seed + pytest ``e2e``.

Legal intent: single entrypoint for hackathon/CI — no manual copy-paste of app/SBT ids after deploy.

From ``vedaguard/``::

    # Reuse existing app + SBT (set VEDAGUARD_E2E_* in .env.testnet or export):
    poetry run python scripts/run_testnet_e2e.py

    # Full chain: fund deployer → deploy + onboard + SBT → run tests (uses DEPLOYER_MNEMONIC):
    poetry run python scripts/run_testnet_e2e.py --fresh

Pass-through to pytest::

    poetry run python scripts/run_testnet_e2e.py -- -x --tb=long

Requires ``ALGOKIT_DISPENSER_ACCESS_TOKEN`` (``algokit dispenser login --ci``).

**Reuse mode** env: ``VEDAGUARD_E2E_APP_ID``, ``VEDAGUARD_E2E_SBT_ID``,
``VEDAGUARD_E2E_PRINCIPAL_MNEMONIC`` (or ``DEPLOYER_MNEMONIC`` if principal is deployer).

**``--fresh``** env: ``DEPLOYER_MNEMONIC``, Algod settings (e.g. ``ALGOD_SERVER``).
"""

from __future__ import annotations

import argparse
import os
import subprocess
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


def _micro(algo: float) -> int:
    return int(round(algo * 1_000_000))


def _ensure_balance(
    algorand,
    address: str,
    min_micro: int,
    dispenser,
) -> None:
    info = algorand.client.algod.account_info(address)
    bal = int(info["amount"])
    if bal >= min_micro:
        return
    need = min_micro - bal + _micro(0.5)
    print(f"Funding {address[:8]}… (+{need} µALGO via Dispenser)")
    dispenser.fund(address=address, amount=need)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__.split("From ``vedaguard/``::")[0].strip(),
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Run deploy (new/update app + onboard SBT + distribute); sets e2e env from result.",
    )
    parser.add_argument(
        "--min-deployer-algo",
        type=float,
        default=8.0,
        help="Ensure deployer / principal has at least this many ALGO before deploy or pytest.",
    )
    args, pyargs = parser.parse_known_args()

    _load_env()

    if not os.getenv("ALGOKIT_DISPENSER_ACCESS_TOKEN", "").strip():
        raise SystemExit(
            "Set ALGOKIT_DISPENSER_ACCESS_TOKEN (e.g. algokit dispenser login --ci).",
        )

    from algokit_utils import AlgorandClient
    from algokit_utils.clients.dispenser_api_client import TestNetDispenserApiClient

    algorand = AlgorandClient.from_environment()
    dispenser = TestNetDispenserApiClient()
    target_micro = _micro(args.min_deployer_algo)

    if args.fresh:
        deployer = algorand.account.from_environment("DEPLOYER")
        _ensure_balance(algorand, deployer.address, target_micro, dispenser)

        from smart_contracts.veda_guard.deploy_config import deploy as deploy_vedaguard

        print("Running deploy (factory + onboard_minor + distribute_and_freeze_sbt)…")
        app_id, sbt_id = deploy_vedaguard()
        print(f"  app_id={app_id}  sbt_id={sbt_id}")

        dm = os.getenv("DEPLOYER_MNEMONIC", "").strip()
        if not dm:
            raise SystemExit("DEPLOYER_MNEMONIC required for --fresh (principal = deployer).")
        os.environ["VEDAGUARD_E2E_APP_ID"] = str(app_id)
        os.environ["VEDAGUARD_E2E_SBT_ID"] = str(sbt_id)
        os.environ["VEDAGUARD_E2E_PRINCIPAL_MNEMONIC"] = dm

        cache = _ROOT / ".vedaguard_e2e_cache.env"
        cache.write_text(
            "VITE_ALGOD_URL=https://testnet-api.algonode.cloud\n"
            "VITE_ALGOD_TOKEN=\n"
            f"VITE_VEDAGUARD_APP_ID={app_id}\n"
            f"VITE_CONSENT_ASSET_ID={sbt_id}\n",
            encoding="utf-8",
        )
        print(
            f"Wrote UI hints to {cache.name} (gitignored). "
            "Apply to the dashboard: poetry run python scripts/sync_veda_ui_env.py",
        )
    else:
        app_ok = os.getenv("VEDAGUARD_E2E_APP_ID", "").strip()
        sbt_ok = os.getenv("VEDAGUARD_E2E_SBT_ID", "").strip()
        if not app_ok or not sbt_ok:
            raise SystemExit(
                "Missing VEDAGUARD_E2E_APP_ID / VEDAGUARD_E2E_SBT_ID. "
                "Run with --fresh once, or set them in .env.testnet.",
            )
        principal_m = os.getenv("VEDAGUARD_E2E_PRINCIPAL_MNEMONIC", "").strip()
        if not principal_m:
            principal_m = os.getenv("DEPLOYER_MNEMONIC", "").strip()
            if principal_m:
                os.environ["VEDAGUARD_E2E_PRINCIPAL_MNEMONIC"] = principal_m
        if not os.getenv("VEDAGUARD_E2E_PRINCIPAL_MNEMONIC", "").strip():
            raise SystemExit(
                "Set VEDAGUARD_E2E_PRINCIPAL_MNEMONIC (or DEPLOYER_MNEMONIC if same wallet).",
            )

        principal = algorand.account.from_environment("VEDAGUARD_E2E_PRINCIPAL")
        _ensure_balance(algorand, principal.address, target_micro, dispenser)

    forward = list(pyargs[1:]) if pyargs and pyargs[0] == "--" else list(pyargs)
    pytest_args = ["-m", "e2e", "-v", *forward]

    print("Running:", "pytest", "tests/e2e", *pytest_args)
    env = os.environ.copy()
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/e2e", *pytest_args],
        cwd=_ROOT,
        env=env,
    )
    raise SystemExit(r.returncode)


if __name__ == "__main__":
    main()
