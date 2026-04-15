import logging

import algokit_utils

logger = logging.getLogger(__name__)

# onboard_minor / distribute use ensure_budget + inner ASAs; AlgoKit simulate needs an
# explicit fee ceiling and inner-fee coverage or logic fails with "fee too small".
_APP_CALL_MAX_FEE = algokit_utils.AlgoAmount(micro_algo=500_000)
_COVER_INNER_FEES = {"cover_app_call_inner_transaction_fees": True}
_INNER_FEE_APP_CALL = algokit_utils.CommonAppCallParams(max_fee=_APP_CALL_MAX_FEE)


def deploy() -> tuple[int, int]:
    """
    Legal Intent:
      Deploys the VedaGuard consent contract and performs an initial
      onboard_minor call to seed the environment that hospitals will
      interact with during the Atomic Consent Loop.

    Returns:
        ``(app_id, sbt_asa_id)`` for automation (e.g. ``scripts/run_testnet_e2e.py``).
    """
    from smart_contracts.artifacts.veda_guard.veda_guard_client import (
        DistributeAndFreezeSbtArgs,
        OnboardMinorArgs,
        VedaGuardFactory,
    )

    algorand = algokit_utils.AlgorandClient.from_environment()
    deployer = algorand.account.from_environment("DEPLOYER")

    factory = algorand.client.get_typed_app_factory(
        VedaGuardFactory, default_sender=deployer.address
    )

    app_client, result = factory.deploy(
        on_update=algokit_utils.OnUpdate.AppendApp,
        on_schema_break=algokit_utils.OnSchemaBreak.AppendApp,
    )

    if result.operation_performed in [
        algokit_utils.OperationPerformed.Create,
        algokit_utils.OperationPerformed.Replace,
    ]:
        algorand.send.payment(
            algokit_utils.PaymentParams(
                amount=algokit_utils.AlgoAmount(algo=1),
                sender=deployer.address,
                receiver=app_client.app_address,
            )
        )

    parent_account = deployer.address
    demo_birth_date = 1_100_000_000  # ~2004-11-09 (minor is ~21 now → adult)
    # Demo 32-byte hash commitment only (replace with a real hash in production).
    demo_principal_commitment = bytes(range(32))

    response = app_client.send.onboard_minor(
        args=OnboardMinorArgs(
            parent=parent_account,
            birth_date=demo_birth_date,
            principal_commitment=demo_principal_commitment,
        ),
        params=_INNER_FEE_APP_CALL,
        send_params=_COVER_INNER_FEES,
    )
    sbt_id = int(response.abi_return)
    logger.info(
        f"Minted SBT ASA on {app_client.app_name} ({app_client.app_id}), "
        f"asset id: {sbt_id}"
    )

    algorand.asset.bulk_opt_in(parent_account, [sbt_id])
    app_client.send.distribute_and_freeze_sbt(
        args=DistributeAndFreezeSbtArgs(sbt=sbt_id, holder=parent_account),
        params=_INNER_FEE_APP_CALL,
        send_params=_COVER_INNER_FEES,
    )
    logger.info(
        "Transferred SBT to parent and froze holding (soul-bound on this network)."
    )
    return (int(app_client.app_id), int(sbt_id))
