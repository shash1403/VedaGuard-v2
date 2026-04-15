"""
TestNet e2e: AlgoKit Dispenser + live VedaGuard ``verify_consent`` (Section 9).

These tests are **skipped** unless the documented environment variables are set.
They do not run against LocalNet or the algopy simulator.

Legal intent: proves funding via Dispenser API and a real atomic consent group on TestNet.
"""

from __future__ import annotations

import os
from pathlib import Path

import algokit_utils
import algosdk.logic
import pytest
from algokit_utils import AlgorandClient
from algokit_utils.clients.dispenser_api_client import TestNetDispenserApiClient
from algosdk.atomic_transaction_composer import TransactionWithSigner
from algosdk.transaction import AssetTransferTxn, PaymentTxn

from smart_contracts.artifacts.veda_guard.veda_guard_client import (
    VerifyConsentArgs,
    VedaGuardClient,
)

_ROOT = Path(__file__).resolve().parents[2]

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


_load_env()

_INNER = algokit_utils.CommonAppCallParams(
    max_fee=algokit_utils.AlgoAmount(micro_algo=500_000),
)
_COVER: algokit_utils.SendParams = {"cover_app_call_inner_transaction_fees": True}


def _dispenser_configured() -> bool:
    return bool(os.getenv("ALGOKIT_DISPENSER_ACCESS_TOKEN", "").strip())


def _consent_e2e_configured() -> bool:
    """Requires ``VEDAGUARD_E2E_PRINCIPAL_MNEMONIC`` (AlgoKit naming: ``from_environment('VEDAGUARD_E2E_PRINCIPAL')``)."""
    return all(
        os.getenv(k, "").strip()
        for k in (
            "VEDAGUARD_E2E_APP_ID",
            "VEDAGUARD_E2E_SBT_ID",
            "ALGOKIT_DISPENSER_ACCESS_TOKEN",
            "VEDAGUARD_E2E_PRINCIPAL_MNEMONIC",
        )
    )


def _account_opted_into_asset(algod, address: str, asset_id: int) -> bool:
    try:
        algod.account_asset_info(address, asset_id)
        return True
    except Exception as e:
        err = str(e).lower()
        if "404" in err or "not found" in err or "does not exist" in err:
            return False
        raise


@pytest.mark.e2e
@pytest.mark.skipif(not _dispenser_configured(), reason="ALGOKIT_DISPENSER_ACCESS_TOKEN not set")
def test_dispenser_funds_fresh_account() -> None:
    """AlgoKit Dispenser credits a new random TestNet account (microAlgos balance > 0)."""
    algorand = AlgorandClient.from_environment()
    acct = algorand.account.random()
    dispenser = TestNetDispenserApiClient()
    fund_micro = int(2 * 1_000_000)
    res = dispenser.fund(address=acct.address, amount=fund_micro)
    assert res.tx_id
    info = algorand.client.algod.account_info(acct.address)
    assert int(info["amount"]) >= fund_micro


@pytest.mark.e2e
@pytest.mark.skipif(
    not _consent_e2e_configured(),
    reason="Set VEDAGUARD_E2E_APP_ID, VEDAGUARD_E2E_SBT_ID, "
    "VEDAGUARD_E2E_PRINCIPAL_MNEMONIC, ALGOKIT_DISPENSER_ACCESS_TOKEN",
)
def test_atomic_verify_consent_increments_consent_count() -> None:
    """
    Principal wallet (mnemonic) must match on-chain data principal for ``VEDAGUARD_E2E_SBT_ID``
    and hold the frozen SBT (same as UI / deploy demo).
    """
    algorand = AlgorandClient.from_environment()
    app_id = int(os.environ["VEDAGUARD_E2E_APP_ID"])
    sbt_id = int(os.environ["VEDAGUARD_E2E_SBT_ID"])

    principal = algorand.account.from_environment("VEDAGUARD_E2E_PRINCIPAL")
    algorand.set_signer_from_account(principal)

    dispenser = TestNetDispenserApiClient()
    dispenser.fund(principal.address, int(5 * 1_000_000))

    if not _account_opted_into_asset(algorand.client.algod, principal.address, sbt_id):
        algorand.asset.bulk_opt_in(
            principal.address,
            [sbt_id],
            signer=principal.signer,
            send_params=_COVER,
        )

    app = VedaGuardClient(
        algorand=algorand,
        app_id=app_id,
        default_sender=principal.address,
        default_signer=principal.signer,
    )

    before = app.state.global_state.consent_count
    sp = algorand.get_suggested_params()

    axfer = AssetTransferTxn(
        sender=principal.address,
        sp=sp,
        receiver=principal.address,
        amt=0,
        index=sbt_id,
    )
    hospital_leg = TransactionWithSigner(axfer, principal.signer)

    app_addr = algosdk.logic.get_application_address(app_id)
    pay = PaymentTxn(
        sender=principal.address,
        sp=sp,
        receiver=app_addr,
        amt=0,
    )
    parent_leg = TransactionWithSigner(pay, principal.signer)

    result = app.send.verify_consent(
        args=VerifyConsentArgs(hospital_req=hospital_leg, parent_auth=parent_leg),
        params=_INNER,
        send_params=_COVER,
    )
    assert result.abi_return is True

    after = app.state.global_state.consent_count
    assert after == before + 1, f"consent_count expected {before + 1}, got {after}"
