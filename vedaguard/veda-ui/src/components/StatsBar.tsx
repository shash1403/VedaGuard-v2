import type { ReactNode } from "react";
import type { SbtPrincipalView } from "../lib/algorand";
import { ALGORAND_ZERO_ADDRESS } from "../lib/algorand";

export type StatsDetailKey = "minors" | "consents" | "pending";

/** Sample pending rows shown in the Pending Requests detail panel. */
export interface PendingAccessRequestDetail {
  id: string;
  hospitalName: string;
  recordType: string;
  childName: string;
  timestamp: string;
}

interface StatsBarProps {
  minorsOnboarded: number;
  consentsGranted: number;
  pendingRequests: number;
  pendingItems: PendingAccessRequestDetail[];
  expandedKey: StatsDetailKey | null;
  onToggleExpanded: (key: StatsDetailKey) => void;
  appId: string;
  consentAssetId: string;
  sbtRegistry: SbtPrincipalView | null;
  sbtRegistryLoading: boolean;
  sbtRegistryError: string | null;
  onRetrySbtRegistry?: () => void;
  envOk: boolean;
  /** ASA ids parsed from on-chain registry box names (`vg` + id). */
  registrySbtAssetIds: number[];
  registrySbtIdsError: string | null;
}

function formatAdultPrincipal(row: SbtPrincipalView): string {
  return row.adultPrincipal === ALGORAND_ZERO_ADDRESS
    ? "Not set — guardian is data principal"
    : row.adultPrincipal;
}

function DetailShell({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div
      className="rounded-xl border border-slate-600/80 bg-slate-900/60 p-4 text-left"
      role="region"
      aria-label={title}
    >
      <h4 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-400">
        {title}
      </h4>
      {children}
    </div>
  );
}

export function StatsBar({
  minorsOnboarded,
  consentsGranted,
  pendingRequests,
  pendingItems,
  expandedKey,
  onToggleExpanded,
  appId,
  consentAssetId,
  sbtRegistry,
  sbtRegistryLoading,
  sbtRegistryError,
  onRetrySbtRegistry,
  envOk,
  registrySbtAssetIds,
  registrySbtIdsError,
}: StatsBarProps) {
  const envConsentNum = Number(consentAssetId);
  const consentMismatch =
    Number.isFinite(envConsentNum) &&
    registrySbtAssetIds.length > 0 &&
    !registrySbtAssetIds.includes(envConsentNum);
  const stats: {
    key: StatsDetailKey;
    label: string;
    value: number;
    color: string;
    subtext: string;
  }[] = [
    {
      key: "minors",
      label: "Minors Registered",
      value: minorsOnboarded,
      color: "text-teal-400",
      subtext: "Section 2(i) SBTs",
    },
    {
      key: "consents",
      label: "Consents Granted",
      value: consentsGranted,
      color: "text-emerald-400",
      subtext: "Atomic Groups",
    },
    {
      key: "pending",
      label: "Pending Requests",
      value: pendingRequests,
      color: "text-amber-400",
      subtext: "Awaiting Signature",
    },
  ];

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {stats.map((s) => {
          const isOpen = expandedKey === s.key;
          return (
            <button
              key={s.key}
              type="button"
              onClick={() => onToggleExpanded(s.key)}
              className={`rounded-xl border bg-slate-800/50 p-5 text-left transition-colors hover:bg-slate-800/80 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-500/60 ${
                isOpen
                  ? "border-teal-500/50 ring-1 ring-teal-500/30"
                  : "border-slate-700"
              }`}
            >
              <p className="text-sm text-slate-400">{s.label}</p>
              <p className={`mt-1 text-3xl font-bold ${s.color}`}>{s.value}</p>
              <p className="mt-1 text-xs text-slate-500">{s.subtext}</p>
              <p className="mt-3 text-[11px] text-slate-600">
                {isOpen ? "Click to collapse" : "Click for full details"}
              </p>
            </button>
          );
        })}
      </div>

      {expandedKey === "minors" && (
        <DetailShell title="Minors registered — full detail">
          <p className="mb-3 text-xs leading-relaxed text-slate-400">
            The contract keeps an on-chain aggregate{" "}
            <code className="text-slate-300">minor_count</code> (shown on the
            card). Each successful <code className="text-slate-300">onboard_minor</code>{" "}
            mints an SBT and creates a box row for age and principal resolution.
          </p>
          <dl className="space-y-2 font-mono text-xs text-slate-300">
            <div className="flex flex-wrap gap-x-2">
              <dt className="text-slate-500">Application id</dt>
              <dd>{appId}</dd>
            </div>
            <div className="flex flex-wrap gap-x-2">
              <dt className="text-slate-500">minor_count — global</dt>
              <dd>{minorsOnboarded}</dd>
            </div>
            <div className="flex flex-wrap gap-x-2">
              <dt className="text-slate-500">Configured SBT ASA from env</dt>
              <dd>{consentAssetId}</dd>
            </div>
          </dl>
          <div className="mt-4 border-t border-slate-700 pt-4">
            <p className="mb-2 text-xs font-medium text-slate-400">
              SBT ASA ids with a registry box on this app
            </p>
            <p className="mb-2 text-xs leading-relaxed text-slate-500">
              Each onboarded minor gets a box named <code className="text-slate-400">vg</code>{" "}
              + asset id. Set <code className="text-slate-400">VITE_CONSENT_ASSET_ID</code> in{" "}
              <code className="text-slate-400">.env</code> to one of these values (then restart{" "}
              <code className="text-slate-400">npm run dev</code>).
            </p>
            {registrySbtIdsError && (
              <p className="mb-2 text-xs text-red-300">
                Could not list boxes: {registrySbtIdsError}
              </p>
            )}
            {!registrySbtIdsError && sbtRegistryLoading && (
              <p className="mb-2 animate-pulse text-xs text-slate-500">Loading box list…</p>
            )}
            {!registrySbtIdsError && !sbtRegistryLoading && (
              <p className="mb-2 font-mono text-xs text-teal-300">
                {registrySbtAssetIds.length > 0
                  ? registrySbtAssetIds.join(", ")
                  : "No matching registry boxes found; unexpected when minor_count is above zero."}
              </p>
            )}
            {consentMismatch && (
              <p className="mb-3 rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-100">
                <strong className="text-amber-50">Mismatch:</strong> env ASA{" "}
                <code className="text-amber-200">{consentAssetId}</code> is not in the list
                above. Use one of the listed ids for consent + handoff, or redeploy and copy
                the new SBT id from deploy logs.
              </p>
            )}
          </div>
          <div className="mt-4 border-t border-slate-700 pt-4">
            <p className="mb-2 text-xs text-slate-500">
              Registry row for the configured SBT (read via algod{" "}
              <code className="text-slate-400">/v2/applications/…/box</code>
              ):
            </p>
            {!envOk && (
              <p className="text-xs text-amber-200/90">
                Configure <code className="text-amber-100">.env</code> to load
                this row.
              </p>
            )}
            {envOk && sbtRegistryLoading && (
              <p className="animate-pulse text-xs text-slate-500">Loading…</p>
            )}
            {envOk && sbtRegistryError && (
              <div className="space-y-2">
                <p className="text-xs text-red-300">{sbtRegistryError}</p>
                {onRetrySbtRegistry && (
                  <button
                    type="button"
                    onClick={onRetrySbtRegistry}
                    className="rounded border border-slate-600 px-2 py-1 text-xs text-slate-300 hover:bg-slate-800"
                  >
                    Retry
                  </button>
                )}
              </div>
            )}
            {envOk && !sbtRegistryLoading && !sbtRegistryError && sbtRegistry && (
              <dl className="space-y-2 break-all font-mono text-xs text-slate-300">
                <div>
                  <dt className="text-slate-500">birth_ts</dt>
                  <dd>{sbtRegistry.birthTs.toString()}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">guardian</dt>
                  <dd>{sbtRegistry.guardian}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">adult_principal</dt>
                  <dd>{formatAdultPrincipal(sbtRegistry)}</dd>
                </div>
              </dl>
            )}
            {envOk &&
              !sbtRegistryLoading &&
              !sbtRegistryError &&
              !sbtRegistry && (
                <p className="text-xs text-slate-500">No row loaded yet.</p>
              )}
          </div>
        </DetailShell>
      )}

      {expandedKey === "consents" && (
        <DetailShell title="Consents granted — full detail">
          <p className="mb-3 text-xs leading-relaxed text-slate-400">
            Each successful atomic group that passes{" "}
            <code className="text-slate-300">verify_consent</code> increments{" "}
            <code className="text-slate-300">consent_count</code> on the app.
            The UI does not list individual tx ids without an indexer; use the
            explorer filtered by your app id to audit past groups.
          </p>
          <dl className="space-y-2 font-mono text-xs text-slate-300">
            <div className="flex flex-wrap gap-x-2">
              <dt className="text-slate-500">Application id</dt>
              <dd>{appId}</dd>
            </div>
            <div className="flex flex-wrap gap-x-2">
              <dt className="text-slate-500">consent_count — global</dt>
              <dd>{consentsGranted}</dd>
            </div>
            <div className="flex flex-wrap gap-x-2">
              <dt className="text-slate-500">Hospital leg ASA from env</dt>
              <dd>{consentAssetId}</dd>
            </div>
          </dl>
        </DetailShell>
      )}

      {expandedKey === "pending" && (
        <DetailShell title="Pending access requests — full detail">
          <p className="mb-3 text-xs leading-relaxed text-slate-400">
            Sample queue: each row is a sample hospital request. Approving in the
            cards below submits a live atomic group under Section 9. Count on the stat
            card matches the rows listed here.
          </p>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left text-xs">
              <thead>
                <tr className="border-b border-slate-700 text-slate-500">
                  <th className="py-2 pr-3 font-medium">ID</th>
                  <th className="py-2 pr-3 font-medium">Hospital</th>
                  <th className="py-2 pr-3 font-medium">Record type</th>
                  <th className="py-2 pr-3 font-medium">Child label</th>
                  <th className="py-2 font-medium">Timestamp</th>
                </tr>
              </thead>
              <tbody className="text-slate-300">
                {pendingItems.map((r) => (
                  <tr
                    key={r.id}
                    className="border-b border-slate-800/80 align-top"
                  >
                    <td className="py-2 pr-3 font-mono text-slate-400">
                      {r.id}
                    </td>
                    <td className="py-2 pr-3">{r.hospitalName}</td>
                    <td className="py-2 pr-3">{r.recordType}</td>
                    <td className="py-2 pr-3">{r.childName}</td>
                    <td className="py-2 whitespace-nowrap text-slate-400">
                      {r.timestamp}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </DetailShell>
      )}
    </div>
  );
}
