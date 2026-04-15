# AlgoBharat

**VedaGuard** — verifiable parental consent for pediatric health data on Algorand — aligned with India’s **DPDP Act** narrative (atomic consent, audit trail, age transition).  
Built for **[AlgoBharat Developer Hub](https://algobharat.in/devportal/)** and hackathon-style **end-to-end** demos: **UI → wallet → atomic group → on-chain confirmation**.

After you push to GitHub, add a CI badge (replace `YOUR_ORG` / `YOUR_REPO`):

`![CI](https://github.com/YOUR_ORG/YOUR_REPO/actions/workflows/ci.yml/badge.svg)`

## Highlights

- **Smart contract (Algorand Python / Puya):** `onboard_minor`, `verify_consent` (atomic **axfer + pay + app call**), `check_age_transition`, DPB-friendly read-only counters.
- **Tests:** `pytest` + `algopy_testing` (no Docker required for unit tests).
- **Frontend:** React, TypeScript, Tailwind, Pera Wallet, live `verify_consent` via `algosdk` `AtomicTransactionComposer`.
- **Tooling:** AlgoKit, LocalNet, ARC-56 artifact, optional [VibeKit](https://www.getvibekit.ai/) for agentic rehearsal ([setup](vedaguard/README.md#vibekit-tick-the-algobharat-agentic-box)).

## Repository layout

```
.
├── README.md                 ← You are here
├── VEDAGUARD.md              ← Product spec, DPDP mapping, AlgoBharat checklist
├── LICENSE
└── vedaguard/                ← AlgoKit project (contracts, tests, deploy, UI)
    ├── README.md             ← Bootstrap, AlgoKit commands, VibeKit
    ├── smart_contracts/
    │   └── veda_guard/       # Contract + deploy_config (not generic "hello_world")
    ├── tests/                # pytest suite
    ├── smart_contracts/artifacts/veda_guard/  # TEAL + ARC-56
    └── veda-ui/              # Parent dashboard SPA
```

## Quick start

### 1. Contracts & tests (Python)

```bash
cd vedaguard
poetry install                    # or: algokit project bootstrap all
poetry run python -m pytest tests/ -v
poetry run algokit project run build
```

### 2. Local chain (optional)

```bash
algokit localnet start
poetry run algokit project deploy localnet
```

### 3. Parent UI

```bash
cd vedaguard/veda-ui
cp .env.example .env            # set VITE_VEDAGUARD_APP_ID, VITE_CONSENT_ASSET_ID, algod URL
npm install
npm run dev
```

See **`vedaguard/README.md`** for AlgoKit details, **`veda-ui/.env.example`** for frontend env vars, and **`VEDAGUARD.md`** for requirements and hub links.

## Security & privacy

- **No raw PII on-chain** — design stores hashes / references only; demo UI uses placeholders.
- **Never commit** real mnemonics or `.env` secrets; use `.env.example` patterns only.

## License

See [LICENSE](LICENSE).

## Contributing

Issues and PRs welcome. Keep changes scoped; match existing AlgoKit / Puya / React patterns. For AlgoBharat submissions, cite **`VEDAGUARD.md`** for DPDP ↔ code mapping.

---
