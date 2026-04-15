"""
VedaGuard Smart Contract - Test Suite
======================================

Validates the three legal pillars of DPDP Act 2025 compliance:
  1. Section 2(i) - SBT-based Data Principal onboarding
  2. Section 9(1) - Atomic Consent Loop (success & failure)
  3. Section 2(f) - 18-year age transition handoff
"""

import algosdk.logic
import pytest
from algopy import Account, Asset, Bytes, UInt64
from algopy_testing import algopy_testing_context

from smart_contracts.veda_guard.contract import VedaGuard

# Hash-sized commitment placeholder for tests (no real PII).
PRINCIPAL_COMMITMENT = Bytes(bytes(range(32)))


# --------------------------------------------------------------------------- #
#  Section 2(i): Onboarding / SBT Minting                                     #
# --------------------------------------------------------------------------- #


class TestOnboardMinor:
    """Validates that only the admin can register a minor and receive an SBT ID."""

    def test_onboard_minor_success(self) -> None:
        with algopy_testing_context() as ctx:
            contract = VedaGuard()
            parent = ctx.any.account()

            birth_date = UInt64(1_100_000_000)

            sbt_id = contract.onboard_minor(parent, birth_date, PRINCIPAL_COMMITMENT)
            assert sbt_id > UInt64(0)
            assert contract.minor_count == UInt64(1)

    def test_onboard_multiple_minors_increments(self) -> None:
        with algopy_testing_context() as ctx:
            contract = VedaGuard()
            parent = ctx.any.account()

            sbt1 = contract.onboard_minor(parent, UInt64(1_000_000_000), PRINCIPAL_COMMITMENT)
            c2 = Bytes(bytes([i ^ 0xFF for i in range(32)]))
            sbt2 = contract.onboard_minor(parent, UInt64(1_100_000_000), c2)

            assert sbt1 != sbt2
            assert contract.minor_count == UInt64(2)

    def test_onboard_minor_rejects_non_admin(self) -> None:
        with algopy_testing_context() as ctx:
            contract = VedaGuard()
            parent = ctx.any.account()
            non_admin = ctx.any.account()

            with ctx.txn.create_group(active_txn_overrides={"sender": non_admin}):
                with pytest.raises(AssertionError, match="Only admin can onboard"):
                    contract.onboard_minor(parent, UInt64(1_100_000_000), PRINCIPAL_COMMITMENT)

    def test_onboard_minor_rejects_zero_birthdate(self) -> None:
        with algopy_testing_context() as ctx:
            contract = VedaGuard()
            parent = ctx.any.account()

            with pytest.raises(AssertionError, match="Birth date must be positive"):
                contract.onboard_minor(parent, UInt64(0), PRINCIPAL_COMMITMENT)

    def test_onboard_minor_rejects_bad_commitment_length(self) -> None:
        with algopy_testing_context() as ctx:
            contract = VedaGuard()
            parent = ctx.any.account()

            bad = Bytes(b"short")
            with pytest.raises(AssertionError, match="principal_commitment must be 32 bytes"):
                contract.onboard_minor(parent, UInt64(1_100_000_000), bad)


class TestDistributeSbt:
    """Holder must opt in before distribute_and_freeze_sbt (enforced on-chain on real nets)."""

    def test_distribute_and_freeze_sbt_from_admin(self) -> None:
        with algopy_testing_context() as ctx:
            contract = VedaGuard()
            holder = ctx.any.account()

            sbt_id = contract.onboard_minor(holder, UInt64(1_100_000_000), PRINCIPAL_COMMITMENT)
            sbt = Asset(sbt_id)

            app_addr_str = algosdk.logic.get_application_address(int(contract.__app_id__))
            app_addr = Account(app_addr_str)
            ctx.ledger.update_asset_holdings(sbt, app_addr, balance=1)

            # Opt-in + zero balance on holder; xfer delivers the single unit.
            ctx.ledger.update_asset_holdings(sbt, holder, balance=0)

            contract.distribute_and_freeze_sbt(sbt, holder)


# --------------------------------------------------------------------------- #
#  Section 9(1): Atomic Consent Loop                                           #
# --------------------------------------------------------------------------- #


class TestAtomicConsentLoop:
    """
    Validates the Atomic Consent Loop. The critical insight:
      If the parent doesn't sign, the hospital request is
      *mathematically impossible* to execute.
    """

    def test_consent_success_atomic_group(self) -> None:
        """
        Happy path: Hospital sends AssetTransfer (Txn 0), Parent co-signs
        a zero-ALGO Payment (Txn 1). Both in an Atomic Group -> consent verified.
        """
        with algopy_testing_context() as ctx:
            contract = VedaGuard()
            hospital = ctx.any.account()
            parent = ctx.any.account()

            hospital_req = ctx.any.txn.asset_transfer(
                sender=hospital,
                asset_receiver=ctx.any.account(),
                xfer_asset=ctx.any.asset(),
                asset_amount=UInt64(0),
            )

            parent_auth = ctx.any.txn.payment(
                sender=parent,
                receiver=ctx.default_sender,
                amount=UInt64(0),
            )

            deferred = ctx.txn.defer_app_call(
                contract.verify_consent,
                hospital_req,
                parent_auth,
            )

            with ctx.txn.create_group(
                gtxns=[hospital_req, parent_auth, deferred],
            ):
                result = deferred.submit()

            assert result.native is True
            assert contract.consent_count == UInt64(1)

    def test_consent_rejects_nonzero_payment(self) -> None:
        """
        Failure path: Parent payment carries a non-zero amount.
        Contract must reject - consent cannot involve payment.
        """
        with algopy_testing_context() as ctx:
            contract = VedaGuard()
            hospital = ctx.any.account()
            parent = ctx.any.account()

            hospital_req = ctx.any.txn.asset_transfer(
                sender=hospital,
                asset_receiver=ctx.any.account(),
                xfer_asset=ctx.any.asset(),
                asset_amount=UInt64(0),
            )

            parent_auth = ctx.any.txn.payment(
                sender=parent,
                receiver=ctx.default_sender,
                amount=UInt64(1_000_000),  # 1 ALGO - this should fail
            )

            deferred = ctx.txn.defer_app_call(
                contract.verify_consent,
                hospital_req,
                parent_auth,
            )

            with ctx.txn.create_group(
                gtxns=[hospital_req, parent_auth, deferred],
            ):
                with pytest.raises(AssertionError, match="Consent must be free"):
                    deferred.submit()

    def test_consent_count_increments(self) -> None:
        """Multiple successful consent events accumulate in the audit counter."""
        with algopy_testing_context() as ctx:
            contract = VedaGuard()

            for _ in range(3):
                hospital_req = ctx.any.txn.asset_transfer(
                    sender=ctx.any.account(),
                    asset_receiver=ctx.any.account(),
                    xfer_asset=ctx.any.asset(),
                    asset_amount=UInt64(0),
                )
                parent_auth = ctx.any.txn.payment(
                    sender=ctx.any.account(),
                    receiver=ctx.default_sender,
                    amount=UInt64(0),
                )
                deferred = ctx.txn.defer_app_call(
                    contract.verify_consent,
                    hospital_req,
                    parent_auth,
                )
                with ctx.txn.create_group(
                    gtxns=[hospital_req, parent_auth, deferred],
                ):
                    deferred.submit()

            assert contract.consent_count == UInt64(3)

    def test_consent_registered_sbt_requires_guardian_signer(self) -> None:
        """If hospital axfer references a minted SBT, parent_auth must be the guardian."""
        with algopy_testing_context() as ctx:
            contract = VedaGuard()
            guardian = ctx.any.account()
            stranger = ctx.any.account()
            hospital = ctx.any.account()

            birth = UInt64(1_000_000_000)
            sbt_id = contract.onboard_minor(guardian, birth, PRINCIPAL_COMMITMENT)
            sbt = Asset(sbt_id)
            app_addr_str = algosdk.logic.get_application_address(int(contract.__app_id__))
            app_addr = Account(app_addr_str)
            ctx.ledger.update_asset_holdings(sbt, app_addr, balance=1)
            ctx.ledger.update_asset_holdings(sbt, guardian, balance=0)
            contract.distribute_and_freeze_sbt(sbt, guardian)

            hospital_req = ctx.any.txn.asset_transfer(
                sender=hospital,
                asset_receiver=hospital,
                xfer_asset=sbt,
                asset_amount=UInt64(0),
            )
            bad_pay = ctx.any.txn.payment(
                sender=stranger,
                receiver=ctx.default_sender,
                amount=UInt64(0),
            )
            deferred_bad = ctx.txn.defer_app_call(
                contract.verify_consent,
                hospital_req,
                bad_pay,
            )
            with ctx.txn.create_group(
                gtxns=[hospital_req, bad_pay, deferred_bad],
            ):
                with pytest.raises(AssertionError, match="current data principal"):
                    deferred_bad.submit()

            hospital_req2 = ctx.any.txn.asset_transfer(
                sender=hospital,
                asset_receiver=hospital,
                xfer_asset=sbt,
                asset_amount=UInt64(0),
            )
            good_pay = ctx.any.txn.payment(
                sender=guardian,
                receiver=ctx.default_sender,
                amount=UInt64(0),
            )
            deferred_ok = ctx.txn.defer_app_call(
                contract.verify_consent,
                hospital_req2,
                good_pay,
            )
            with ctx.txn.create_group(
                gtxns=[hospital_req2, good_pay, deferred_ok],
            ):
                assert deferred_ok.submit().native is True


# --------------------------------------------------------------------------- #
#  Section 2(f): 18-Year Age Transition                                        #
# --------------------------------------------------------------------------- #


class TestAgeTransition:
    """Validates the time-locked authority handoff at age 18."""

    def test_minor_still_under_18(self) -> None:
        """
        Simulates a child born recently. Global timestamp is near their
        birth -> they are still a minor -> parent retains authority.
        """
        with algopy_testing_context() as ctx:
            contract = VedaGuard()
            birth_date = UInt64(1_700_000_000)  # ~Nov 2023

            ctx.ledger.patch_global_fields(latest_timestamp=UInt64(1_730_000_000))

            result = contract.check_age_transition(birth_date)
            assert result.native is False

    def test_minor_has_turned_18(self) -> None:
        """
        Simulates a child born in 2004. Global timestamp is 2024 ->
        child is ~20 -> authority handoff required.
        """
        with algopy_testing_context() as ctx:
            contract = VedaGuard()
            birth_date = UInt64(1_100_000_000)  # ~Nov 2004

            ctx.ledger.patch_global_fields(latest_timestamp=UInt64(1_700_000_000))

            result = contract.check_age_transition(birth_date)
            assert result.native is True

    def test_exact_18th_birthday_boundary(self) -> None:
        """Edge case: timestamp is exactly 18 years after birth."""
        with algopy_testing_context() as ctx:
            contract = VedaGuard()
            birth_date = UInt64(1_000_000_000)
            eighteen_years = UInt64(567_648_000)
            exact_boundary = birth_date + eighteen_years

            ctx.ledger.patch_global_fields(latest_timestamp=exact_boundary)

            result = contract.check_age_transition(birth_date)
            assert result.native is True  # >= boundary -> adult

    def test_handoff_moves_principal_and_sbt(self) -> None:
        """After 18+, admin can hand off SBT to adult; consent then needs adult signer."""
        with algopy_testing_context() as ctx:
            contract = VedaGuard()
            guardian = ctx.any.account()
            adult = ctx.any.account()
            hospital = ctx.any.account()

            birth = UInt64(1_000_000_000)
            ctx.ledger.patch_global_fields(latest_timestamp=UInt64(2_000_000_000))

            sbt_id = contract.onboard_minor(guardian, birth, PRINCIPAL_COMMITMENT)
            sbt = Asset(sbt_id)
            app_addr_str = algosdk.logic.get_application_address(int(contract.__app_id__))
            app_addr = Account(app_addr_str)
            ctx.ledger.update_asset_holdings(sbt, app_addr, balance=1)
            ctx.ledger.update_asset_holdings(sbt, guardian, balance=0)
            contract.distribute_and_freeze_sbt(sbt, guardian)

            ctx.ledger.update_asset_holdings(sbt, adult, balance=0)
            contract.handoff_sbt_to_adult(sbt, adult)

            rec = contract.get_sbt_principal_record(sbt)
            assert rec.adult_principal.native == adult

            hospital_req = ctx.any.txn.asset_transfer(
                sender=hospital,
                asset_receiver=hospital,
                xfer_asset=sbt,
                asset_amount=UInt64(0),
            )
            guardian_pay = ctx.any.txn.payment(
                sender=guardian,
                receiver=ctx.default_sender,
                amount=UInt64(0),
            )
            deferred_bad = ctx.txn.defer_app_call(
                contract.verify_consent,
                hospital_req,
                guardian_pay,
            )
            with ctx.txn.create_group(
                gtxns=[hospital_req, guardian_pay, deferred_bad],
            ):
                with pytest.raises(AssertionError, match="current data principal"):
                    deferred_bad.submit()

            hospital_req2 = ctx.any.txn.asset_transfer(
                sender=hospital,
                asset_receiver=hospital,
                xfer_asset=sbt,
                asset_amount=UInt64(0),
            )
            adult_pay = ctx.any.txn.payment(
                sender=adult,
                receiver=ctx.default_sender,
                amount=UInt64(0),
            )
            deferred_ok = ctx.txn.defer_app_call(
                contract.verify_consent,
                hospital_req2,
                adult_pay,
            )
            with ctx.txn.create_group(
                gtxns=[hospital_req2, adult_pay, deferred_ok],
            ):
                assert deferred_ok.submit().native is True


# --------------------------------------------------------------------------- #
#  DPB Audit: Read-Only Accessors                                             #
# --------------------------------------------------------------------------- #


class TestAuditAccessors:
    """Validates the read-only counters used for Data Protection Board audits."""

    def test_initial_counts_are_zero(self) -> None:
        with algopy_testing_context() as ctx:
            contract = VedaGuard()
            assert contract.get_consent_count() == UInt64(0)
            assert contract.get_minor_count() == UInt64(0)

    def test_minor_count_after_onboarding(self) -> None:
        with algopy_testing_context() as ctx:
            contract = VedaGuard()
            parent = ctx.any.account()

            c2 = Bytes(bytes([0xAB] * 32))
            contract.onboard_minor(parent, UInt64(1_100_000_000), PRINCIPAL_COMMITMENT)
            contract.onboard_minor(parent, UInt64(1_200_000_000), c2)

            assert contract.get_minor_count() == UInt64(2)
