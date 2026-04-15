# VedaGuard DPDP Readiness Checklist

Last updated: 2026-04-14

This checklist maps VedaGuard's current implementation to practical DPDP readiness controls for a pediatric consent platform.

Status legend:
- Green: Implemented and evidenced in current codebase
- Amber: Partially implemented; policy/process or integration gaps remain
- Red: Not yet implemented

## A. Purpose, Notice, and Lawful Processing

| Control | Status | Current Evidence | Gap / Action |
|---|---|---|---|
| Explicit consent mechanism for pediatric data access | Green | Atomic group flow in `smart_contracts/veda_guard/contract.py` via `verify_consent`; UI submission in `veda-ui/src/lib/algorand.ts` | Keep immutable consent trail exports for audits |
| Purpose limitation metadata | Amber | Technical flow exists, but no structured purpose catalog linked to each consent request | Add purpose code taxonomy and persist per request off-chain |
| Notice transparency to parents/adults | Amber | UX explains consent mechanics; no formal privacy notice + retention disclosure workflow | Add legal notice screens, versioning, and acceptance logs |

## B. Child Data Principal and Guardian Authority

| Control | Status | Current Evidence | Gap / Action |
|---|---|---|---|
| Guardian mapped to child principal | Green | `onboard_minor` stores guardian in SBT registry box in `contract.py` | Ensure onboarding SOP verifies guardian identity off-chain |
| No raw child PII on-chain | Green | `principal_commitment` fixed to 32 bytes, used as `metadata_hash` | Standardize commitment derivation and custody process |
| Admin-controlled onboarding | Green | `assert Txn.sender == self.admin` in onboarding/distribution methods | Move production admin key to multisig/governed signer |

## C. Age Transition and Authority Handoff

| Control | Status | Current Evidence | Gap / Action |
|---|---|---|---|
| 18+ eligibility check | Green | `check_age_transition` and age assertion in `handoff_sbt_to_adult` in `contract.py` | Add monitoring dashboard for upcoming transitions |
| Parent authority revocation after handoff | Green | `verify_consent` resolves principal to `adult_principal` once set | Add runbook for disputed transitions |
| Automatic handoff execution | Amber | Condition is enforced on-chain, but handoff requires explicit call | Add scheduled operational workflow to trigger handoff at due date |

## D. Consent Integrity and Auditability

| Control | Status | Current Evidence | Gap / Action |
|---|---|---|---|
| Atomic consent integrity | Green | Group ordering + zero-payment checks in `verify_consent` | Keep negative-case tests in CI |
| Immutable counters and traceability | Green | `consent_count` and logs in contract; confirmations in UI | Add indexer-backed consent report endpoint |
| Consent withdrawal handling | Red | No explicit withdraw/revoke consent state model | Add revoke method and off-chain enforcement for future requests |

## E. Hospital Governance and Requester Controls

| Control | Status | Current Evidence | Gap / Action |
|---|---|---|---|
| Hospital identity verification on-chain | Amber | Hospital request leg exists, but no hospital allowlist in contract | Add admin-managed hospital registry and enforce sender membership |
| Hospital lifecycle controls (suspend/revoke) | Red | No registration lifecycle methods yet | Add register, suspend, revoke methods + policy controls |
| Purpose-bound hospital request validation | Amber | Request exists technically; purpose code not enforced on-chain/off-chain | Enforce purpose id + policy checks in request workflow |

## F. Security and Key Management

| Control | Status | Current Evidence | Gap / Action |
|---|---|---|---|
| Separation of app roles and SBT controls | Green | App account controls manager/reserve/freeze/clawback for SBT | Add periodic key rotation policy for admin signer |
| Secure secret handling in codebase | Amber | Repo avoids committing sensitive mnemonics; env-based flow documented in `vedaguard/README.md` | Add managed secret store and production incident playbook |
| Least-privilege admin operations | Amber | Admin-only contract gates exist | Implement multisig and dual-control approval process |

 

## Practical conclusion

VedaGuard is strong on cryptographic consent enforcement, guardian-to-adult principal transition logic, and on-chain minimization of child identity data.  
For production-grade DPDP readiness, the main gaps are governance and operational controls around hospitals, rights handling, breach management, and formal legal accountability artifacts.
