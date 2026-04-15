import { useState, type FormEvent } from "react";
import {
  adminGatePasswordExpected,
  persistAdminGateUnlocked,
} from "../lib/adminGate";

interface AdminGateLoginProps {
  onUnlocked: () => void;
}

/**
 * UI gate for the Admin tab. On-chain control remains the deployer wallet + contract.
 */
export function AdminGateLogin({ onUnlocked }: AdminGateLoginProps) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    const want = adminGatePasswordExpected();
    if (password !== want) {
      setError("Incorrect password.");
      return;
    }
    persistAdminGateUnlocked();
    onUnlocked();
  };

  return (
    <div className="mx-auto max-w-md rounded-xl border border-slate-600 bg-slate-900/60 p-6 shadow-lg">
      <h3 className="text-lg font-semibold text-white">Admin access</h3>
      <p className="mt-2 text-xs leading-relaxed text-slate-400">
        This password is a <strong className="text-slate-300">UI-only</strong> screen so the
        admin workflow is separated from the parent dashboard. It does not replace blockchain
        rules: only the <strong className="text-slate-300">deployer wallet</strong> can execute
        mint and distribute on-chain.
      </p>
      <form onSubmit={submit} className="mt-5 space-y-4">
        <label className="block text-xs font-medium text-slate-400">
          Password
          <input
            type="password"
            autoComplete="off"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-950 px-3 py-2 text-sm text-white placeholder:text-slate-600"
            placeholder="Default: admin"
          />
        </label>
        {error && (
          <p className="text-xs text-red-300" role="alert">
            {error}
          </p>
        )}
        <button
          type="submit"
          className="w-full rounded-lg bg-amber-600 px-4 py-2.5 text-sm font-semibold text-slate-950 hover:bg-amber-500"
        >
          Unlock admin console
        </button>
      </form>
      <p className="mt-4 text-[11px] leading-relaxed text-slate-600">
        Default password is <code className="text-slate-500">admin</code>. To hide this screen,
        set <code className="text-slate-500">VITE_ADMIN_DEMO_GATE=false</code> in{" "}
        <code className="text-slate-500">.env</code> for local development.
      </p>
    </div>
  );
}
