import { useCallback, useMemo, useState } from "react";
import algosdk from "algosdk";
import type { PeraWalletConnect } from "@perawallet/connect";
import {
  createAlgodClient,
  submitAssetOptIn,
  submitDistributeAndFreezeSbt,
  submitOnboardMinor,
} from "../lib/algorand";
import { makePeraWalletSigner } from "../lib/peraSigner";
import { getVedaGuardEnv } from "../lib/config";
import { vgError, vgInfo } from "../lib/vedaGuardLog";

interface AdminConsoleProps {
  /** Must equal application creator (on-chain admin). */
  adminAddress: string;
  connectedAddress: string;
  peraWallet: InstanceType<typeof PeraWalletConnect>;
  /** After mint / distribute, parent dashboard stats can refresh. */
  onChainUpdated?: () => void;
}

/** 32-byte sample pattern for metadata_hash — not PII. */
function samplePrincipalCommitmentHex(): string {
  return Array.from({ length: 32 }, (_, i) => i.toString(16).padStart(2, "0")).join("");
}

function parseCommitmentHex(hex: string): Uint8Array {
  const s = hex.replace(/\s+/g, "");
  if (!/^[0-9a-fA-F]{64}$/.test(s)) {
    throw new Error("Commitment must be 64 hexadecimal characters (32 bytes).");
  }
  return Uint8Array.from(s.match(/.{2}/g)!.map((b) => parseInt(b, 16)));
}

/**
 * Legal intent: admin surface for Section 2i onboarding — mint, opt-in, distribute.
 * Production should use audited workflows and real principal hashes off-chain.
 */
export function AdminConsole({
  adminAddress,
  connectedAddress,
  peraWallet,
  onChainUpdated,
}: AdminConsoleProps) {
  const env = getVedaGuardEnv();
  const client = useMemo(() => createAlgodClient(env), [env]);

  const [parentAddr, setParentAddr] = useState(connectedAddress);
  const [birthUnix, setBirthUnix] = useState("1100000000");
  const [commitmentHex, setCommitmentHex] = useState(samplePrincipalCommitmentHex);

  const [mintedSbt, setMintedSbt] = useState<number | null>(null);
  const [guardianAtMint, setGuardianAtMint] = useState<string | null>(null);
  const [phase, setPhase] = useState<
    "idle" | "minting" | "opting" | "distributing"
  >("idle");
  const [error, setError] = useState<string | null>(null);
  const [lastTx, setLastTx] = useState<string | null>(null);

  const adminSigner = useCallback(
    (purpose: string) => makePeraWalletSigner(peraWallet, adminAddress, purpose),
    [peraWallet, adminAddress],
  );

  const guardianSigner = useCallback(
    (guardian: string, purpose: string) =>
      makePeraWalletSigner(peraWallet, guardian, purpose),
    [peraWallet],
  );

  const runMint = useCallback(async () => {
    setError(null);
    setLastTx(null);
    const birth = BigInt(birthUnix.trim() || "0");
    if (birth <= 0n) {
      setError("Birth date must be a positive Unix timestamp.");
      return;
    }
    if (!algosdk.isValidAddress(parentAddr.trim())) {
      setError("Enter a valid guardian Algorand address.");
      return;
    }
    let commitment: Uint8Array;
    try {
      commitment = parseCommitmentHex(commitmentHex);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      return;
    }
    const guardian = parentAddr.trim();
    setPhase("minting");
    vgInfo("AdminConsole", "Mint minor (onboard_minor)", { guardian });
    try {
      const signer = adminSigner(
        "VedaGuard Admin: onboard_minor — mint SBT + registry, Section 2i",
      );
      const r = await submitOnboardMinor(
        client,
        signer,
        adminAddress,
        guardian,
        birth,
        commitment,
        env,
      );
      setMintedSbt(r.sbtAssetId);
      setGuardianAtMint(guardian);
      setLastTx(r.txIDs[0] ?? null);
      onChainUpdated?.();
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
      vgError("AdminConsole", "onboard_minor failed", e);
    } finally {
      setPhase("idle");
    }
  }, [
    adminSigner,
    adminAddress,
    birthUnix,
    client,
    commitmentHex,
    env,
    onChainUpdated,
    parentAddr,
  ]);

  const runOptIn = useCallback(async () => {
    if (mintedSbt == null || !guardianAtMint) return;
    setError(null);
    setLastTx(null);
    setPhase("opting");
    try {
      const signer = guardianSigner(
        guardianAtMint,
        "VedaGuard: opt in to pediatric SBT ASA — required before distribute",
      );
      const r = await submitAssetOptIn(client, signer, guardianAtMint, mintedSbt);
      setLastTx(r.txIDs[0] ?? null);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
      vgError("AdminConsole", "opt-in failed", e);
    } finally {
      setPhase("idle");
    }
  }, [client, guardianAtMint, guardianSigner, mintedSbt]);

  const runDistribute = useCallback(async () => {
    if (mintedSbt == null || !guardianAtMint) return;
    setError(null);
    setLastTx(null);
    setPhase("distributing");
    vgInfo("AdminConsole", "distribute_and_freeze_sbt", {
      sbt: mintedSbt,
      holder: guardianAtMint,
    });
    try {
      const signer = adminSigner(
        "VedaGuard Admin: distribute_and_freeze_sbt — soul-bound to guardian",
      );
      const r = await submitDistributeAndFreezeSbt(
        client,
        signer,
        adminAddress,
        mintedSbt,
        guardianAtMint,
        env,
      );
      setLastTx(r.txIDs[0] ?? null);
      onChainUpdated?.();
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
      vgError("AdminConsole", "distribute failed", e);
    } finally {
      setPhase("idle");
    }
  }, [
    adminAddress,
    adminSigner,
    client,
    env,
    guardianAtMint,
    mintedSbt,
    onChainUpdated,
  ]);

  const guardianMatchesWallet = guardianAtMint === connectedAddress;
  const busy = phase !== "idle";

  return (
    <div className="rounded-xl border border-amber-500/25 bg-amber-950/20 p-6">
      <h3 className="text-lg font-semibold text-amber-100">Admin console</h3>
      <p className="mt-2 text-sm leading-relaxed text-amber-100/80">
        On-chain admin is the <strong className="text-amber-50">application creator</strong>.
        This flow runs <code className="text-amber-200/90">onboard_minor</code>, guardian{" "}
        <code className="text-amber-200/90">opt-in</code>, then{" "}
        <code className="text-amber-200/90">distribute_and_freeze_sbt</code> — same as the
        Python script. Store only a <strong className="text-amber-50">32-byte hash</strong> in
        commitment metadata, never raw PII.
      </p>

      <div className="mt-6 space-y-4 border-t border-amber-500/20 pt-6">
        <label className="block text-xs font-medium text-slate-400">
          Guardian address — receives the frozen SBT
          <input
            type="text"
            value={parentAddr}
            onChange={(e) => setParentAddr(e.target.value)}
            spellCheck={false}
            className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 font-mono text-sm text-white placeholder:text-slate-600"
            placeholder="58-character Algorand address"
          />
        </label>
        <label className="block text-xs font-medium text-slate-400">
          Birth timestamp (Unix seconds, on-chain age / handoff logic)
          <input
            type="text"
            inputMode="numeric"
            value={birthUnix}
            onChange={(e) => setBirthUnix(e.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 font-mono text-sm text-white"
          />
        </label>
        <div>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <label className="text-xs font-medium text-slate-400">
              Principal commitment — 64 hex chars, 32 bytes
            </label>
            <button
              type="button"
              onClick={() => setCommitmentHex(samplePrincipalCommitmentHex())}
              className="rounded border border-slate-600 px-2 py-1 text-xs text-slate-300 hover:bg-slate-800"
            >
              Fill sample pattern
            </button>
          </div>
          <textarea
            value={commitmentHex}
            onChange={(e) => setCommitmentHex(e.target.value)}
            rows={2}
            spellCheck={false}
            className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 font-mono text-xs text-white"
          />
        </div>
      </div>

      <ol className="mt-6 space-y-4 text-sm text-slate-300">
        <li className="rounded-lg border border-slate-700 bg-slate-900/40 p-4">
          <span className="font-medium text-white">1. Mint SBT</span>
          <p className="mt-1 text-xs text-slate-500">
            Signs as admin. Creates ASA + registry row; SBT unit stays in the app account until
            step 3.
          </p>
          <button
            type="button"
            disabled={busy}
            onClick={() => void runMint()}
            className="mt-3 rounded-lg bg-amber-600 px-4 py-2 text-sm font-medium text-slate-950 hover:bg-amber-500 disabled:opacity-40"
          >
            {phase === "minting" ? "Signing…" : "Sign onboard_minor"}
          </button>
          {mintedSbt != null && (
            <p className="mt-2 font-mono text-xs text-emerald-400">
              New SBT ASA id: {mintedSbt}
            </p>
          )}
        </li>
        <li className="rounded-lg border border-slate-700 bg-slate-900/40 p-4">
          <span className="font-medium text-white">2. Guardian opt-in</span>
          <p className="mt-1 text-xs text-slate-500">
            The guardian must hold the ASA before distribution. If the guardian is another wallet,
            add the asset there in Pera; use the button below only when the connected wallet is the
            guardian.
          </p>
          <button
            type="button"
            disabled={busy || mintedSbt == null || !guardianMatchesWallet}
            onClick={() => void runOptIn()}
            className="mt-3 rounded-lg border border-slate-500 px-4 py-2 text-sm text-slate-200 hover:bg-slate-800 disabled:opacity-40"
          >
            {phase === "opting"
              ? "Signing…"
              : "Sign opt-in when wallet is guardian"}
          </button>
          {mintedSbt != null && !guardianMatchesWallet && (
            <p className="mt-2 text-xs text-amber-200/90">
              Connected wallet is not the guardian from step 1 — use Pera on{" "}
              <span className="font-mono">{guardianAtMint?.slice(0, 10)}…</span> to opt in to ASA{" "}
              {mintedSbt}.
            </p>
          )}
        </li>
        <li className="rounded-lg border border-slate-700 bg-slate-900/40 p-4">
          <span className="font-medium text-white">3. Distribute & freeze</span>
          <p className="mt-1 text-xs text-slate-500">
            Signs as admin. Transfers the SBT to the guardian and freezes it as soul-bound.
          </p>
          <button
            type="button"
            disabled={busy || mintedSbt == null}
            onClick={() => void runDistribute()}
            className="mt-3 rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-500 disabled:opacity-40"
          >
            {phase === "distributing" ? "Signing…" : "Sign distribute_and_freeze_sbt"}
          </button>
        </li>
      </ol>

      {error && (
        <div className="mt-4 rounded-lg border border-red-500/40 bg-red-950/30 px-3 py-2 text-xs text-red-100">
          {error}
        </div>
      )}
      {lastTx && (
        <p className="mt-3 font-mono text-xs text-slate-500">
          Last tx: {lastTx}
        </p>
      )}

      {mintedSbt != null && (
        <p className="mt-4 text-xs leading-relaxed text-slate-500">
          To drive <strong className="text-slate-400">Grant Access</strong> for this minor, set{" "}
          <code className="text-slate-400">VITE_CONSENT_ASSET_ID={mintedSbt}</code> in{" "}
          <code className="text-slate-400">veda-ui/.env</code> and restart Vite, or run{" "}
          <code className="text-slate-400">sync_veda_ui_env.py</code>.
        </p>
      )}
    </div>
  );
}
