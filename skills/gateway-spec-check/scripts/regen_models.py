#!/usr/bin/env python3
"""Rewrite a repo's generated Gateway models from a spec, in place.

The `models` check in check_spec.py reports that the committed file is not what a given
Gateway produces. This is how you adopt that change: it rewrites the file, and the git
diff that follows is exactly what changed in Gateway -- reviewable, rather than a
9,000-line spec dump nobody reads.

    python3 regen_models.py --spec /tmp/openapi.json --repo hummingbot

Rerun check_spec.py afterwards. A regenerated model file usually makes the mirrors and
kwargs checks start reporting the call sites that now have to follow the rename -- which
is the point: the generated file moves first, and it names the work.
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_spec import Failure, _generate, codegen_command  # noqa: E402
from repos import REPOS  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--repo", required=True, choices=list(REPOS))
    parser.add_argument("--root", type=Path, help="override the checkout location")
    args = parser.parse_args()

    if not args.spec.is_file():
        raise SystemExit(f"No spec at {args.spec}. Generate one with scripts/generate_spec.sh")

    repo = REPOS[args.repo]
    root = (args.root or repo["root"]).expanduser()
    target = root / repo["generated"]
    if not target.is_file():
        raise SystemExit(f"No {repo['generated']} under {root}. Point at the checkout with --root.")

    try:
        _generate(codegen_command(), args.spec, target, repo, root)
    except Failure as failure:
        raise SystemExit(str(failure))

    print(f"Rewrote {target}")
    diff = subprocess.run(
        ["git", "-C", str(root), "diff", "--stat", "--", repo["generated"]],
        capture_output=True, text=True,
    ).stdout
    print(diff or "  (no change -- it already matched this spec)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
