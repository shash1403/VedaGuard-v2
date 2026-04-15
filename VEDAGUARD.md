# Project Specification: VedaGuard (MVP)

## 1. Objective
To build a functional "Parental Consent Loop" that satisfies Section 9 of the DPDP Act 2025 using the Algorand Blockchain.

## 2. Key Features 
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

 

### Quick verification commands

```bash
cd vedaguard && poetry run python -m pytest tests/ -v
cd vedaguard && poetry run python -m smart_contracts build veda_guard
cd vedaguard/veda-ui && npm run build
```
