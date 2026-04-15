"""
Generate a standalone Algorand account (25-word mnemonic) using AlgoKit Utils.

Uses ``AlgorandClient.account.random()`` and ``algosdk.mnemonic.from_private_key``,
matching the flow described at:
https://dev.algorand.co/concepts/accounts/create/#standalone

Do not commit or share the printed mnemonic. Fund the address on TestNet before deploy.

Usage (from ``vedaguard/``)::

    poetry run python scripts/generate_standalone_account.py
"""

from __future__ import annotations

import algosdk.mnemonic
from algokit_utils import AlgorandClient


def main() -> None:
    # Network config is irrelevant for local key generation; TestNet client is a simple default.
    client = AlgorandClient.testnet()
    acct = client.account.random()
    phrase = algosdk.mnemonic.from_private_key(acct.private_key)

    # Sanity check against AlgoKit Utils mnemonic loader (deploy uses this path).
    assert client.account.from_mnemonic(mnemonic=phrase).address == acct.address

    print("New standalone account — store offline; fund on TestNet before deploy.")
    print(f"  Address:   {acct.address}")
    print(f"  Mnemonic:  {phrase}")
    print()
    print("In .env.testnet:")
    print(f"  DEPLOYER_MNEMONIC={phrase}")


if __name__ == "__main__":
    main()
