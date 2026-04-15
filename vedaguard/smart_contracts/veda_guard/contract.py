from algopy import (
    ARC4Contract,
    Account,
    Asset,
    BoxMap,
    Bytes,
    Global,
    GlobalState,
    OpUpFeeSource,
    Txn,
    UInt64,
    arc4,
    ensure_budget,
    gtxn,
    itxn,
    log,
)


class SbtPrincipalRecord(arc4.Struct):
    """
    Legal Intent (Section 2i + 2f):
      Per-SBT registry row: opaque birth timestamp for age checks, guardian
      (parent wallet at onboarding), and adult_principal (filled after handoff).
      Stored in a box keyed by ASA id — no raw PII beyond public addresses.
    """

    birth_ts: arc4.UInt64
    guardian: arc4.Address
    adult_principal: arc4.Address


class VedaGuard(ARC4Contract):
    """
    VedaGuard: DPDP Act 2025 Compliant Pediatric Health Record Consent Manager.

    Legal Intent:
      This contract enforces India's Digital Personal Data Protection Act 2025
      by encoding three core legal requirements directly into AVM bytecode:
        - Section 9(1): Verifiable Parental Consent via Atomic Transfers
        - Section 2(i): Data Principal identity via Soul-Bound Tokens
        - Section 2(f): Age-based authority transition at 18 years
    """

    def __init__(self) -> None:
        self.admin = Global.creator_address
        self.minor_count = UInt64(0)
        self.consent_count = UInt64(0)
        self.sbt_registry = BoxMap(arc4.UInt64, SbtPrincipalRecord, key_prefix=b"vg")

    # ------------------------------------------------------------------ #
    #  Phase A — Onboarding: SBT Minting (Section 2i — Data Principal)   #
    # ------------------------------------------------------------------ #

    @arc4.abimethod()
    def onboard_minor(
        self,
        parent: Account,
        birth_date: UInt64,
        principal_commitment: Bytes,
    ) -> UInt64:
        """
        Legal Intent (Section 2i):
          Mints a single-unit ASA (NFT-style) controlled by this application:
          manager, reserve, freeze, and clawback all point at the app account so
          the protocol can freeze the holder after distribution (soul-bound).

        On-chain storage is limited to a 32-byte ``metadata_hash`` (no raw PII).
        ``birth_date`` is retained only as an opaque unix timestamp for age logic;
        off-chain identity maps to ``principal_commitment`` via hashing.

        A box row is created keyed by the new ASA id with guardian + birth_ts for
        Section 2(f) handoff and consent principal resolution.

        Returns:
          The newly created ASA index (the on-chain SBT id).

        Note:
          The ASA supply starts in the application account. The admin must call
          ``distribute_and_freeze_sbt`` after the holder has opted in.
        """
        assert Txn.sender == self.admin, "Only admin can onboard"
        assert birth_date > UInt64(0), "Birth date must be positive"
        assert principal_commitment.length == UInt64(32), "principal_commitment must be 32 bytes"

        ensure_budget(UInt64(10_000), fee_source=OpUpFeeSource.GroupCredit)

        self.minor_count += UInt64(1)

        app_self = Global.current_application_address
        sbt_id = (
            itxn.AssetConfig(
                total=UInt64(1),
                decimals=UInt64(0),
                default_frozen=False,
                asset_name=Bytes(b"VedaGuard Pediatric SBT"),
                unit_name=Bytes(b"VG-SBT"),
                url=Bytes(b""),
                metadata_hash=principal_commitment,
                manager=app_self,
                reserve=app_self,
                freeze=app_self,
                clawback=app_self,
                fee=UInt64(0),
            )
            .submit()
            .created_asset.id
        )

        zero = arc4.Address(Global.zero_address)
        key = arc4.UInt64(sbt_id)
        row = SbtPrincipalRecord(arc4.UInt64(birth_date), arc4.Address(parent), zero)
        self.sbt_registry[key] = row.copy()

        log(b"ONBOARD: minor registered, SBT ASA created")
        return sbt_id

    @arc4.abimethod()
    def distribute_and_freeze_sbt(self, sbt: Asset, holder: Account) -> None:
        """
        Legal Intent (Section 2i):
          Completes soul-bound issuance: moves the single SBT unit to the holder,
          then freezes that account for this ASA so it cannot be transferred.

        Preconditions:
          ``holder`` must have opted into ``sbt`` before this call; the ASA must
          still hold one unit in the application account. Holder must match the
          guardian address recorded at onboarding for this SBT.
        """
        assert Txn.sender == self.admin, "Only admin can distribute SBT"

        ensure_budget(UInt64(8_000), fee_source=OpUpFeeSource.GroupCredit)

        sbt_key = arc4.UInt64(sbt.id)
        assert sbt_key in self.sbt_registry, "SBT not registered"
        reg = self.sbt_registry[sbt_key].copy()
        assert holder == reg.guardian.native, "Holder must match onboarded guardian"

        itxn.AssetTransfer(
            xfer_asset=sbt,
            asset_amount=UInt64(1),
            asset_receiver=holder,
            fee=UInt64(0),
        ).submit()

        itxn.AssetFreeze(
            freeze_asset=sbt,
            freeze_account=holder,
            frozen=True,
            fee=UInt64(0),
        ).submit()

        log(b"SBT: transferred to holder and frozen (non-transferable)")

    # ------------------------------------------------------------------ #
    #  Phase B — The Atomic Consent Loop (Section 9 — Verifiable Consent) #
    # ------------------------------------------------------------------ #

    @arc4.abimethod()
    def verify_consent(
        self,
        hospital_req: gtxn.AssetTransferTransaction,
        parent_auth: gtxn.PaymentTransaction,
    ) -> arc4.Bool:
        """
        Legal Intent (Section 9(1)):
          Implements 'Verifiable Parental Consent' as an Algorand Atomic Group.

          Txn 0 — hospital_req: The Data Fiduciary (hospital) sends an
                  AssetTransferTransaction referencing the minor's SBT.
          Txn 1 — parent_auth:  The Data Principal (parent) co-signs a
                  zero-ALGO PaymentTransaction as cryptographic proof of
                  consent.

          If the SBT appears in the on-chain registry, parent_auth.sender must be
          the current data principal: guardian before handoff, or adult_principal
          after Section 2(f) handoff.

        Failure Modes:
          - Parent refuses to sign  → entire group is rejected
          - Group ordering violated → assertion fails
          - Non-zero payment amount → assertion fails (consent must be free)
        """
        assert (
            hospital_req.group_index + UInt64(1) == parent_auth.group_index
        ), "Atomic group ordering violation"

        assert parent_auth.amount == UInt64(0), "Consent must be free — no payment"

        axfer_asset = hospital_req.xfer_asset
        sbt_key = arc4.UInt64(axfer_asset.id)
        zero = arc4.Address(Global.zero_address)
        if sbt_key in self.sbt_registry:
            reg = self.sbt_registry[sbt_key].copy()
            if reg.adult_principal == zero:
                principal = reg.guardian.native
            else:
                principal = reg.adult_principal.native
            assert parent_auth.sender == principal, "Signer must be current data principal"

        self.consent_count += UInt64(1)

        log(b"CONSENT: parental consent verified via atomic group")
        return arc4.Bool(True)

    # ------------------------------------------------------------------ #
    #  Phase C — 18-Year Ownership Handoff (Section 2f — Age Transition)  #
    # ------------------------------------------------------------------ #

    @arc4.abimethod()
    def check_age_transition(self, birth_date: UInt64) -> arc4.Bool:
        """
        Legal Intent (Section 2f):
          Determines whether a minor has reached 18 years of age.
          When True, the parent's signing authority must be revoked and
          transferred to the now-adult child's own wallet.

          Prefer ``handoff_sbt_to_adult`` for on-chain principal + SBT relocation
          once the minor is 18.

        Note:
          18 years ≈ 567,648,000 seconds (18 × 365.25 × 24 × 3600).
        """
        seconds_in_18_years = UInt64(567_648_000)
        is_adult = Global.latest_timestamp >= birth_date + seconds_in_18_years

        if is_adult:
            log(b"AGE: minor has turned 18 - authority handoff required")
        else:
            log(b"AGE: minor is still under 18 - parent retains authority")

        return arc4.Bool(is_adult)

    @arc4.abimethod()
    def handoff_sbt_to_adult(self, sbt: Asset, adult: Account) -> None:
        """
        Legal Intent (Section 2f):
          After the minor is 18+, records the child's wallet as adult_principal and
          moves the soul-bound ASA from the guardian to the adult using clawback,
          then re-freezes the adult's holding.

        Authorization: application admin OR the registered guardian.

        Preconditions:
          - Registry row exists; handoff not already done.
          - ``Global.latest_timestamp >= birth_ts + 18 years``.
          - Adult has opted into the SBT.
        """
        ensure_budget(UInt64(16_000), fee_source=OpUpFeeSource.GroupCredit)

        sbt_key = arc4.UInt64(sbt.id)
        assert sbt_key in self.sbt_registry, "SBT not registered"
        reg = self.sbt_registry[sbt_key].copy()
        guardian = reg.guardian.native
        assert Txn.sender == self.admin or Txn.sender == guardian, "Only admin or guardian can initiate handoff"

        zero = arc4.Address(Global.zero_address)
        assert reg.adult_principal == zero, "Handoff already completed"

        seconds_in_18_years = UInt64(567_648_000)
        birth_u = reg.birth_ts.as_uint64()
        assert (
            Global.latest_timestamp >= birth_u + seconds_in_18_years
        ), "Minor not yet 18 — handoff blocked"

        itxn.AssetFreeze(
            freeze_asset=sbt,
            freeze_account=guardian,
            frozen=False,
            fee=UInt64(0),
        ).submit()

        itxn.AssetTransfer(
            xfer_asset=sbt,
            asset_amount=UInt64(1),
            asset_receiver=adult,
            asset_sender=guardian,
            fee=UInt64(0),
        ).submit()

        itxn.AssetFreeze(
            freeze_asset=sbt,
            freeze_account=adult,
            frozen=True,
            fee=UInt64(0),
        ).submit()

        new_row = SbtPrincipalRecord(reg.birth_ts, reg.guardian, arc4.Address(adult))
        self.sbt_registry[sbt_key] = new_row.copy()

        log(b"HANDOFF: adult principal set; SBT re-frozen on child wallet")

    @arc4.abimethod(readonly=True)
    def get_sbt_principal_record(self, sbt: Asset) -> SbtPrincipalRecord:
        """
        Legal Intent (audit / dapp):
          Returns the registry row for an SBT minted by this app, or reverts if
          unknown. Use off-chain to show guardian vs adult principal.
        """
        sbt_key = arc4.UInt64(sbt.id)
        assert sbt_key in self.sbt_registry, "SBT not registered"
        return self.sbt_registry[sbt_key].copy()

    # ------------------------------------------------------------------ #
    #  Read-Only Accessors (for DPB Audit Trail)                          #
    # ------------------------------------------------------------------ #

    @arc4.abimethod(readonly=True)
    def get_consent_count(self) -> UInt64:
        """
        Legal Intent (DPB Audit):
          Returns the total number of verified consent events recorded by
          this contract, providing an immutable audit trail for the Data
          Protection Board.
        """
        return self.consent_count

    @arc4.abimethod(readonly=True)
    def get_minor_count(self) -> UInt64:
        """Returns the total number of minors onboarded."""
        return self.minor_count
