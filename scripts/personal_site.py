"""Nonmutating personal-site planning and observation checks; no network/approval authority."""
import argparse
import json
import re
from pathlib import Path
import importlib.util
_spec = importlib.util.spec_from_file_location('personal_public_paths', Path(__file__).with_name('public_paths.py'))
_public_paths = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_public_paths)

def plan(username, branch, repository_exists=False, local_exists=False):
    if not isinstance(username, str) or not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?", username) or "--" in username:
        raise ValueError("Invalid personal GitHub username")
    if not isinstance(branch, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", branch) or any(x in branch for x in ("..", "//", "@{")) or any(x.startswith(".") or x.endswith((".", ".lock")) for x in branch.split("/")) or branch.endswith("/"):
        raise ValueError("Invalid publishing branch")
    user = username.lower()
    repo = user + ".github.io"
    return dict(username=user, repository=repo, remote=f"https://github.com/{user}/{repo}", site_url=f"https://{repo}/", branch=branch, source="/docs", method="branch-docs", action="inspect_existing" if repository_exists or local_exists else "propose_new", steps=["review", "render", "verify_public_files", "commit", "push", "configure_pages", "verify_deployment", "inspect_live_site"])

def private_path(path):
    return _public_paths.private_path(path)

def check(p, o):
    canonical = plan(p["username"], p["branch"])
    errors = []
    for key in ("repository", "remote", "site_url", "source", "method"):
        if p.get(key) != canonical[key]:
            errors.append("plan_" + key)
    if p.get("action") != "propose_new":
        errors.append("existing_project_requires_assessment")
    expected = {"repository": p["repository"], "owner": p["username"], "branch": p["branch"], "site_url": p["site_url"], "output_dir": "docs", "pages_source": "/docs", "pages_method": "branch-docs"}
    for key, value in expected.items():
        if o.get(key) != value:
            errors.append(key)
    paths = o.get("public_files")
    if not isinstance(paths, list) or not paths or any(private_path(x) for x in paths):
        errors.append("public_files")
    elif not {"docs/index.html", "docs/.nojekyll"}.issubset(paths):
        errors.append("publishing_files")
    for key in ("identity_verified", "visibility_verified", "privacy_review", "root_review", "assets_and_links_review"):
        if o.get(key) is not True:
            errors.append(key)
    commit = o.get("intended_commit")
    if not isinstance(commit, str) or not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", commit) or o.get("deployed_commit") != commit:
        errors.append("deployment_commit")
    if o.get("deployment_status") != "success":
        errors.append("deployment_status")
    return dict(deployment_verified=not errors, blockers=errors, evidence_type="operator_observations_not_independent_verification")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    a = sub.add_parser("plan")
    a.add_argument("username"); a.add_argument("branch")
    a.add_argument("--repository-exists", action="store_true")
    a.add_argument("--local-exists", action="store_true")
    a = sub.add_parser("check")
    a.add_argument("plan"); a.add_argument("observations")
    args = parser.parse_args()
    if args.command == "plan":
        result = plan(args.username, args.branch, args.repository_exists, args.local_exists)
    else:
        from pathlib import Path
        result = check(json.loads(Path(args.plan).read_text(encoding="utf-8")), json.loads(Path(args.observations).read_text(encoding="utf-8")))
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
