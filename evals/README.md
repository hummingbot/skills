# Skill Evals

Evaluation system for testing and comparing Hummingbot skills.

## Structure

```
evals/
├── run_eval.sh          # Shared runner (hummingbot-deploy style)
├── compare.sh           # Compare results between skills
├── prompts.json         # hummingbot-deploy test prompts
├── results/             # hummingbot-deploy results
├── Dockerfile           # Docker image for containerized evals
├── lp-agent/            # LP Agent eval suite
│   ├── run_eval.sh      # Runner with token/turn tracking
│   ├── summary.sh       # Results analyzer & comparison
│   ├── prompts.json     # 28 test cases across 8 commands
│   └── results/         # LP Agent results
└── README.md
```

## Usage

### hummingbot-deploy (shared runner)

```bash
./run_eval.sh hummingbot-deploy                    # Run all prompts
./run_eval.sh hummingbot-deploy install_api        # Run single prompt
./run_eval.sh hummingbot-deploy --direct           # Direct mode (skip Claude)
./compare.sh hummingbot-deploy hummingbot-api-setup
```

### lp-agent

```bash
cd lp-agent
./run_eval.sh                          # Run all 28 tests
./run_eval.sh --command explore-pools  # Run tests for one command
./run_eval.sh --id start_onboarding   # Run a single test
./run_eval.sh --tag conversational    # Run tests by tag
./run_eval.sh --model haiku           # Use a specific model
./run_eval.sh --dry-run               # List tests without running

./summary.sh                          # Analyze latest results
./summary.sh --compare                # Compare two most recent runs
./summary.sh --all                    # Historical overview
```

See [lp-agent/README.md](lp-agent/README.md) for full documentation.

## Adding a New Skill

Create a subdirectory under `evals/` with:
- `prompts.json` — Test case definitions
- `run_eval.sh` — Runner script (copy from lp-agent as template)
- `results/` — Output directory

## Shared Prompt Format

```json
{
  "id": "my_test",
  "prompt": "What the user would ask",
  "verify": "command to verify success (or echo 'manual')"
}
```

## Extended Prompt Format (lp-agent style)

```json
{
  "id": "test_id",
  "command": "subcommand-name",
  "prompt": "Natural language user request",
  "description": "What this test verifies",
  "expect_patterns": ["regex1|alt1", "regex2"],
  "expect_scripts": ["script.sh --flag"],
  "tags": ["category1", "category2"]
}
```
