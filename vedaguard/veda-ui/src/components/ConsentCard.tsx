import { useState } from "react";
import { vgError, vgInfo } from "../lib/vedaGuardLog";

export interface ConsentOnChainResult {
  appCallTxId: string;
  confirmedRound: bigint;
}

interface ConsentCardProps {
  hospitalName: string;
  recordType: string;
  childName: string;
  timestamp: string;
  onApprove: () => Promise<ConsentOnChainResult>;
}

export function ConsentCard({
  hospitalName,
  recordType,
  childName,
  timestamp,
  onApprove,
}: ConsentCardProps) {
  const [status, setStatus] = useState<
    "pending" | "signing" | "approved" | "error"
  >("pending");
  const [errorDetail, setErrorDetail] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<ConsentOnChainResult | null>(
    null,
  );

  const handleApprove = async () => {
    setStatus("signing");
    setErrorDetail(null);
    vgInfo("ConsentCard", "Grant Access clicked", {
      hospitalName,
      recordType,
      at: new Date().toISOString(),
    });
    try {
      const result = await onApprove();
      setLastResult(result);
      setStatus("approved");
      vgInfo("ConsentCard", "Grant Access confirmed on-chain", {
        hospitalName,
        appCallTxId: result.appCallTxId,
        confirmedRound: String(result.confirmedRound),
      });
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setErrorDetail(msg);
      setStatus("error");
      vgError("ConsentCard", "Grant Access failed", e, { hospitalName, recordType });
    }
  };

  const statusConfig = {
    pending: {
      badge: "Awaiting Consent",
      badgeClass: "bg-amber-500/10 text-amber-400 border-amber-500/20",
      borderClass: "border-slate-700",
    },
    signing: {
      badge: "Signing in wallet…",
      badgeClass: "bg-blue-500/10 text-blue-400 border-blue-500/20",
      borderClass: "border-blue-500/30",
    },
    approved: {
      badge: "On-chain confirmed",
      badgeClass: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
      borderClass: "border-emerald-500/30",
    },
    error: {
      badge: "Failed",
      badgeClass: "bg-red-500/10 text-red-400 border-red-500/20",
      borderClass: "border-red-500/30",
    },
  };

  const config = statusConfig[status];

  return (
    <div
      className={`rounded-xl border ${config.borderClass} bg-slate-800/50 p-6 transition-all duration-300`}
    >
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <h3 className="text-lg font-semibold text-white">{hospitalName}</h3>
          <p className="text-sm text-slate-400">
            Requesting access to{" "}
            <span className="text-slate-300">{recordType}</span>
          </p>
        </div>
        <span
          className={`rounded-full border px-3 py-1 text-xs font-medium ${config.badgeClass}`}
        >
          {config.badge}
        </span>
      </div>

      <div className="mt-4 space-y-2 rounded-lg bg-slate-900/50 p-4">
        <div className="flex justify-between text-sm">
          <span className="text-slate-500">Child</span>
          <span className="text-slate-300">{childName}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-slate-500">Record Type</span>
          <span className="text-slate-300">{recordType}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-slate-500">Requested</span>
          <span className="text-slate-300">{timestamp}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-slate-500">Consent Method</span>
          <span className="font-medium text-teal-400">Algorand Atomic Group</span>
        </div>
      </div>

      <div className="mt-4 rounded-lg border border-slate-700/50 bg-slate-900/30 p-3">
        <p className="text-xs leading-relaxed text-slate-500">
          <span className="font-semibold text-amber-400">DPDP Section 9:</span>{" "}
          Pera will ask you to sign three grouped transactions: asset transfer for the
          hospital leg, zero-ALGO payment as consent proof, and the app call to{" "}
          <code className="text-slate-400">verify_consent</code>. All succeed or
          all fail.
        </p>
      </div>

      {status === "pending" && (
        <button
          type="button"
          onClick={handleApprove}
          className="mt-5 w-full cursor-pointer rounded-lg bg-gradient-to-r from-emerald-500 to-teal-500 py-3 text-sm font-semibold text-white transition-all hover:from-emerald-400 hover:to-teal-400"
        >
          Grant Access to {hospitalName}
        </button>
      )}

      {status === "signing" && (
        <div className="mt-5 flex items-center justify-center gap-2 py-3">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-blue-400 border-t-transparent" />
          <span className="text-sm text-blue-400">
            Approve in Pera Wallet…
          </span>
        </div>
      )}

      {status === "approved" && lastResult && (
        <div className="mt-5 space-y-2 py-2">
          <div className="flex items-center gap-2 text-emerald-400">
            <svg
              className="h-5 w-5 shrink-0"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
            <span className="text-sm font-medium">
              Atomic group committed in round {lastResult.confirmedRound.toString()}
            </span>
          </div>
          <p className="break-all font-mono text-xs text-slate-400">
            verify_consent tx: {lastResult.appCallTxId}
          </p>
        </div>
      )}

      {status === "error" && errorDetail && (
        <div className="mt-4 rounded-lg border border-red-500/20 bg-red-500/5 p-3">
          <p className="text-xs text-red-300">{errorDetail}</p>
          <button
            type="button"
            onClick={() => {
              setStatus("pending");
              setErrorDetail(null);
            }}
            className="mt-2 text-xs font-medium text-red-200 underline hover:text-white"
          >
            Try again
          </button>
        </div>
      )}
    </div>
  );
}
