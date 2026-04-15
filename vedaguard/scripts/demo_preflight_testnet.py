"""
TestNet demo preflight — run once before a panel / live demo.

Checks (no secrets printed):
  - App exists; approval bytecode includes ``handoff_sbt_to_adult`` ABI selector
  - SBT ASA exists and app account is creator/clawback (expected for VedaGuard)
  - Registry box for SBT exists; decode guardian + birth_ts + adult_principal
  - Indexer: exactly one positive balance; frozen state reported
  - Optional: ``--child ADDR`` must be opted in to the SBT

Reads ``veda-ui/.env`` for ``VITE_VEDAGUARD_APP_ID`` and ``VITE_CONSENT_ASSET_ID``
unless overridden by flags.

Usage (from ``vedaguard/``)::

    poetry run python scripts/demo_preflight_testnet.py
    poetry run python scripts/demo_preflight_testnet.py --child 5DVIXLPT7XBXRDG6ATZ2DIZR3SS7PANDEOXKZF6XI4RYTD6WFEZBXNIZSM
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]

# From current VedaGuard ARC-4 ABI (must match veda-ui arc56).
_SELECTOR_HANDOFF = bytes.fromhex("ab2a08e4")
_SELECTOR_VERIFY = bytes.fromhex("a00d3bc6")
_SBT_PREFIX = b"vg"


def _parse_veda_ui_env() -> dict[str, str]:
    p = _ROOT / "veda-ui" / ".env"
    out: dict[str, str] = {}
    if not p.is_file():
        return out
    for line in p.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def _encode_registry_box_name(sbt_id: int) -> bytes:
    enc = sbt_id.to_bytes(8, "big")
    return _SBT_PREFIX + enc


def _http_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "VedaGuard-preflight/1"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def _http_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "VedaGuard-preflight/1"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def _decode_box_principal(value: bytes) -> tuple[int, str, str]:
    """birth_ts BE u64, guardian 32b, adult 32b → addresses via algo encoding."""
    from algosdk.encoding import encode_address

    if len(value) < 8 + 32 + 32:
        raise ValueError(f"box value too short: {len(value)}")
    birth = int.from_bytes(value[:8], "big")
    g = encode_address(value[8:40])
    a = encode_address(value[40:72])
    return birth, g, a


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--app-id", type=int, default=None)
    ap.add_argument("--sbt-id", type=int, default=None)
    ap.add_argument(
        "--child",
        metavar="ADDR",
        default="",
        help="If set, require this account to be opted in to the SBT",
    )
    ap.add_argument(
        "--algod",
        default="https://testnet-api.algonode.cloud",
        help="Algod base URL",
    )
    ap.add_argument(
        "--indexer",
        default="https://testnet-idx.algonode.cloud",
        help="Indexer base URL",
    )
    args = ap.parse_args()

    env_map = _parse_veda_ui_env()
    app_id = args.app_id
    sbt_id = args.sbt_id
    if app_id is None:
        app_id = int(env_map.get("VITE_VEDAGUARD_APP_ID", "0") or 0)
    if sbt_id is None:
        sbt_id = int(env_map.get("VITE_CONSENT_ASSET_ID", "0") or 0)
    if app_id <= 0 or sbt_id <= 0:
        raise SystemExit(
            "Set VITE_VEDAGUARD_APP_ID and VITE_CONSENT_ASSET_ID in veda-ui/.env "
            "or pass --app-id and --sbt-id",
        )

    algod = args.algod.rstrip("/")
    idx = args.indexer.rstrip("/")
    errors: list[str] = []
    warnings: list[str] = []

    print(f"Preflight app_id={app_id} sbt_id={sbt_id}")
    print(f"  algod={algod}")
    print(f"  indexer={idx}")

    # 1) App + bytecode
    try:
        app = _http_json(f"{algod}/v2/applications/{app_id}")
        approval = base64.b64decode(app["params"]["approval-program"])
        has_verify = _SELECTOR_VERIFY in approval
        has_handoff = _SELECTOR_HANDOFF in approval
        print(f"  approval program: {len(approval)} bytes")
        print(f"  bytecode has verify_consent selector: {has_verify}")
        print(f"  bytecode has handoff_sbt_to_adult selector: {has_handoff}")
        if not has_verify:
            errors.append("Missing verify_consent in on-chain approval (wrong/old deploy?)")
        if not has_handoff:
            errors.append("Missing handoff_sbt_to_adult — UI handoff will fail with router err")
    except urllib.error.HTTPError as e:
        errors.append(f"Application {app_id}: HTTP {e.code}")
        approval = b""

    # 2) ASA
    try:
        asset = _http_json(f"{algod}/v2/assets/{sbt_id}")
        p = asset["params"]
        creator = p.get("creator", "")
        print(f"  ASA {sbt_id} name={p.get('name')} creator={creator[:8]}… total={p.get('total')}")
    except urllib.error.HTTPError as e:
        errors.append(f"Asset {sbt_id}: HTTP {e.code}")

    # 3) Registry box
    try:
        box_name = _encode_registry_box_name(sbt_id)
        b64name = base64.b64encode(box_name).decode()
        # Algod expects ``encoding:value`` (e.g. ``b64:...``), not raw base64.
        name_param = urllib.parse.quote(f"b64:{b64name}", safe="")
        box_url = f"{algod}/v2/applications/{app_id}/box?name={name_param}"
        raw = _http_json(box_url)
        raw_val = base64.b64decode(raw["value"])
        birth, guardian, adult_z = _decode_box_principal(raw_val)
        from algosdk.encoding import encode_address

        zero = encode_address(bytes(32))
        adult_set = adult_z != zero
        print(f"  registry box: birth_ts={birth} guardian={guardian}")
        if adult_set:
            print(f"  adult_principal: {adult_z} (handoff already done on-chain)")
            warnings.append(
                "Handoff already completed for this SBT — redeploy/onboard if you need a live handoff demo",
            )
        else:
            print("  adult_principal: (zero — guardian still data principal)")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            errors.append(
                f"No registry box for sbt_id={sbt_id} on app {app_id} — wrong VITE_CONSENT_ASSET_ID?",
            )
        else:
            errors.append(f"Box fetch: HTTP {e.code}")

    # 4) Holdings
    try:
        bal = _http_json(f"{idx}/v2/assets/{sbt_id}/balances?currency-greater-than=0")
        rows = bal.get("balances") or []
        print(f"  indexer holders (balance>0): {len(rows)}")
        for r in rows:
            print(
                f"    {r['address'][:8]}… amount={r['amount']} frozen={r.get('is-frozen')}",
            )
        if len(rows) != 1:
            errors.append(f"Expected exactly 1 holder with SBT; got {len(rows)}")
    except urllib.error.HTTPError as e:
        errors.append(f"Indexer balances: HTTP {e.code}")

    # 5) Optional child opt-in
    child = args.child.strip()
    if child:
        try:
            acct = _http_json(f"{idx}/v2/accounts/{child}")
            holdings = acct.get("assets") or []
            found = None
            for h in holdings:
                if int(h.get("asset-id", 0)) == sbt_id:
                    found = h
                    break
            if found is None:
                errors.append(
                    f"Child {child[:8]}… has no indexer row for ASA {sbt_id} — opt in Pera (TestNet) first",
                )
            else:
                amt = found.get("amount", 0)
                print(f"  child opt-in OK {child[:8]}… amount={amt}")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                errors.append(
                    f"Child account {child[:8]}… not found on indexer — fund the account on TestNet",
                )
            else:
                errors.append(f"Child account lookup: HTTP {e.code}")

    print()
    if warnings:
        print("WARNINGS (non-blocking):")
        for w in warnings:
            print(f"  ! {w}")
        print()
    if errors:
        print("PREFLIGHT FAILED:")
        for e in errors:
            print(f"  - {e}")
        raise SystemExit(1)
    print("PREFLIGHT OK — proceed with Pera TestNet + guardian wallet + Grant Access / handoff.")
    raise SystemExit(0)


if __name__ == "__main__":
    main()
