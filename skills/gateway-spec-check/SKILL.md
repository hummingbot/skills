---
name: gateway-spec-check
description: Compare the Gateway clients in hummingbot and hummingbot-api against a Gateway OpenAPI spec generated from a chosen version of the gateway repo. Use this skill when a Gateway route or field was renamed, before merging a Gateway change, when a Gateway call 404s or a response field reads as None, or when adopting a new Gateway release in either client.
metadata:
  author: hummingbot
commands:
  check:
    description: Generate a spec from gateway and check both clients against it
  check-ref:
    description: Check both clients against a specific gateway branch, tag, or commit
  generate-spec:
    description: Generate a Gateway OpenAPI spec without running any checks
  adopt:
    description: Regenerate a repo's Gateway models from a spec and show what changed
---

# Gateway spec check

## What this is for

Three repos, one API. `gateway` defines it; `hummingbot`'s `GatewayHttpClient` and
`hummingbot-api`'s `GatewayClient` are both hand-written against it. Neither client
imports anything from Gateway, so a rename over there is invisible on this side until it
fails in production, mid-trade:

- `/trading/swap/*` split into `/trading/{router,clmm,amm}/*-swap`, and every swap 404'd.
- `clmm quote-position` became `quote-liquidity`, `amm add-liquidity` became `add`.
- `chain` + `network` merged into `chainNetwork`, and every Gateway executor failed to
  start with `querystring must have required property 'chainNetwork'` — a message that
  pointed nowhere near the call that sent it.
- `approve_token` read `gasPrice` from a response whose schema is
  `{signature, status, data}`, recording a gas price of zero on every approval. Nothing
  raised: every reader is a `.get()`, so a renamed field reads `None`.

Each of those was found by reading Gateway's source by hand. This skill asks the spec
instead.

## Prerequisites

All three repos checked out locally, and a Gateway with `node_modules` installed
(`pnpm install`). Defaults are `~/hummingbot`, `~/hummingbot-api`, `~/gateway`; override
with `$HUMMINGBOT_DIR`, `$HUMMINGBOT_API_DIR`, `$GATEWAY_DIR` or the `--gateway`,
`--hummingbot`, `--hummingbot-api` flags.

The `models` check needs `datamodel-code-generator`. If `uvx` is on the PATH it is used
without installing anything permanently; otherwise install the package into the
interpreter running the script. The run header names the version it used — that file is
compared byte for byte, so a generator release that changes its formatting reads as drift
that is not there. Pin one with `$GATEWAY_SPEC_CODEGEN`:

```bash
export GATEWAY_SPEC_CODEGEN="uvx --from datamodel-code-generator==0.75.1 datamodel-codegen"
```

Nothing is imported from either client repo, so no conda environment is needed and one
interpreter checks both.

## check — the normal run

```bash
cd skills/gateway-spec-check
SPEC=$(bash scripts/generate_spec.sh --out /tmp/gateway-spec.json)
python3 scripts/check_spec.py --spec "$SPEC"
```

`generate_spec.sh` runs Gateway's own `scripts/generate-openapi.ts`, which builds the
document from the route table without starting a server. It restores gateway's committed
`openapi.json` afterwards, so the checkout you are editing is left clean.

`check_spec.py` prints one line per check per repo and exits non-zero if any failed:

```
hummingbot  (/Users/you/hummingbot)
  ok   routes   35 client routes, all served by the spec's 67
  ok   keys     46 camelCase keys, all declared by the spec
  ok   models   hummingbot/core/gateway/gateway_models.py is byte-identical to what this spec generates
  ok   mirrors  6 hand-written models match the schemas they mirror
  ok   kwargs   13 model constructions, every keyword a real field
```

Narrow it with `--repo hummingbot` / `--repo hummingbot-api`, or
`--check routes,keys`.

## check-ref — against a specific Gateway version

```bash
SPEC=$(bash scripts/generate_spec.sh --ref development --out /tmp/gw-development.json)
python3 scripts/check_spec.py --spec "$SPEC"
```

`--ref` takes any branch, tag, or commit. It checks that ref out into a throwaway git
worktree under `$TMPDIR` and generates there, so the gateway working tree is untouched,
and it prints the `git worktree remove` line to run when you are done. The worktree's
`node_modules` is populated with symlinks to the main checkout's packages rather than
reinstalled — if the ref moved a dependency the generator reaches for, run `pnpm install`
in the worktree and rerun.

Two versions, diffed, is the fastest way to see what a Gateway release actually changed:

```bash
bash scripts/generate_spec.sh --ref v2.9.0    --out /tmp/gw-2.9.json
bash scripts/generate_spec.sh --ref v2.10.0   --out /tmp/gw-2.10.json
python3 -c "
import json
old, new = (set(json.load(open(p))['paths']) for p in ['/tmp/gw-2.9.json', '/tmp/gw-2.10.json'])
print('gone: ', sorted(old - new))
print('added:', sorted(new - old))
"
```

## The five checks

| check | what it reads | what it catches |
|---|---|---|
| `routes` | every path literal the client hands to its request method, plus hummingbot's `_lp_route`-assembled LP paths | a renamed or deleted route — the 404 class |
| `keys` | every camelCase string literal in the modules that speak Gateway's wire format | a renamed field read through `.get()` — the silent-`None` class |
| `models` | regenerates the committed generated-models file from this spec and compares | the models drifting from the Gateway they claim to mirror |
| `mirrors` | hand-written response models vs the generated schema each is built from | a hand-transcribed model expecting a field Gateway no longer sends |
| `kwargs` | keywords passed to generated request models | a misspelled optional field, which pydantic drops in silence |

`references/CHECKS.md` has the detail: what each one exempts and why, and the bug behind
each exemption.

Every check refuses to pass vacuously. A truncated spec, an extraction regex gone stale,
or an empty model is reported as a failure rather than a clean run — a check that
silently matched nothing is how a rename reaches production.

## adopt — following a Gateway change

When `models` fails, the generated file is behind the Gateway you pointed at:

```bash
python3 scripts/regen_models.py --spec "$SPEC" --repo hummingbot
git -C ~/hummingbot diff -- hummingbot/core/gateway/gateway_models.py
```

Read that diff. It is exactly what changed in Gateway, in the shape the client uses.

Then rerun `check_spec.py`. A regenerated model file usually makes `mirrors` and `kwargs`
start reporting call sites — that is the point: the generated file moves first, and it
names the work still to do by hand.

## Reading a failure

A failure means one of two things, and the report cannot tell them apart:

- **The client is stale.** Gateway moved and this side has not followed. Fix the client.
- **The spec is stale.** You generated from a Gateway older than the client targets.
  Regenerate from the right ref.

Check which Gateway you generated from before changing any client code. `keys` in
particular reports plain string literals: if one is not a Gateway field at all — a
config-tree key like `solana.defaultWallet`, or a local sentinel — it belongs in
`config_tree_keys` or `local_constants` in `scripts/repos.py`, named individually so a
genuinely renamed field cannot hide behind the exemption.

## Adding a repo, or fixing a stale extraction

Everything repo-specific lives in `scripts/repos.py`: where each checkout is, which
module builds the requests, the regex that finds its path literals, which modules speak
the wire format, the generated-models file and its target Python version, and the
hand-written models paired with the Gateway schemas they mirror. A third client is a
sixth entry in that table.

If a check reports "the extraction regex has gone stale", the client changed how it
builds requests and the regex in `repos.py` no longer sees them. Fix the regex before
trusting a pass.
