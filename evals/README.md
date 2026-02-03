# Skill Evals

Minimal evaluation system for comparing skills.

## Usage

```bash
# Run eval for a skill
./run_eval.sh hummingbot-deploy

# Run eval for the old skill
./run_eval.sh hummingbot-api-setup

# Compare results
./compare.sh hummingbot-deploy hummingbot-api-setup

# Run single prompt
./run_eval.sh hummingbot-deploy install_api
```

## Files

- `prompts.json` - Test prompts and verification commands
- `run_eval.sh` - Runs prompts against a skill
- `compare.sh` - Compares results between two skills
- `results/` - Timestamped result files (JSON)

## Adding Prompts

Edit `prompts.json`:

```json
{
  "id": "my_test",
  "prompt": "What the user would ask",
  "verify": "command to verify success (or echo 'manual')"
}
```
