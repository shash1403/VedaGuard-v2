"""
TestNet demo: opt the *adult child* into the SBT, then call ``handoff_sbt_to_adult``.

Legal intent (Section 2f): exercises on-chain relocation + registry update so
``verify_consent`` must be signed by the child afterward.

Prerequisites
-------------
1. Deploy a **current** VedaGuard build (with ``handoff_sbt_to_adult``) on TestNet.
2. An SBT already **onboarded** and **distributed** to the guardian (e.g. deploy script).
3. ``birth_ts`` stored at onboard must be at least ~18 years before **current block time**
   (deploy_config demo uses ~2004 — fine on TestNet in 2026).
4. ``.env.testnet`` (or env) with Algod + ``DEPLOYER_MNEMONIC`` (must be the **guardian**
   holding the frozen SBT).
5. A second account: set ``HANDOFF_CHILD_MNEMONIC`` (25 words). Fund it on TestNet and
   keep the mnemonic secret.

Run from ``vedaguard/``::

    export HANDOFF_CHILD_MNEMONIC="twenty five words ..."
    poetry run python scripts/handoff_testnet_demo.py --app-id YOUR_APP_ID --sbt-id YOUR_ASA_ID

AlgoKit loads ``.env.testnet`` when variables are set; you can also ``source`` or export
``ALGOD_SERVER``, ``DEPLOYER_MNEMONIC``, etc. yourself.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

# Project root on sys.path (script lives in scripts/)
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import algokit_utils

logging.basicConfig(level=logging.INFO)
_LOG = logging.getLogger("handoff_demo")

_INNER = algokit_utils.CommonAppCallParams(
    max_fee=algokit_utils.AlgoAmount(micro_algo=500_000),
)
_COVER: algokit_utils.SendParams = {
    "cover_app_call_inner_transaction_fees": True,
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("Prerequisites")[0].strip())
    parser.add_argument("--app-id", type=int, required=True)
    parser.add_argument("--sbt-id", type=int, required=True)
    parser.add_argument(
        "--fund-child-algo",
        type=float,
        default=0.0,
        help="If > 0, send this many ALGO from deployer to child before opt-in (for fees/MBR).",
    )
    args = parser.parse_args()

    if not os.environ.get("HANDOFF_CHILD_MNEMONIC"):
        raise SystemExit(
            "Set HANDOFF_CHILD_MNEMONIC (25-word TestNet account for the adult child)."
        )

    algorand = algokit_utils.AlgorandClient.from_environment()
    guardian = algorand.account.from_environment("DEPLOYER")
    child = algorand.account.from_environment("HANDOFF_CHILD")

    from smart_contracts.artifacts.veda_guard.veda_guard_client import (
        GetSbtPrincipalRecordArgs,
        HandoffSbtToAdultArgs,
        VedaGuardClient,
    )

    if args.fund_child_algo > 0:
        algorand.send.payment(
            algokit_utils.PaymentParams(
                sender=guardian.address,
                receiver=child.address,
                amount=algokit_utils.AlgoAmount(algo=args.fund_child_algo),
            )
        )
        _LOG.info("Funded child with %s ALGO", args.fund_child_algo)

    app = VedaGuardClient(
        algorand=algorand,
        app_id=args.app_id,
        default_sender=guardian.address,
    )

    _LOG.info("Opting child %s into ASA %s", child.address, args.sbt_id)
    algorand.asset.bulk_opt_in(child.address, [args.sbt_id])

    _LOG.info("Calling handoff_sbt_to_adult (signer: guardian/deployer)")
    app.send.handoff_sbt_to_adult(
        args=HandoffSbtToAdultArgs(sbt=args.sbt_id, adult=child.address),
        params=_INNER,
        send_params=_COVER,
    )

    rec = app.send.get_sbt_principal_record(
        args=GetSbtPrincipalRecordArgs(sbt=args.sbt_id),
        params=_INNER,
        send_params=_COVER,
    )
    row = rec.abi_return
    _LOG.info(
        "Registry after handoff: birth_ts=%s guardian=%s adult_principal=%s",
        row.birth_ts,
        row.guardian,
        row.adult_principal,
    )
    if str(row.adult_principal) != child.address:
        raise SystemExit("Unexpected adult_principal in box vs child address")
    print("OK: SBT moved to child, adult_principal matches HANDOFF_CHILD address.")


if __name__ == "__main__":
    main()
