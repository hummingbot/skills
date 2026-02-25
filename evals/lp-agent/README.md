# LP Agent Evaluations

Test suite for evaluating lp-agent skill commands. Measures task completion, token usage, turn count, and output quality.

## Quick Start

```bash
# Run all tests
./run_eval.sh

# Run tests for one command
./run_eval.sh --command start
./run_eval.sh --command explore-pools

# Run a single test
./run_eval.sh --id start_onboarding

# Run by tag
./run_eval.sh --tag conversational

# List tests without running
./run_eval.sh --dry-run

# Use a specific model
./run_eval.sh --model haiku
```

## Analyzing Results

```bash
# View latest results
./summary.sh

# Compare two most recent runs
./summary.sh --compare

# View all historical runs
./summary.sh --all

# View a specific result file
./summary.sh results/lp-agent_20260225_120000.json
```

## Test Coverage

| Command | Tests | What's Verified |
|---------|-------|-----------------|
| `start` | 2 | Welcomes user, checks infra, explains capabilities |
| `deploy-hummingbot-api` | 3 | Status check, install with defaults, view logs |
| `setup-gateway` | 4 | Status, start, custom RPC, network config |
| `add-wallet` | 3 | List wallets, add securely, check balances |
| `explore-pools` | 5 | List pools, search, sort by APR, pool details, advisory |
| `select-strategy` | 3 | Compare strategies, recommend passive, recommend testing |
| `run-strategy` | 5 | Create config, deploy bot, status, create executor, stop |
| `analyze-performance` | 3 | Visualize, export CSV, filter recent |

**Total: 28 test cases**

## Metrics Tracked

Each test records:
- **success** — Exit code 0 + expected patterns in output + expected scripts invoked
- **duration_seconds** — Wall-clock time
- **tokens.input / tokens.output** — Token counts from Claude CLI
- **num_turns** — Agent round-trips (tool calls)
- **cost_usd** — API cost per test
- **output_length** — Response character count

## Verification

Tests use two verification methods:

1. **Output patterns** — Regex patterns the agent's response must contain (e.g., `"liquidity|LP"`)
2. **Script patterns** — Script names/args that must appear in the agent's tool calls (e.g., `"list_meteora_pools.py --query SOL"`)

Pipe-separated alternatives match any variant: `"check_api.sh|check_gateway.sh"` passes if either appears.

## Result Format

```json
{
  "skill": "lp-agent",
  "model": "sonnet",
  "timestamp": "2026-02-25T12:00:00Z",
  "summary": {
    "total": 28,
    "passed": 25,
    "failed": 3,
    "pass_rate": 89,
    "total_tokens": 142000,
    "avg_duration_seconds": 12.5,
    "avg_tokens_per_test": 5071
  },
  "results": [
    {
      "id": "start_onboarding",
      "command": "start",
      "success": true,
      "duration_seconds": 8.2,
      "tokens": { "input": 3200, "output": 1800, "total": 5000 },
      "num_turns": 3,
      "verification": {
        "patterns": [{"pattern": "liquidity|LP", "matched": true}],
        "scripts": [{"script": "check_api.sh", "matched": true}]
      }
    }
  ]
}
```

## Tags

Filter tests by category:

| Tag | Description |
|-----|-------------|
| `conversational` | Agent responds with guidance, no scripts required |
| `onboarding` | First-time setup and orientation |
| `infrastructure` | API/Gateway deployment and management |
| `status` | Checking current state of services |
| `install` | Installing or deploying services |
| `config` | Configuration changes (RPC, network, etc.) |
| `wallet` | Wallet operations |
| `pools` | Pool discovery and exploration |
| `discovery` | Searching and listing |
| `details` | Fetching detailed information |
| `advisory` | Agent recommends or explains tradeoffs |
| `strategy` | LP strategy configuration and deployment |
| `analysis` | Performance analysis and reporting |
