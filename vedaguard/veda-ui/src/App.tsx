import { useCallback, useEffect, useState } from "react";
import { usePeraWallet } from "./hooks/usePeraWallet";
import { Header, type MainNavTab } from "./components/Header";
import {
  StatsBar,
  type PendingAccessRequestDetail,
  type StatsDetailKey,
} from "./components/StatsBar";
import { ConsentCard } from "./components/ConsentCard";
import { HandoffSection } from "./components/HandoffSection";
import { AdminConsole } from "./components/AdminConsole";
import { AdminGateLogin } from "./components/AdminGateLogin";
import {
  adminGateEnabled,
  clearAdminGateUnlock,
  readAdminGateUnlockedFromSession,
} from "./lib/adminGate";
import {
  createAlgodClient,
  fetchApplicationCreatorAddress,
  fetchConsentCount,
  fetchMinorCount,
  listRegistrySbtAssetIds,
  simulateGetSbtPrincipalRecord,
  submitAtomicVerifyConsent,
  type SbtPrincipalView,
} from "./lib/algorand";
import { makePeraWalletSigner } from "./lib/peraSigner";
import { envConfigured, getVedaGuardEnv } from "./lib/config";
import { vgDebug, vgError, vgInfo } from "./lib/vedaGuardLog";

const MOCK_REQUESTS: PendingAccessRequestDetail[] = [
  {
    id: "1",
    hospitalName: "Manipal Hospital",
    recordType: "Vaccination Records",
    childName: "Aarav J., hashed identifier",
    timestamp: "2025-04-03 14:32 IST",
  },
  {
    id: "2",
    hospitalName: "Apollo Children's",
    recordType: "Blood Work Panel",
    childName: "Aarav J., hashed identifier",
    timestamp: "2025-04-03 11:15 IST",
  },
  {
    id: "3",
    hospitalName: "AIIMS Pediatrics",
    recordType: "Growth Chart Data",
    childName: "Priya J., hashed identifier",
    timestamp: "2025-04-02 09:45 IST",
  },
];

function App() {
  const { address, connect, disconnect, isConnecting, peraWallet } =
    usePeraWallet();
  const [envOk] = useState(envConfigured);
  const [minorCount, setMinorCount] = useState<number | null>(null);
  const [consentCount, setConsentCount] = useState<number | null>(null);
  const [chainError, setChainError] = useState<string | null>(null);
  const [statsExpanded, setStatsExpanded] = useState<StatsDetailKey | null>(
    null,
  );
  const [sbtForMinorsPanel, setSbtForMinorsPanel] =
    useState<SbtPrincipalView | null>(null);
  const [sbtPanelLoading, setSbtPanelLoading] = useState(false);
  const [sbtPanelError, setSbtPanelError] = useState<string | null>(null);
  const [registrySbtAssetIds, setRegistrySbtAssetIds] = useState<number[]>([]);
  const [registrySbtIdsError, setRegistrySbtIdsError] = useState<string | null>(
    null,
  );
  const [mainTab, setMainTab] = useState<MainNavTab>("dashboard");

  const setMainTabFromNav = useCallback((tab: MainNavTab) => {
    setMainTab(tab);
    const path = `${window.location.pathname}${window.location.search}`;
    if (tab === "admin") {
      if (window.location.hash !== "#admin") {
        window.history.replaceState(null, "", `${path}#admin`);
      }
    } else if (window.location.hash === "#admin") {
      window.history.replaceState(null, "", path);
    }
  }, []);
  const [appCreatorAddress, setAppCreatorAddress] = useState<string | null>(
    null,
  );
  const [creatorFetchError, setCreatorFetchError] = useState<string | null>(
    null,
  );
  const [adminGateUnlocked, setAdminGateUnlocked] = useState(
    () => readAdminGateUnlockedFromSession(),
  );

  const refreshOnChainStats = useCallback(async () => {
    if (!envOk) return;
    setChainError(null);
    vgDebug("App", "refreshOnChainStats start");
    try {
      const env = getVedaGuardEnv();
      const client = createAlgodClient(env);
      const [minors, consents] = await Promise.all([
        fetchMinorCount(client, env.appId),
        fetchConsentCount(client, env.appId),
      ]);
      setMinorCount(Number(minors));
      setConsentCount(Number(consents));
      vgInfo("App", "refreshOnChainStats OK", {
        minorCount: String(minors),
        consentCount: String(consents),
        appId: String(env.appId),
      });
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setChainError(msg);
      vgError("App", "refreshOnChainStats failed", e);
    }
  }, [envOk]);

  useEffect(() => {
    if (address && envOk) {
      void refreshOnChainStats();
    }
  }, [address, envOk, refreshOnChainStats]);

  useEffect(() => {
    if (!envOk) {
      setAppCreatorAddress(null);
      setCreatorFetchError(null);
      return;
    }
    let cancelled = false;
    void (async () => {
      try {
        const env = getVedaGuardEnv();
        const client = createAlgodClient(env);
        const creator = await fetchApplicationCreatorAddress(client, env.appId);
        if (!cancelled) {
          setAppCreatorAddress(creator);
          setCreatorFetchError(null);
        }
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        if (!cancelled) {
          setAppCreatorAddress(null);
          setCreatorFetchError(msg);
        }
        vgError("App", "fetchApplicationCreatorAddress failed", e);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [envOk]);

  useEffect(() => {
    const syncFromHash = () => {
      if (window.location.hash.replace(/^#/, "") === "admin") {
        setMainTab("admin");
      }
    };
    syncFromHash();
    window.addEventListener("hashchange", syncFromHash);
    return () => window.removeEventListener("hashchange", syncFromHash);
  }, []);

  useEffect(() => {
    if (!address) return;
    if (window.location.hash.replace(/^#/, "") === "admin") {
      setMainTab("admin");
    }
  }, [address]);

  useEffect(() => {
    if (!address) {
      clearAdminGateUnlock();
      setAdminGateUnlocked(false);
    }
  }, [address]);

  const loadSbtRegistryForStatsPanel = useCallback(async () => {
    if (!address || !envOk) return;
    setSbtPanelLoading(true);
    setSbtPanelError(null);
    setRegistrySbtIdsError(null);
    setRegistrySbtAssetIds([]);
    setSbtForMinorsPanel(null);
    try {
      const env = getVedaGuardEnv();
      const client = createAlgodClient(env);
      vgInfo("App", "loadSbtRegistryForStatsPanel", {
        wallet: address,
        consentAssetId: String(env.consentAssetId),
      });
      let ids: number[] = [];
      try {
        ids = await listRegistrySbtAssetIds(client, env.appId);
        setRegistrySbtAssetIds(ids);
      } catch (e) {
        const m = e instanceof Error ? e.message : String(e);
        setRegistrySbtIdsError(m);
        vgError("App", "listRegistrySbtAssetIds failed", e);
      }
      try {
        const row = await simulateGetSbtPrincipalRecord(
          client,
          address,
          env,
          Number(env.consentAssetId),
        );
        setSbtForMinorsPanel(row);
      } catch (e) {
        const m = e instanceof Error ? e.message : String(e);
        setSbtPanelError(m);
        vgError("App", "simulateGetSbtPrincipalRecord for stats panel failed", e, {
          wallet: address,
        });
      }
    } finally {
      setSbtPanelLoading(false);
    }
  }, [address, envOk]);

  useEffect(() => {
    if (statsExpanded === "minors" && address && envOk) {
      void loadSbtRegistryForStatsPanel();
    }
  }, [statsExpanded, address, envOk, loadSbtRegistryForStatsPanel]);

  const toggleStatsDetail = useCallback((key: StatsDetailKey) => {
    setStatsExpanded((cur) => (cur === key ? null : key));
  }, []);

  const handleApproveConsent = useCallback(async () => {
    if (!address) {
      const err = new Error("Connect Pera Wallet first");
      vgError("App", "handleApproveConsent blocked", err);
      throw err;
    }
    if (!envOk) {
      const err = new Error(
        "Configure .env: copy .env.example to .env and set VITE_VEDAGUARD_APP_ID and VITE_CONSENT_ASSET_ID",
      );
      vgError("App", "handleApproveConsent blocked", err);
      throw err;
    }

    vgInfo("App", "handleApproveConsent → submitAtomicVerifyConsent", {
      address,
    });
    const env = getVedaGuardEnv();
    const client = createAlgodClient(env);
    const signer = makePeraWalletSigner(peraWallet, address);

    const result = await submitAtomicVerifyConsent(
      client,
      signer,
      address,
      env,
    );

    await refreshOnChainStats();

    return {
      appCallTxId: result.appCallTxId,
      confirmedRound: result.confirmedRound,
    };
  }, [address, envOk, peraWallet, refreshOnChainStats]);

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <Header
        address={address}
        isConnecting={isConnecting}
        onConnect={connect}
        onDisconnect={disconnect}
        mainTab={mainTab}
        onMainTabChange={address ? setMainTabFromNav : undefined}
      />

      <main className="mx-auto max-w-6xl px-6 py-10">
        {!envOk && (
          <div className="mb-6 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
            <strong className="text-amber-50">Blockchain env not configured.</strong>{" "}
            Copy <code className="text-amber-200">veda-ui/.env.example</code> to{" "}
            <code className="text-amber-200">veda-ui/.env</code> and set{" "}
            <code className="text-amber-200">VITE_VEDAGUARD_APP_ID</code> and{" "}
            <code className="text-amber-200">VITE_CONSENT_ASSET_ID</code>. The wallet must be
            opted in to that ASA. Restart <code className="text-amber-200">npm run dev</code>.
          </div>
        )}

        {chainError && (
          <div className="mb-6 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">
            Could not read on-chain stats: {chainError}
          </div>
        )}

        {!address ? (
          <div className="flex flex-col items-center justify-center py-32 text-center">
            <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-400 to-teal-500 text-4xl font-bold text-slate-900">
              V
            </div>
            <h2 className="mb-3 text-3xl font-bold text-white">
              VedaGuard Parent Dashboard
            </h2>
            <p className="mb-8 max-w-md leading-relaxed text-slate-400">
              DPDP Act 2025 compliant pediatric health record consent manager.
              Connect Pera, then sign a real Algorand atomic group for each
              access request under Section 9.
            </p>
            <button
              type="button"
              onClick={connect}
              disabled={isConnecting}
              className="cursor-pointer rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 px-8 py-3.5 text-base font-semibold text-white transition-all hover:from-emerald-400 hover:to-teal-400 disabled:opacity-50"
            >
              {isConnecting ? "Connecting..." : "Connect Pera Wallet"}
            </button>
            <p className="mt-4 text-xs text-slate-600">
              Use the same network as your Algod URL (LocalNet or TestNet).
            </p>
            <p className="mt-6 max-w-md text-xs leading-relaxed text-slate-500">
              <strong className="text-slate-400">Admin onboarding:</strong> open{" "}
              <code className="rounded bg-slate-800 px-1 text-slate-300">
                {typeof window !== "undefined" ? `${window.location.origin}${window.location.pathname}#admin` : "…#admin"}
              </code>
              , connect the deployer wallet, then use the <strong className="text-slate-400">Admin</strong>{" "}
              control in the top bar. Admin gate password defaults to{" "}
              <code className="text-slate-400">admin</code>.
            </p>
          </div>
        ) : (
          <div className="space-y-8">
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <h2 className="text-2xl font-bold text-white">
                  {mainTab === "dashboard" ? "Parent Dashboard" : "Admin console"}
                </h2>
                <p className="mt-1 text-sm text-slate-400">
                  {mainTab === "dashboard"
                    ? 'Each "Grant Access" submits a live atomic transaction group to VedaGuard.'
                    : "On-chain onboarding for judges: mint SBT, guardian opt-in, distribute & freeze."}
                </p>
              </div>
              {envOk && mainTab === "dashboard" && (
                <button
                  type="button"
                  onClick={() => void refreshOnChainStats()}
                  className="rounded-lg border border-slate-600 px-4 py-2 text-sm text-slate-300 hover:bg-slate-800"
                >
                  Refresh chain stats
                </button>
              )}
            </div>

            {mainTab === "admin" ? (
              <div className="space-y-4">
                {!envOk && (
                  <p className="text-sm text-slate-500">
                    Configure <code className="text-slate-400">.env</code> first.
                  </p>
                )}
                {envOk && creatorFetchError && (
                  <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-100">
                    Could not load app creator: {creatorFetchError}
                  </div>
                )}
                {envOk && appCreatorAddress && address !== appCreatorAddress && (
                  <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-50">
                    <p className="font-medium">Connect the deployer wallet</p>
                    <p className="mt-1 text-xs text-amber-100/80">
                      On-chain admin — application creator:{" "}
                      <code className="text-amber-50">{appCreatorAddress}</code>
                    </p>
                    <p className="mt-2 text-xs text-amber-100/70">
                      Your connected address does not match. Switch accounts in Pera, then
                      reconnect.
                    </p>
                  </div>
                )}
                {envOk && appCreatorAddress && address === appCreatorAddress && (
                  adminGateEnabled() && !adminGateUnlocked ? (
                    <AdminGateLogin onUnlocked={() => setAdminGateUnlocked(true)} />
                  ) : (
                    <AdminConsole
                      key={address}
                      adminAddress={appCreatorAddress}
                      connectedAddress={address}
                      peraWallet={peraWallet}
                      onChainUpdated={() => void refreshOnChainStats()}
                    />
                  )
                )}
              </div>
            ) : (
              <>
                <StatsBar
                  minorsOnboarded={minorCount ?? 0}
                  consentsGranted={consentCount ?? 0}
                  pendingRequests={MOCK_REQUESTS.length}
                  pendingItems={MOCK_REQUESTS}
                  expandedKey={statsExpanded}
                  onToggleExpanded={toggleStatsDetail}
                  appId={
                    envOk ? getVedaGuardEnv().appId.toString() : "—"
                  }
                  consentAssetId={
                    envOk ? getVedaGuardEnv().consentAssetId.toString() : "—"
                  }
                  sbtRegistry={sbtForMinorsPanel}
                  sbtRegistryLoading={sbtPanelLoading}
                  sbtRegistryError={sbtPanelError}
                  onRetrySbtRegistry={() => void loadSbtRegistryForStatsPanel()}
                  envOk={envOk}
                  registrySbtAssetIds={registrySbtAssetIds}
                  registrySbtIdsError={registrySbtIdsError}
                />

                {address && (
                  <HandoffSection
                    connectedAddress={address}
                    peraWallet={peraWallet}
                    envOk={envOk}
                  />
                )}

                <div>
                  <h3 className="mb-4 text-lg font-semibold text-white">
                    Pending Access Requests
                  </h3>
                  <div className="grid gap-5 lg:grid-cols-2">
                    {MOCK_REQUESTS.map((req) => (
                      <ConsentCard
                        key={req.id}
                        hospitalName={req.hospitalName}
                        recordType={req.recordType}
                        childName={req.childName}
                        timestamp={req.timestamp}
                        onApprove={handleApproveConsent}
                      />
                    ))}
                  </div>
                </div>

                <div className="rounded-xl border border-slate-700 bg-slate-800/30 p-6">
                  <h3 className="mb-3 text-sm font-semibold text-slate-300">
                    Full-stack flow — submission-ready
                  </h3>
                  <ol className="list-decimal space-y-2 pl-5 text-xs text-slate-500">
                    <li>
                      UI builds txn 0 (asset transfer), txn 1 (0 µALGO payment to app
                      account), txn 2 (<code className="text-slate-400">verify_consent</code>).{" "}
                      <code className="text-slate-400">assignGroupID</code> ties them.
                    </li>
                    <li>
                      Pera signs all three; <code className="text-slate-400">algod</code>{" "}
                      confirms the group; <code className="text-slate-400">consent_count</code>{" "}
                      increments on success.
                    </li>
                    <li>
                      Single-wallet flow: one address signs the hospital self-transfer and the
                      parent legs. Production: hospital signs txn 0; parent signs txn 1 and 2,
                      or use split signers.
                    </li>
                  </ol>
                </div>
              </>
            )}
          </div>
        )}
      </main>

      <footer className="border-t border-slate-800 px-6 py-6 text-center text-xs text-slate-600">
        <p>
          VedaGuard &middot; DPDP Act 2025 Sections 9, 2(i), 2(f) &middot; Live
          Algorand + Pera
        </p>
        <p className="mt-2">
          Builder resources:{" "}
          <a
            href="https://algobharat.in/devportal/"
            target="_blank"
            rel="noopener noreferrer"
            className="text-teal-500 hover:text-teal-400 underline"
          >
            AlgoBharat Developer Hub
          </a>
          {" · "}
          <a
            href="https://dev.algorand.co/"
            target="_blank"
            rel="noopener noreferrer"
            className="text-teal-500 hover:text-teal-400 underline"
          >
            Algorand Developer Portal
          </a>
        </p>
      </footer>
    </div>
  );
}

export default App;
