#!/usr/bin/env python3
"""Compare the hummingbot and hummingbot-api Gateway clients against a Gateway spec.

Both clients are hand-written against an API defined in the gateway repository, so a
rename there is invisible on this side until a call 404s at runtime -- mid-trade -- or a
`.get()` reads None and a fee of zero gets recorded. This reads both clients out of
source and holds them against one OpenAPI document.

    python3 check_spec.py --spec /path/to/openapi.json

Five checks, each guarding a different way the two sides drift apart:

  routes   every path the client calls exists in the spec
  keys     every camelCase key the client writes or reads is declared in the spec
  models   the committed generated-models file is what this spec produces
  mirrors  hand-written response models declare only fields Gateway sends
  kwargs   every keyword passed to a generated request model is a field of it

Nothing is imported from either repo -- the models are read with `ast` -- so no conda
environment is needed and both repos can be checked from one interpreter.
"""
import argparse
import ast
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from repos import REPOS, SEGMENT_VALUES, UNSCHEMAD_ROUTES  # noqa: E402

CAMEL_CASE = re.compile(r'["\']([a-z][a-zA-Z0-9]*[A-Z][a-zA-Z0-9]*)["\']')
# `ModelNameRequest(\n    key=..., ...)` -- the shape every model-built call site uses.
MODEL_CALL = re.compile(r"\b([A-Z][A-Za-z0-9]*Request)\(\s*\n((?:\s+\w+=.*\n)+)")
MODEL_KWARG = re.compile(r"^\s+(\w+)=", re.M)

LP_METHOD = re.compile(r"\s*async def (\w+)\(")
LP_TRADING_TYPE = re.compile(r'\s*trading_type: str = "(\w+)"')
LP_ROUTE = re.compile(r'_lp_route\([a-z_]+,\s*"([a-z-]+)"\)')


class Failure(Exception):
    """A check found real drift, with the detail the reader needs to act on it."""


# --------------------------------------------------------------------------- spec

def spec_paths(spec: dict) -> set:
    return set(spec.get("paths", {}))


def spec_field_names(spec: dict) -> set:
    """Every property and query-parameter name anywhere in the spec.

    Query parameters have to be collected alongside schema properties: Gateway's reads
    are GETs, so their fields live under `parameters` and never reach components.schemas.
    """
    names = set()

    def walk(node):
        if isinstance(node, list):
            for item in node:
                walk(item)
            return
        if not isinstance(node, dict):
            return
        for key, value in node.items():
            if key == "properties" and isinstance(value, dict):
                names.update(value)
            if key == "parameters" and isinstance(value, list):
                names.update(p["name"] for p in value if isinstance(p, dict) and "name" in p)
            walk(value)

    walk(spec)
    return names


def shape(path: str) -> str:
    """Compare by segment shape: the spec names ids differently ({address} vs {token})."""
    return re.sub(r"\{[^}]+\}", "{}", path.split("?")[0].rstrip("/"))


def expand(path: str) -> list:
    candidates = [f"/{path.lstrip('/')}"]
    for token, values in SEGMENT_VALUES.items():
        if any(token in c for c in candidates):
            candidates = [c.replace(token, v) for c in candidates for v in values]
    return candidates


# --------------------------------------------------------------------------- source

def wire_names_by_class(source: str) -> dict:
    """{ClassName: {field name as it travels on the wire}} for every pydantic model.

    The wire name is the alias where one is set, the attribute name otherwise -- the same
    rule `(field.alias or name)` applies at runtime, read statically so neither repo has
    to be importable.
    """
    classes = {}
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.ClassDef):
            continue
        names = set()
        for statement in node.body:
            if not isinstance(statement, ast.AnnAssign) or not isinstance(statement.target, ast.Name):
                continue
            attr = statement.target.id
            if attr.startswith("_") or attr == "model_config":
                continue
            names.add(_alias(statement.value) or attr)
        if names:
            classes[node.name] = names
    return classes


def field_names_by_class(source: str) -> dict:
    """{ClassName: {attribute name} | {alias}} -- both spellings a keyword may use."""
    classes = {}
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.ClassDef):
            continue
        names = set()
        for statement in node.body:
            if not isinstance(statement, ast.AnnAssign) or not isinstance(statement.target, ast.Name):
                continue
            attr = statement.target.id
            if attr.startswith("_") or attr == "model_config":
                continue
            names.add(attr)
            alias = _alias(statement.value)
            if alias:
                names.add(alias)
        classes[node.name] = names
    return classes


def _alias(value) -> str:
    """The `alias=` of a `Field(...)` call, or "" when there is none."""
    if not isinstance(value, ast.Call):
        return ""
    for keyword in value.keywords:
        if keyword.arg == "alias" and isinstance(keyword.value, ast.Constant):
            return keyword.value.value
    return ""


def lp_routes(source: str) -> set:
    """LP paths assembled by _lp_route, each resolved with its method's default type.

    Each verb is paired with its own method's `trading_type` default rather than tried
    against both types, because the LP surfaces are not symmetric: collect-fees is CLMM
    only, and pairing every verb with every type invents routes nobody calls.
    """
    routes, trading_type = set(), None
    for line in source.splitlines():
        if LP_METHOD.match(line):
            trading_type = None
        default = LP_TRADING_TYPE.match(line)
        if default:
            trading_type = default.group(1)
        verb = LP_ROUTE.search(line)
        if verb:
            if not trading_type:
                raise Failure(
                    f"_lp_route(..., {verb.group(1)!r}) sits in a method with no "
                    "`trading_type: str = ...` default, so this check cannot tell which "
                    "surface it targets. Give the parameter a default, or check it by hand."
                )
            routes.add(f"trading/{trading_type}/{verb.group(1)}")
    return routes


# --------------------------------------------------------------------------- checks

def check_routes(repo: dict, root: Path, spec: dict) -> str:
    source = (root / repo["client"]).read_text()
    called = set(re.findall(repo["path_regex"], source, re.MULTILINE))
    if repo["lp_routes"]:
        called |= lp_routes(source)

    # Guard the guard: a regex that matched nothing would pass the real check vacuously.
    if len(called) < 15:
        raise Failure(
            f"Only {len(called)} paths found in {repo['client']}. The extraction regex has "
            "gone stale -- fix it in repos.py before trusting a pass here."
        )
    shapes = {shape(p) for p in spec_paths(spec)}
    if len(shapes) < 20:
        raise Failure(f"Only {len(shapes)} paths in the spec -- is it truncated?")

    missing = [
        candidate
        for call in sorted(called)
        for candidate in expand(call)
        if shape(candidate) not in shapes and candidate not in UNSCHEMAD_ROUTES
    ]
    if missing:
        raise Failure(
            "The client calls paths this Gateway does not serve:\n    "
            + "\n    ".join(missing)
            + "\n  Either the client is stale and should follow the rename, or the spec is "
            "from a Gateway older than the client targets."
        )
    return f"{len(called)} client routes, all served by the spec's {len(shapes)}"


def check_keys(repo: dict, root: Path, spec: dict) -> str:
    declared = spec_field_names(spec)
    if len(declared) < 100:
        raise Failure(f"Only {len(declared)} field names in the spec -- is it truncated?")

    unknown, counted = [], 0
    for relative in repo["wire_sources"]:
        used = set(CAMEL_CASE.findall((root / relative).read_text()))
        if len(used) < 3:
            raise Failure(f"Only {len(used)} camelCase keys found in {relative} -- regex stale?")
        counted += len(used)
        unknown += [
            f"{key}  ({Path(relative).name})"
            for key in used - declared - repo["config_tree_keys"] - repo["local_constants"]
        ]
    if unknown:
        raise Failure(
            "The client sends or reads keys this Gateway's spec does not declare:\n    "
            + "\n    ".join(sorted(unknown))
            + "\n  Either the caller is stale and should follow the rename, or the string is "
            "not a Gateway field at all -- see config_tree_keys and local_constants in repos.py."
        )
    return f"{counted} camelCase keys, all declared by the spec"


def check_models(repo: dict, root: Path, spec: dict, spec_path: Path, codegen: list) -> str:
    """Regenerating from this spec must reproduce the committed file exactly.

    The models are committed so they import without a build step and so a Gateway change
    reads as a diff. That only holds while the committed copy is what the spec produces --
    a hand-edit, or a spec refreshed without rerunning the generator, and the mirrors and
    kwargs checks below start comparing against a shape Gateway never described.
    """
    if not spec.get("components", {}).get("schemas"):
        raise Failure(
            "This spec declares no components.schemas, so there is nothing to generate "
            "models from. Gateway inlined its schemas until it adopted shared components "
            "-- against a Gateway that old, run the routes and keys checks only."
        )
    committed = root / repo["generated"]
    # Generated beside the committed file, not in /tmp, because the generator's `black`
    # and `isort` passes discover their settings by walking up from the file they format.
    # Both repos set line_length in pyproject.toml, and hummingbot's isort also sets
    # conda_env -- so the same spec formatted in a temp directory comes out wrapped
    # differently and every run would report drift that is not there.
    scratch = committed.with_name(f".{committed.stem}_speccheck.py")
    try:
        _generate(codegen, spec_path, scratch, repo, root)
        if scratch.read_text() != committed.read_text():
            raise Failure(
                f"{repo['generated']} is not what this spec generates. Rewrite it with:\n"
                f"    python3 scripts/regen_models.py --spec {spec_path} --repo {repo['name']}\n"
                "  and read the diff: it is exactly what changed in Gateway. If it is all\n"
                "  formatting and no renames, the committed file came from a different\n"
                f"  generator version than this run's ({codegen_version(codegen)}) --\n"
                "  pin the one the repo used with $GATEWAY_SPEC_CODEGEN."
            )
    finally:
        scratch.unlink(missing_ok=True)
    return f"{repo['generated']} is byte-identical to what this spec generates"


def _header(committed: Path) -> str:
    """The committed file's own header, kept rather than rebuilt."""
    return "\n".join(committed.read_text().splitlines()[:2])


def _generate(codegen: list, spec_path: Path, output: Path, repo: dict, root: Path) -> None:
    """Run datamodel-code-generator the way the repo's committed file was produced."""
    result = subprocess.run(
        codegen + [
            "--input", str(spec_path),
            "--input-file-type", "openapi",
            "--openapi-scopes", "schemas",
            "--output", str(output),
            "--output-model-type", "pydantic_v2.BaseModel",
            "--snake-case-field",
            # The repo's python_requires floor, not the interpreter running this: 3.12
            # emits StrEnum, which 3.10 does not have, so the file differs by target.
            "--target-python-version", repo["target_python"],
            "--disable-timestamp",
            # Keeps `connector`/`network` as plain strings. Gateway constrains them by
            # enum so its docs can offer dropdowns, but generating those as Python enums
            # would bake a venue roster into the client: a connector Gateway added later
            # would be rejected before the request left the process. It also removes the
            # only classes the generator had to number (Connector9, Connector15, ...),
            # which any unrelated route insertion renamed.
            "--ignore-enum-constraints",
            "--formatters", "black",
            "--formatters", "isort",
            "--custom-file-header", _header(root / repo["generated"]),
        ],
        # From the repo root, so isort resolves `conda_env` and both formatters read the
        # repo's pyproject.toml rather than whatever the caller happened to cd into.
        cwd=root, capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise Failure(f"datamodel-codegen failed:\n{result.stderr}")


def check_mirrors(repo: dict, root: Path) -> str:
    """Hand-written response models may declare only fields Gateway actually sends.

    Each is built by handing Gateway's response straight to pydantic, so a field Gateway
    does not send reads as its default forever rather than raising. The reverse is
    deliberate: Gateway sends fields this side has no use for, and pydantic drops them.
    """
    mirrors = repo["mirrors"]
    hand_written = wire_names_by_class((root / mirrors["file"]).read_text())
    generated = wire_names_by_class((root / repo["generated"]).read_text())

    problems = []
    for mirror_name, schema_name in mirrors["pairs"]:
        if mirror_name not in hand_written:
            raise Failure(f"{mirror_name} is not a model in {mirrors['file']} -- repos.py is stale")
        if schema_name not in generated:
            raise Failure(
                f"{schema_name} is not in {repo['generated']}. Gateway renamed the schema "
                f"{mirror_name} mirrors, or dropped it -- repair the pairing in repos.py."
            )
        # A mirror with no fields would satisfy the subset check trivially.
        if len(hand_written[mirror_name]) < 3 or len(generated[schema_name]) < 3:
            raise Failure(f"{mirror_name}/{schema_name} looks empty -- the AST read went wrong")
        extra = sorted(hand_written[mirror_name] - generated[schema_name] - mirrors["locally_populated"])
        if extra:
            problems.append(
                f"{mirror_name} declares {extra}, which Gateway's {schema_name} does not send"
            )
    if problems:
        raise Failure(
            "\n    ".join(["Hand-written models expect fields Gateway no longer sends:"] + problems)
            + "\n  Those fields are populated from Gateway's response, so they read as their "
            "defaults forever rather than raising. Follow the rename, or drop them."
        )
    return f"{len(mirrors['pairs'])} hand-written models match the schemas they mirror"


def check_kwargs(repo: dict, root: Path) -> str:
    """Every keyword passed to a generated request model must be a field of it.

    Pydantic ignores an unknown keyword. On a required field that still fails loudly --
    the real one goes missing -- but `slippagePc=1` for `slippagePct` is dropped in
    silence, and the request goes out without the slippage the caller asked for.
    """
    fields = field_names_by_class((root / repo["generated"]).read_text())
    calls = [
        (m.group(1), MODEL_KWARG.findall(m.group(2)))
        for m in MODEL_CALL.finditer((root / repo["client"]).read_text())
    ]
    if len(calls) < 10:
        raise Failure(
            f"Only {len(calls)} model constructions found in {repo['client']} -- has the "
            "regex gone stale, or did the /trading methods go back to hand-written dicts?"
        )

    unknown = []
    for model_name, kwargs in calls:
        if model_name not in fields:
            raise Failure(
                f"{model_name} is not in {repo['generated']}. Gateway renamed or dropped "
                "the request schema the client builds from."
            )
        unknown += [f"{model_name}.{k}" for k in kwargs if k not in fields[model_name]]
    if unknown:
        raise Failure(
            "The client passes keywords no generated model declares:\n    "
            + "\n    ".join(sorted(unknown))
            + "\n  Pydantic drops an unknown keyword, so an optional one goes missing in "
            "silence. Follow the rename, or correct the spelling."
        )
    return f"{len(calls)} model constructions, every keyword a real field"


# --------------------------------------------------------------------------- driver

def codegen_command() -> list:
    """How to reach datamodel-code-generator on this machine.

    The generated file is compared byte for byte, so which version produces it matters: a
    generator release that changes its formatting reads as drift that is not there. Set
    $GATEWAY_SPEC_CODEGEN to pin one, e.g.
        GATEWAY_SPEC_CODEGEN="uvx --from datamodel-code-generator==0.75.1 datamodel-codegen"
    """
    override = os.environ.get("GATEWAY_SPEC_CODEGEN")
    if override:
        return shlex.split(override)
    if shutil.which("uvx"):
        return ["uvx", "--from", "datamodel-code-generator", "datamodel-codegen"]
    if subprocess.run(
        [sys.executable, "-c", "import datamodel_code_generator"], capture_output=True
    ).returncode == 0:
        return [sys.executable, "-m", "datamodel_code_generator"]
    raise SystemExit(
        "The models check needs datamodel-code-generator and found neither `uvx` nor an\n"
        "importable copy. Install uv (https://docs.astral.sh/uv/) or run\n"
        f"    {sys.executable} -m pip install datamodel-code-generator\n"
        "Or skip it with --check routes,keys,mirrors,kwargs."
    )


def codegen_version(codegen: list) -> str:
    result = subprocess.run(codegen + ["--version"], capture_output=True, text=True)
    return result.stdout.strip().splitlines()[-1] if result.returncode == 0 else "datamodel-codegen"


ALL_CHECKS = ["routes", "keys", "models", "mirrors", "kwargs"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--spec", required=True, type=Path, help="Gateway openapi.json to check against")
    parser.add_argument("--repo", default="all", help=f"{', '.join(REPOS)}, or all (default)")
    parser.add_argument("--check", default="all", help=f"comma-separated: {','.join(ALL_CHECKS)}, or all")
    parser.add_argument("--hummingbot", type=Path, help="override the hummingbot checkout")
    parser.add_argument("--hummingbot-api", type=Path, help="override the hummingbot-api checkout")
    args = parser.parse_args()

    if not args.spec.is_file():
        raise SystemExit(f"No spec at {args.spec}. Generate one with scripts/generate_spec.sh")
    spec = json.loads(args.spec.read_text())

    names = list(REPOS) if args.repo == "all" else [args.repo]
    for name in names:
        if name not in REPOS:
            raise SystemExit(f"Unknown repo {name!r}. Known: {', '.join(REPOS)}")
    checks = ALL_CHECKS if args.check == "all" else [c.strip() for c in args.check.split(",")]
    for check in checks:
        if check not in ALL_CHECKS:
            raise SystemExit(f"Unknown check {check!r}. Known: {', '.join(ALL_CHECKS)}")

    codegen = codegen_command() if "models" in checks else []
    overrides = {"hummingbot": args.hummingbot, "hummingbot-api": args.hummingbot_api}

    print(f"Gateway spec: {args.spec}  ({len(spec_paths(spec))} paths, "
          f"{len(spec.get('components', {}).get('schemas', {}))} schemas)")
    if codegen:
        print(f"Generator:    {codegen_version(codegen)}")
    print()

    failed = 0
    for name in names:
        repo = dict(REPOS[name], name=name)
        root = (overrides[name] or repo["root"]).expanduser()
        print(f"{name}  ({root})")
        if not (root / repo["client"]).is_file():
            print(f"  ! no {repo['client']} under {root} -- point at the checkout with "
                  f"--{name} or ${'HUMMINGBOT_API_DIR' if name.endswith('api') else 'HUMMINGBOT_DIR'}")
            failed += 1
            print()
            continue
        for check in checks:
            try:
                if check == "routes":
                    detail = check_routes(repo, root, spec)
                elif check == "keys":
                    detail = check_keys(repo, root, spec)
                elif check == "models":
                    detail = check_models(repo, root, spec, args.spec, codegen)
                elif check == "mirrors":
                    detail = check_mirrors(repo, root)
                else:
                    detail = check_kwargs(repo, root)
            except Failure as failure:
                failed += 1
                print(f"  FAIL {check:8} {failure}")
            else:
                print(f"  ok   {check:8} {detail}")
        print()

    print("Every check passed." if not failed else f"{failed} check(s) failed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
