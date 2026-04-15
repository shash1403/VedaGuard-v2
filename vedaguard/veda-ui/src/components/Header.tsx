export type MainNavTab = "dashboard" | "admin";

interface HeaderProps {
  address: string | null;
  isConnecting: boolean;
  onConnect: () => void;
  onDisconnect: () => void;
  /** When set (wallet connected), show Parent / Admin switcher in the sticky header. */
  mainTab?: MainNavTab;
  onMainTabChange?: (tab: MainNavTab) => void;
}

export function Header({
  address,
  isConnecting,
  onConnect,
  onDisconnect,
  mainTab = "dashboard",
  onMainTabChange,
}: HeaderProps) {
  const truncated = address
    ? `${address.slice(0, 6)}...${address.slice(-4)}`
    : null;

  const showNav = Boolean(address && onMainTabChange);

  return (
    <header className="border-b border-slate-700 bg-slate-900/80 backdrop-blur-md sticky top-0 z-50">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-6 py-4">
        <div className="flex min-w-0 flex-1 flex-wrap items-center gap-3 sm:gap-4">
          <div className="flex items-center gap-3 shrink-0">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-400 to-teal-500 font-bold text-slate-900 text-lg">
              V
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight">
                VedaGuard
              </h1>
              <p className="text-xs text-slate-400">DPDP Act 2025 Compliant</p>
            </div>
          </div>

          {showNav && (
            <nav
              className="flex shrink-0 rounded-lg bg-slate-800/90 p-1 ring-1 ring-slate-600"
              aria-label="Main sections"
            >
              <button
                type="button"
                onClick={() => onMainTabChange!("dashboard")}
                className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                  mainTab === "dashboard"
                    ? "bg-slate-700 text-white shadow"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                Parent
              </button>
              <button
                type="button"
                onClick={() => onMainTabChange!("admin")}
                className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                  mainTab === "admin"
                    ? "bg-amber-600/90 text-white shadow"
                    : "text-slate-400 hover:text-amber-200"
                }`}
              >
                Admin
              </button>
            </nav>
          )}
        </div>

        {address ? (
          <div className="flex shrink-0 items-center gap-3">
            <span className="rounded-full bg-emerald-500/10 px-4 py-1.5 text-sm font-medium text-emerald-400 border border-emerald-500/20">
              {truncated}
            </span>
            <button
              onClick={onDisconnect}
              className="rounded-lg bg-slate-700 px-4 py-2 text-sm text-slate-300 hover:bg-slate-600 transition-colors cursor-pointer"
            >
              Disconnect
            </button>
          </div>
        ) : (
          <button
            onClick={onConnect}
            disabled={isConnecting}
            className="rounded-lg bg-gradient-to-r from-emerald-500 to-teal-500 px-6 py-2.5 text-sm font-semibold text-white hover:from-emerald-400 hover:to-teal-400 disabled:opacity-50 transition-all cursor-pointer"
          >
            {isConnecting ? "Connecting..." : "Connect Pera Wallet"}
          </button>
        )}
      </div>
    </header>
  );
}
