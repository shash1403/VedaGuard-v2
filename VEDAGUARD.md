# Project Specification: VedaGuard (MVP)

## 1. Objective
To build a functional "Parental Consent Loop" that satisfies Section 9 of the DPDP Act 2025 using the Algorand Blockchain.

## 2. Key Features to Implement by April 15
### Feature A: The Link (Onboarding)
- **Action:** A parent connects their wallet and "registers" a child.
- **Result:** The Smart Contract mints a non-transferable Soul-Bound Token (SBT) to the parent's wallet. The token metadata contains the hashed ID of the child.

### Feature B: The Consent Loop (Atomic Transfer)
- **Step 1:** Hospital (Data Fiduciary) initiates an `AccessRequest` transaction.
- **Step 2:** VedaGuard UI detects the request and prompts the parent for a signature.
- **Step 3:** The Parent signs. Both transactions are sent as an **Atomic Group**.
- **Step 4:** Upon successful settlement, the contract emits a `ConsentLogged` event.

### Feature C: The 18-Year Handoff
- **Trigger:** A smart contract function `claim_adult_status`.
- **Logic:** Compares `Global.latest_timestamp` with the `birth_date` stored in the SBT metadata. If >= 18 years, it transfers the "Master Key" authority to a new wallet address provided by the child.

## 3. Implementation Checklist
- [x] Initialize AlgoKit environment (`vedaguard/` AlgoKit Python project).
- [x] VedaGuard smart contract (`smart_contracts/veda_guard/contract.py`, Algorand Python / Puya).
- [x] Python test suite (`tests/vedaguard_test.py`, `pytest`).
- [x] React + TypeScript frontend (`veda-ui/`) with Pera Wallet and live atomic `verify_consent` submission.
- [x] **VibeKit (AlgoBharat agentic stack)** — Documented one-time setup in [`vedaguard/README.md`](vedaguard/README.md) (`curl … | sh`, `vibekit init`, `vibekit status`). Adds official Algorand skills + MCP for transaction rehearsal in Cursor; run locally to satisfy the Developer Hub checklist (not a runtime dependency of the dApp).

## 4. AlgoBharat Developer Hub (compliance & resources)

This project is aligned with the official **AlgoBharat Developer Hub** guidance for builders and hackathon participants.

| Resource | URL |
|----------|-----|
| **Developer Hub (canonical)** | [https://algobharat.in/devportal/](https://algobharat.in/devportal/) |
| **Hack Series 3.0** | [https://algobharat.in/hack-series3/](https://algobharat.in/hack-series3/) |
| **AlgoKit installation** | Linked from Developer Hub → *Setting Up Your Environment* → AlgoKit |
| **TestNet faucet** | Linked from Developer Hub → *Testnet Faucet* |
| **VibeKit** | Linked from Developer Hub → *Setting Up Your Environment* |
| **Algorand Python (Puya)** | Linked from Developer Hub → *Languages* → Algorand Python |
| **Algorand technical docs** | [https://dev.algorand.co/](https://dev.algorand.co/) |

### Hackathon alignment (from Developer Hub)

- **Lean scope:** One core end-to-end flow — **Parent signs atomic consent group** (DPDP Section 9) with on-chain confirmation; onboarding and age checks support the same narrative.
- **Track fit:** **Digital Personal Data Protection (DPDP) Act and RegTech** (listed under *Core Focus Areas* on the Developer Hub).
- **Tooling:** AlgoKit, Algorand Python, LocalNet/Docker, Pera Wallet, and optional TestNet deploy per hub links.

### Repository map

| Component | Path |
|-----------|------|
| Smart contract (VedaGuard) | `vedaguard/smart_contracts/veda_guard/contract.py` |
| Deploy | `vedaguard/smart_contracts/veda_guard/deploy_config.py` |
| Tests | `vedaguard/tests/vedaguard_test.py` |
| Full-stack UI | `vedaguard/veda-ui/` |
| ARC-56 artifact | `vedaguard/smart_contracts/artifacts/veda_guard/VedaGuard.arc56.json` |

---

## 5. April 15, 2026 submission — panel criteria vs implementation

Use this table when preparing the hack submission and demo script.

### One core feature, full-stack, non-prototype

| Criterion | Status | Evidence in repo |
|-----------|--------|------------------|
| **One polished feature end-to-end** | **Met** | **Atomic parental consent:** UI “Grant Access” builds a real 3-tx group (`axfer` + 0 µALGO `pay` + `verify_consent` app call), Pera signs, algod confirms; `consent_count` updates on-chain. Code: `veda-ui/src/lib/algorand.ts`, `ConsentCard.tsx`, contract `verify_consent`. |
| **UI → Algorand → confirmation** (not clickable fake) | **Met** | `AtomicTransactionComposer` + `waitForConfirmation`; UI shows round + `verify_consent` txid. |
| **Tests / reproducibility** | **Met** | `vedaguard/tests/vedaguard_test.py` — 14 pytest tests including SBT mint/distribute, atomic consent, and age boundary. |
| **CI** | **Met** | `.github/workflows/ci.yml` — pytest, PuyaPy compile, `veda-ui` production build. |

### Panel MVP: SBT issuance + atomic consent

| Ask | Status | Notes |
|-----|--------|--------|
| **Atomic transfer consent mechanism** | **Met** | Enforced in TEAL (`verify_consent`); judges can run tests + Lora + live UI. |
| **SBT issuance (minimal working)** | **Met** | `onboard_minor` submits an inner **`AssetConfig`** (single unit, app-managed roles, **32-byte `metadata_hash` only** — no raw PII). `deploy_config` then **opts the parent in** and calls **`distribute_and_freeze_sbt`** so the SBT sits in the parent wallet **frozen** (non-transferable). Judges: run deploy + set `VITE_CONSENT_ASSET_ID` to that ASA index for the hospital `axfer` leg. |
| **Clarify hospital + parental verification feasibility** | **Partial (document for judges)** | **Current demo:** one wallet signs all three txs (parent + “hospital” leg) so the flow works without a hospital backend. **Narrative for panel:** hospital publishes unsigned `axfer`; backend or dapp groups it with parent `pay` + app call; parent-only signing for payment + app call is the production split. Add 1 slide or README subsection *“Integration: hospital as co-signer on txn 0 only.”* |

### RegTech / DPDP alignment

| Topic | Status |
|-------|--------|
| **Section 9 style consent (atomic)** | Met — enforced by group + TEAL asserts. |
| **Section 2(i) principal (parent / SBT metaphor)** | Met — minted ASA SBT + frozen holder; parent address still passed for off-chain / deploy pairing with `distribute_and_freeze_sbt`. |
| **Section 2(f) age transition** | Met in logic — `check_age_transition` (+ tests). Name differs from spec’s `claim_adult_status`; handoff to child wallet not in MVP scope. |

### Org guidance (Technical Resource Guide, VibeKit)

| Item | Status |
|------|--------|
| **AlgoBharat / Algorand dev resources** | Linked in `README.md`, `VEDAGUARD.md` §4, `veda-ui` footer. |
| **VibeKit** | Documented in `vedaguard/README.md`; optional dev install — not required at runtime. |

### Remaining tasks (pick before demo if time allows)

1. [x] **SBT:** Real **ASA** mint + **freeze** path implemented (`onboard_minor`, `distribute_and_freeze_sbt`, deploy wiring).
2. [ ] **Integration story:** Short **“Hospital integration”** paragraph (API or manual grouping) + diagram in deck or `README`.
3. [ ] **Demo recording:** Screen capture: connect wallet → Grant Access → Pera → confirmed tx + Lora `consent_count`.
4. [ ] **GitHub:** Remote + CI badge + repo description/tags (`algorand`, `algokit`, `dpdp`, `algobharat`).

### Quick verification commands

```bash
cd vedaguard && poetry run python -m pytest tests/ -v
cd vedaguard && poetry run python -m smart_contracts build veda_guard
cd vedaguard/veda-ui && npm run build
```