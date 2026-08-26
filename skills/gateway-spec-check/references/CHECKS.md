# What each check does, and the bug behind each exemption

Every exemption below is written out as a named constant rather than a pattern, so a
genuinely renamed field cannot slip through one. If you add to one, say what it is and
where it lives.

## routes

Reads the path literals each client hands to its request method — `api_request()` in
hummingbot, `_request()` in hummingbot-api — and checks each against `paths` in the spec.

Comparison is by *segment shape*: `{...}` collapses to `{}`, because the spec names its
ids differently from the client (`{address}` vs `{token}`). Interpolated segments the
client chooses at runtime are expanded to every value they can take —
`trading/{trading_type}/quote-swap` is checked as all three of router, clmm and amm —
so the check stays exact instead of pattern-matching.

**hummingbot's LP routes never appear as a literal.** `_lp_route(trading_type, verb)`
assembles them and hands the result to `api_request` as a variable, so the literal regex
cannot see them. They are read separately, pairing each verb with its own method's
`trading_type` default rather than trying both surfaces — the LP surfaces are not
symmetric (`collect-fees` is CLMM only), and pairing every verb with every type invents
routes nobody calls. While this was not done, three LP routes sat on Gateway's pre-rename
names (`quote-position`, `add-liquidity`, `remove-liquidity`) and the check reported
everything fine.

### Exemption: `UNSCHEMAD_ROUTES`

Real Gateway routes that carry no TypeBox schema, so `@fastify/swagger` leaves them out
of the document. Today that is `/restart` — `server.post('/restart')` in `src/app.ts`,
no schema attached. Each is named with where it lives so the exemption is reviewable and
a genuinely deleted route cannot hide behind it.

## keys

Reads every camelCase string literal out of the modules that speak Gateway's wire format
and checks each against every property name and query-parameter name anywhere in the
spec.

Query parameters have to be collected alongside `components.schemas` properties: Gateway's
reads are GETs, so their fields live under a route's `parameters` and never reach the
shared schemas.

This is the check that catches the silent half of drift. These modules write camelCase
keys into query strings and JSON bodies and read them back with `.get()`, so a renamed
field does not raise — it reads `None`, and a strategy acts on a price or balance of zero.
`gateway_base.approve_token` read `gasPrice` from a response whose schema is
`{signature, status, data}`, recording a gas price of 0 on every approval.

### Exemption: `config_tree_keys`

Keys that address Gateway's YAML config tree rather than an HTTP field. `/config` returns
the config as-is, so these arrive as namespaced names (`solana.defaultWallet`,
`apiKeys.helius`) that no route schema declares.

### Exemption: `local_constants`

camelCase strings that are the repo's own values, not Gateway field names — the regex
cannot tell a dict key from any other string literal. Today: `txDataUnavailable`, the
sentinel `gateway_base` invents for a transaction whose data it could not read.

## models

Regenerates the committed generated-models file from the spec and compares byte for byte.

The models are committed so they import without a build step and so a Gateway change
reads as a diff. That only holds while the committed copy is what the spec produces — a
hand-edit, or a spec refreshed without rerunning the generator, and `mirrors` and
`kwargs` start comparing against a shape Gateway never described. This check is what
makes the other two honest.

Two details decide whether the regenerated file matches:

- **Target Python version.** hummingbot generates for 3.10 and hummingbot-api for 3.12,
  each repo's `python_requires` floor rather than whatever interpreter is to hand.
  Targeting 3.12 emits `StrEnum`, which 3.10 does not have, so the same spec produces a
  different file.
- **Where the file is written.** `black` and `isort` discover their settings by walking
  up from the file they format, and both repos set `line_length` in `pyproject.toml`
  (hummingbot's isort also sets `conda_env`). Generating into a temp directory picks up
  neither, wraps the imports differently, and reports drift that is not there — so the
  check generates beside the committed file and deletes the scratch copy afterwards.

`--ignore-enum-constraints` keeps `connector` and `network` as plain strings. Gateway
constrains them by enum so its docs can offer dropdowns, but generating those as Python
enums would bake a venue roster into the client: a connector Gateway added after the last
refresh would be rejected before the request left the process. It also removes the only
classes the generator had to number (`Connector9`, `Connector15`, …), which any unrelated
route insertion renamed.

A third thing decides it, and it is not in the spec at all: **the generator version**.
The file is compared byte for byte, so a `datamodel-code-generator` release that changes
its formatting reads as drift. The run header names the version that ran, and a failure
says to check for that case. `$GATEWAY_SPEC_CODEGEN` overrides the command outright —
`uvx --from datamodel-code-generator==0.75.1 datamodel-codegen` pins a version without
installing it. If a diff is all formatting and no renames, that is what happened.

A Gateway old enough to inline its schemas has no `components.schemas` and nothing to
generate from. The check says so and stops, rather than reporting a codegen error.

## mirrors

Some response models are hand-transcribed rather than generated: each field carries the
camelCase alias of a Gateway response field, and the model is built by handing Gateway's
response straight to pydantic. A field Gateway stops sending therefore stops arriving —
as a default, in silence.

This holds each hand-written model against the generated model of the schema it is built
from, and fails if it declares a field that schema does not carry. Field names are read
statically with `ast` — alias where one is set, attribute name otherwise, the same rule
`(field.alias or name)` applies at runtime — so neither repo has to be importable.

The reverse direction is deliberate, not a defect: Gateway sends fields these repos have
no use for, and pydantic drops them.

### Exemption: `locally_populated`

Fields a model adds for its own use, filled in after construction. hummingbot's position
models carry `base_token` and `quote_token`, populated from token metadata, so Gateway
never sends them and their absence from its schema is correct.

### The pairing itself

`mirrors.pairs` in `repos.py` maps each hand-written model to its Gateway schema. A model
appears once per schema it is fed from: hummingbot-api's `AMMTransactionResponse` is
built from both `AmmAddLiquidityResponse` and `AmmRemoveLiquidityResponse`, and each must
independently satisfy it. If Gateway renames a schema, the check reports the pairing as
broken rather than passing on a name that no longer exists.

## kwargs

The `/trading` methods no longer spell their keys as literals — they build each request
from a generated model, so the names are keyword arguments. Pydantic catches a misspelled
*required* field, because the real one then goes missing. It silently drops a misspelled
optional one: `slippagePc=1` for `slippagePct` sends the request without the slippage the
caller asked for.

This reads the `ModelNameRequest(\n key=..., ...)` call sites out of the client and holds
each keyword against that model's fields, accepting either spelling — the attribute name
or the alias — since both construct the model.
