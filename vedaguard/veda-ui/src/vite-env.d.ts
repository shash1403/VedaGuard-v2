/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_ALGOD_URL?: string;
  readonly VITE_ALGOD_SERVER?: string;
  readonly VITE_ALGOD_PORT?: string;
  readonly VITE_ALGOD_TOKEN?: string;
  readonly VITE_VEDAGUARD_APP_ID?: string;
  readonly VITE_CONSENT_ASSET_ID?: string;
  /** Set to "false" to skip the client-side Admin password screen. */
  readonly VITE_ADMIN_DEMO_GATE?: string;
  /** Admin tab password when gate is on; default "admin" if unset. Not a security boundary. */
  readonly VITE_ADMIN_DEMO_PASSWORD?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
