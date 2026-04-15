import { useCallback, useState } from "react";
import algosdk from "algosdk";
import type { PeraWalletConnect } from "@perawallet/connect";
import {
  ALGORAND_ZERO_ADDRESS,
  createAlgodClient,
  simulateGetSbtPrincipalRecord,
  submitHandoffSbtToAdult,
  type SbtPrincipalView,
} from "../lib/algorand";
import { makePeraWalletSigner } from "../lib/peraSigner";
import { getVedaGuardEnv } from "../lib/config";
import { vgError, vgInfo } from "../lib/vedaGuardLog";

function formatPrincipalRow(row: SbtPrincipalView | null) {
  if (!row) return null;
  const adult =
    row.adultPrincipal === ALGORAND_ZERO_ADDRESS
      ? "Not set — still guardian"
      : row.adultPrincipal;
  return { ...row, adultLabel: adult };
}

interface HandoffSectionProps {
  connectedAddress: string;
  peraWallet: InstanceType<typeof PeraWalletConnect>;
  envOk: boolean;
}

export function HandoffSection({
  connectedAddress,
  peraWallet,
  envOk,
}: HandoffSectionProps) {
  const [adultAddrInput, setAdultAddrInput] = useState("");
  const [registry, setRegistry] = useState<SbtPrincipalView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [phase, setPhase] = useState<"idle" | "loading" | "handoff">("idle");

  const env = envOk ? getVedaGuardEnv() : null;
  const sbtId = env ? Number(env.consentAssetId) : 0;

  const loadRegistry = useCallback(async () => {
    if (!env) return;
    setError(null);
    setPhase("loading");
    vgInfo("HandoffSection", "Load registry clicked", {
      connectedAddress,
      sbtId,
      appId: String(env.appId),
    });
    try {
      const client = createAlgodClient(env);
      const row = await simulateGetSbtPrincipalRecord(
        client,
        connectedAddress,
        env,
        sbtId,
      );
      setRegistry(row);
      vgInfo("HandoffSection", "Registry loaded OK", {
        birthTs: row.birthTs.toString(),
        guardian: row.guardian,
        adultPrincipal: row.adultPrincipal,
      });
    } catch (e) {
      setRegistry(null);
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
      vgError("HandoffSection", "Load registry failed", e, { connectedAddress, sbtId });
    } finally {
      setPhase("idle");
    }
  }, [connectedAddress, env, sbtId]);

  const runHandoff = useCallback(async () => {
    if (!env) return;
    const adult =
      adultAddrInput.trim() === "" ? connectedAddress : adultAddrInput.trim();
    if (!algosdk.isValidAddress(adult)) {
      const msg =
        "Enter a valid Algorand address for the adult child, or leave blank to use the connected wallet.";
      vgError("HandoffSection", "Invalid adult address", new Error(msg), {
        adultInputLength: adult.length,
      });
      setError(msg);
      return;
    }
    setError(null);
    setPhase("handoff");
    vgInfo("HandoffSection", "Run handoff clicked", {
      guardian: connectedAddress,
      adultResolved: adult,
      adultWasEmptyInput: adultAddrInput.trim() === "",
      sbtId,
    });
    try {
      const client = createAlgodClient(env);
      const signer = makePeraWalletSigner(peraWallet, connectedAddress);
      await submitHandoffSbtToAdult(
        client,
        signer,
        connectedAddress,
        adult,
        env,
        sbtId,
      );
      vgInfo("HandoffSection", "Handoff tx submitted OK; refreshing registry");
      await loadRegistry();
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
      vgError("HandoffSection", "Handoff failed", e, {
        guardian: connectedAddress,
        adult,
        sbtId,
      });
    } finally {
      setPhase("idle");
    }
  }, [
    adultAddrInput,
    connectedAddress,
    env,
    loadRegistry,
    peraWallet,
    sbtId,
  ]);

  if (!envOk || !env) {
    return null;
  }

  const formatted = formatPrincipalRow(registry);

  return (
    <div className="rounded-xl border border-slate-700 bg-slate-800/30 p-6">
      <h3 className="mb-1 text-lg font-semibold text-white">
        Section 2(f) — Handoff to adult
      </h3>
      <p className="mb-4 text-xs leading-relaxed text-slate-500">
        Uses <code className="text-slate-400">VITE_CONSENT_ASSET_ID</code> as the SBT
        to inspect and hand off. Connect as the <strong className="text-slate-300">guardian</strong>,
        the wallet that holds the frozen SBT. The adult must{" "}
        <strong className="text-slate-300">opt in</strong> to that ASA in Pera first.
        On-chain rules: minor must be 18+ per stored birth timestamp; handoff runs once.
      </p>

      <div className="mb-4 flex flex-wrap gap-2">
        <button
          type="button"
          disabled={phase !== "idle"}
          onClick={() => void loadRegistry()}
          className="rounded-lg border border-slate-600 px-4 py-2 text-sm text-slate-200 hover:bg-slate-800 disabled:opacity-50"
        >
          Load registry for SBT
        </button>
      </div>

      {formatted && (
        <div className="mb-4 rounded-lg border border-slate-700/80 bg-slate-900/40 p-3 font-mono text-xs text-slate-400">
          <div>
            <span className="text-slate-500">birth_ts </span>
            {formatted.birthTs.toString()}
          </div>
          <div className="mt-1 break-all">
            <span className="text-slate-500">guardian </span>
            {formatted.guardian}
          </div>
          <div className="mt-1 break-all">
            <span className="text-slate-500">adult_principal </span>
            {formatted.adultLabel}
          </div>
        </div>
      )}

      <label className="mb-2 block text-xs font-medium text-slate-400">
        Adult child address — leave blank to use connected wallet
      </label>
      <input
        type="text"
        value={adultAddrInput}
        onChange={(e) => setAdultAddrInput(e.target.value)}
        placeholder={connectedAddress}
        className="mb-3 w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 font-mono text-xs text-slate-200 placeholder:text-slate-600"
      />

      <button
        type="button"
        disabled={phase !== "idle"}
        onClick={() => void runHandoff()}
        className="w-full rounded-lg bg-gradient-to-r from-violet-600 to-indigo-600 py-2.5 text-sm font-semibold text-white hover:from-violet-500 hover:to-indigo-500 disabled:opacity-50"
      >
        {phase === "handoff" ? "Sign handoff in Pera…" : "Run handoff_sbt_to_adult"}
      </button>

      {error && (
        <p className="mt-3 text-xs text-red-400">{error}</p>
      )}
    </div>
  );
}
