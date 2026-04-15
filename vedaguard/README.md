# vedaguard

**VedaGuard** — DPDP-aligned parental consent on Algorand (atomic groups, Algorand Python, AlgoKit).

## AlgoBharat Developer Hub

This repo follows guidance from the **[AlgoBharat Developer Hub](https://algobharat.in/devportal/)**: lean hackathon scope, complete **UI → wallet → blockchain → confirmation** flow, and stack choices listed there (AlgoKit, Algorand Python, TestNet faucet, etc.). For **Hack Series 3.0**, see [https://algobharat.in/hack-series3/](https://algobharat.in/hack-series3/). VedaGuard maps to the hub’s **DPDP / RegTech** focus area.

**Quick links (curated on the Developer Hub):** [VibeKit](https://algobharat.in/devportal/) · AlgoKit install · TestNet faucet · [Algorand docs](https://dev.algorand.co/)

### VibeKit (tick the AlgoBharat “agentic” box)

[VibeKit](https://www.getvibekit.ai/) wires **official Algorand agent skills** + **MCP tools** into Cursor / Claude Code / OpenCode so your assistant can simulate deploys, call contracts, and inspect chain state. It does **not** ship inside your production binary; it is a **one-time machine setup** per developer.

From this folder (`vedaguard/`), after installing the CLI:

```bash
curl -fsSL https://getvibekit.ai/install | sh   # installs ~/.local/bin/vibekit
vibekit init                                    # interactive: pick Cursor, keyring/Vault, etc.
vibekit status                                  # confirm skills + MCP
```

Then enable the VibeKit MCP server in Cursor per the wizard output. Use it to rehearse `verify_consent` groups on LocalNet before demos. See [how it works](https://www.getvibekit.ai/getting-started/how-it-works).

---

This project was bootstrapped with AlgoKit. Default AlgoKit instructions follow below.

# Setup

### Pre-requisites

- [Python 3.12](https://www.python.org/downloads/) or later
- [Docker](https://www.docker.com/) (only required for LocalNet)

> For interactive tour over the codebase, download [vsls-contrib.codetour](https://marketplace.visualstudio.com/items?itemName=vsls-contrib.codetour) extension for VS Code, then open the [`.codetour.json`](./.tours/getting-started-with-your-algokit-project.tour) file in code tour extension.

### Initial Setup

#### 1. Clone the Repository
Start by cloning this repository to your local machine.

#### 2. Install Pre-requisites
Ensure the following pre-requisites are installed and properly configured:

- **Docker**: Required for running a local Algorand network. [Install Docker](https://www.docker.com/).
- **AlgoKit CLI**: Essential for project setup and operations. Install the latest version from [AlgoKit CLI Installation Guide](https://github.com/algorandfoundation/algokit-cli#install). Verify installation with `algokit --version`, expecting `2.0.0` or later.

#### 3. Bootstrap Your Local Environment
Run the following commands within the project folder:

- **Install Poetry**: Required for Python dependency management. [Installation Guide](https://python-poetry.org/docs/#installation). Verify with `poetry -V` to see version `1.2`+.
- **Setup Project**: Execute `algokit project bootstrap all` to install dependencies and setup a Python virtual environment in `.venv`.
- **Configure environment**: Execute `algokit generate env-file -a target_network localnet` to create a `.env.localnet` file with default configuration for `localnet`.
- **Start LocalNet**: Use `algokit localnet start` to initiate a local Algorand network.

### Development Workflow

#### Terminal
Directly manage and interact with your project using AlgoKit commands:

1. **Build Contracts**: `algokit project run build` compiles all smart contracts. You can also specify a specific contract by passing the name of the contract folder as an extra argument.
For example: `algokit project run build -- veda_guard` will only build the `veda_guard` contract.
2. **Deploy**: Use `algokit project deploy localnet` to deploy contracts to the local network. You can also specify a specific contract by passing the name of the contract folder as an extra argument.
For example: `algokit project deploy localnet -- veda_guard` will only deploy the `veda_guard` contract.

### Deploy to TestNet (judges / live UI)

AlgoKit cannot deploy without a **funded TestNet account**. This is done **on your machine** (mnemonic never belongs in git).

1. **Fund the deployer**  
   Create or use a TestNet wallet and request ALGO from the official faucet: [https://bank.testnet.algorand.network/](https://bank.testnet.algorand.network/)

2. **Configure secrets** (from the `vedaguard/` folder):

   ```bash
   cp .env.testnet.example .env.testnet
   ```

   Edit `.env.testnet` and set `DEPLOYER_MNEMONIC` to the wallet’s 25-word phrase.

   To **generate a new standalone account** with AlgoKit Utils (prints address + mnemonic; do not commit output):

   ```bash
   poetry run python scripts/generate_standalone_account.py
   ```

3. **Build and deploy**

   ```bash
   algokit project run build -- veda_guard
   CI=1 algokit project deploy testnet --non-interactive
   ```

   The log prints the **application ID** and **SBT asset id** after `onboard_minor` and `distribute_and_freeze_sbt`.

4. **Point the UI at TestNet** (`veda-ui/.env` or Vercel env vars):

   - `VITE_ALGOD_URL=https://testnet-api.algonode.cloud`
   - `VITE_VEDAGUARD_APP_ID=<app id from deploy log>`
   - `VITE_CONSENT_ASSET_ID=<SBT asset id from deploy log>` (or another ASA you opt into for the hospital leg)

5. **Wallet** — use Pera (or similar) on **TestNet**, same account you used as `parent` in deploy if you want the frozen SBT in that wallet.

#### VS Code 
For a seamless experience with breakpoint debugging and other features:

1. **Open Project**: In VS Code, open the repository root.
2. **Install Extensions**: Follow prompts to install recommended extensions.
3. **Debugging**:
   - Use `F5` to start debugging.
   - **Windows Users**: Select the Python interpreter at `./.venv/Scripts/python.exe` via `Ctrl/Cmd + Shift + P` > `Python: Select Interpreter` before the first run.

#### JetBrains IDEs
While primarily optimized for VS Code, JetBrains IDEs are supported:

1. **Open Project**: In your JetBrains IDE, open the repository root.
2. **Automatic Setup**: The IDE should configure the Python interpreter and virtual environment.
3. **Debugging**: Use `Shift+F10` or `Ctrl+R` to start debugging. Note: Windows users may encounter issues with pre-launch tasks due to a known bug. See [JetBrains forums](https://youtrack.jetbrains.com/issue/IDEA-277486/Shell-script-configuration-cannot-run-as-before-launch-task) for workarounds.

## AlgoKit Workspaces and Project Management
This project supports both standalone and monorepo setups through AlgoKit workspaces. Leverage [`algokit project run`](https://github.com/algorandfoundation/algokit-cli/blob/main/docs/features/project/run.md) commands for efficient monorepo project orchestration and management across multiple projects within a workspace.

## AlgoKit Generators

This template provides a set of [algokit generators](https://github.com/algorandfoundation/algokit-cli/blob/main/docs/features/generate.md) that allow you to further modify the project instantiated from the template to fit your needs, as well as giving you a base to build your own extensions to invoke via the `algokit generate` command.

### Generate Smart Contract 

The main application contract lives under `smart_contracts/veda_guard/`. To add another contract:

1. From the root of the project (`../`) execute `algokit generate smart-contract`. This will create a new starter smart contract and deployment configuration file under `{your_contract_name}` subfolder in the `smart_contracts` directory.
2. Each contract potentially has different creation parameters and deployment steps. Hence, you need to define your deployment logic in `deploy_config.py`file.
3. `config.py` file will automatically build all contracts in the `smart_contracts` directory. If you want to build specific contracts manually, modify the default code provided by the template in `config.py` file.

> Please note, above is just a suggested convention tailored for the base configuration and structure of this template. The default code supplied by the template in `config.py` and `index.ts` (if using ts clients) files are tailored for the suggested convention. You are free to modify the structure and naming conventions as you see fit.

### Generate '.env' files

By default the template instance does not contain any env files. Using [`algokit project deploy`](https://github.com/algorandfoundation/algokit-cli/blob/main/docs/features/project/deploy.md) against `localnet` | `testnet` | `mainnet` will use default values for `algod` and `indexer` unless overwritten via `.env` or `.env.{target_network}`. 

To generate a new `.env` or `.env.{target_network}` file, run `algokit generate env-file`

### Debugging Smart Contracts

This project is optimized to work with AlgoKit AVM Debugger extension. To activate it:
Refer to the commented header in the `__main__.py` file in the `smart_contracts` folder.

If you have opted in to include VSCode launch configurations in your project, you can also use the `Debug TEAL via AlgoKit AVM Debugger` launch configuration to interactively select an available trace file and launch the debug session for your smart contract.

For information on using and setting up the `AlgoKit AVM Debugger` VSCode extension refer [here](https://github.com/algorandfoundation/algokit-avm-vscode-debugger). To install the extension from the VSCode Marketplace, use the following link: [AlgoKit AVM Debugger extension](https://marketplace.visualstudio.com/items?itemName=algorandfoundation.algokit-avm-vscode-debugger).

# Tools

This project makes use of Algorand Python to build Algorand smart contracts. The following tools are in use:

- [Algorand](https://www.algorand.com/) - Layer 1 Blockchain; [Developer portal](https://dev.algorand.co/), [Why Algorand?](https://dev.algorand.co/getting-started/why-algorand/)
- [AlgoKit](https://github.com/algorandfoundation/algokit-cli) - One-stop shop tool for developers building on the Algorand network; [docs](https://github.com/algorandfoundation/algokit-cli/blob/main/docs/algokit.md), [intro tutorial](https://github.com/algorandfoundation/algokit-cli/blob/main/docs/tutorials/intro.md)
- [Algorand Python](https://github.com/algorandfoundation/puya) - A semantically and syntactically compatible, typed Python language that works with standard Python tooling and allows you to express smart contracts (apps) and smart signatures (logic signatures) for deployment on the Algorand Virtual Machine (AVM); [docs](https://github.com/algorandfoundation/puya), [examples](https://github.com/algorandfoundation/puya/tree/main/examples)
- [AlgoKit Utils](https://github.com/algorandfoundation/algokit-utils-py) - A set of core Algorand utilities that make it easier to build solutions on Algorand.
- [Poetry](https://python-poetry.org/): Python packaging and dependency management.
It has also been configured to have a productive dev experience out of the box in [VS Code](https://code.visualstudio.com/), see the [.vscode](./.vscode) folder.

