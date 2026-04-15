"""
Generate a standalone Algorand account (25-word mnemonic) using AlgoKit Utils.

See https://dev.algorand.co/concepts/accounts/create/#standalone

Run from ``vedaguard/`` with Poetry (not system ``python3``)::

    cd vedaguard && poetry install && poetry run python mnemonic.py

Do not commit printed mnemonics. Prefer ``scripts/generate_standalone_account.py`` for CI/docs.
"""

from __future__ import annotations

try:
    from algokit_utils import AlgorandClient
    from algosdk import mnemonic as algo_mnemonic
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Dependencies missing or wrong interpreter.\n"
        "  cd vedaguard && poetry install && poetry run python mnemonic.py\n"
        "Do not run with /opt/homebrew/bin/python3 unless that env has algokit-utils."
    ) from exc


def main() -> None:
    client = AlgorandClient.testnet()
    acct = client.account.random()
    phrase = algo_mnemonic.from_private_key(acct.private_key)
    assert client.account.from_mnemonic(mnemonic=phrase).address == acct.address

    print("New standalone account — store offline; fund on TestNet before deploy.")
    print(f"  Address:   {acct.address}")
    print(f"  Mnemonic:  {phrase}")
    print()
    print("In .env.testnet:")
    print(f"  DEPLOYER_MNEMONIC={phrase}")


if __name__ == "__main__":
    main()
