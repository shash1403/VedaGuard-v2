"""
Merge VedaGuard TestNet IDs into ``veda-ui/.env`` so the dashboard works with minimal typing.

Legal intent: demo hosts set chain targets once; non-technical viewers only use Pera + taps.

From ``vedaguard/``::

    # After ``run_testnet_e2e.py --fresh`` (uses ``.vedaguard_e2e_cache.env``):
    poetry run python scripts/sync_veda_ui_env.py

    # Or pass IDs from deploy logs / AlgoExplorer:
    poetry run python scripts/sync_veda_ui_env.py --app-id 1012 --sbt-id 1029

Updates only: ``VITE_ALGOD_URL``, ``VITE_ALGOD_TOKEN``, ``VITE_VEDAGUARD_APP_ID``,
``VITE_CONSENT_ASSET_ID``. Other lines in ``veda-ui/.env`` are preserved.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_UI_ENV = _ROOT / "veda-ui" / ".env"
_DEFAULT_CACHE = _ROOT / ".vedaguard_e2e_cache.env"

_KEY = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=")


def _parse_simple_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if "=" in s:
            k, v = s.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def merge_env_file(path: Path, updates: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = frozenset(updates)
    lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    out: list[str] = []
    seen: set[str] = set()

    for line in lines:
        m = _KEY.match(line.strip())
        if m and m.group(1) in keys:
            k = m.group(1)
            if k not in seen:
                out.append(f"{k}={updates[k]}")
                seen.add(k)
            continue
        out.append(line)

    for k, v in updates.items():
        if k not in seen:
            out.append(f"{k}={v}")

    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("From ``vedaguard/``::")[0].strip())
    p.add_argument("--from", dest="from_file", type=Path, default=_DEFAULT_CACHE)
    p.add_argument("--app-id", type=int, default=None)
    p.add_argument("--sbt-id", type=int, default=None)
    p.add_argument(
        "--target",
        type=Path,
        default=_UI_ENV,
        help="Path to .env to merge (default: veda-ui/.env)",
    )
    args = p.parse_args()

    updates: dict[str, str] = {
        "VITE_ALGOD_URL": "https://testnet-api.algonode.cloud",
        "VITE_ALGOD_TOKEN": "",
    }

    if args.app_id is not None and args.sbt_id is not None:
        updates["VITE_VEDAGUARD_APP_ID"] = str(args.app_id)
        updates["VITE_CONSENT_ASSET_ID"] = str(args.sbt_id)
    else:
        cached = _parse_simple_env(args.from_file)
        app_raw = cached.get("VITE_VEDAGUARD_APP_ID", "").strip()
        sbt_raw = cached.get("VITE_CONSENT_ASSET_ID", "").strip()
        if not app_raw or not sbt_raw:
            raise SystemExit(
                f"No app/SBT in {args.from_file}. Run with --app-id and --sbt-id, or "
                "run ``poetry run python scripts/run_testnet_e2e.py --fresh`` first."
            )
        updates["VITE_VEDAGUARD_APP_ID"] = app_raw
        updates["VITE_CONSENT_ASSET_ID"] = sbt_raw
        if cached.get("VITE_ALGOD_URL"):
            updates["VITE_ALGOD_URL"] = cached["VITE_ALGOD_URL"]
        if "VITE_ALGOD_TOKEN" in cached:
            updates["VITE_ALGOD_TOKEN"] = cached["VITE_ALGOD_TOKEN"]

    merge_env_file(args.target, updates)
    try:
        shown = str(args.target.relative_to(_ROOT))
    except ValueError:
        shown = str(args.target.resolve())
    print(f"Merged TestNet UI env → {shown}")
    print("  Restart the dev server: cd veda-ui && npm run dev")


if __name__ == "__main__":
    main()
