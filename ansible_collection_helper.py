import argparse
import logging
import os
import shlex
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Set


def _test_changed_roles(args: argparse.Namespace) -> None:
    p = args.parent or ["molecule", "roles"]
    parents = [Path(i) for i in p]
    logging.info("inspect for change based on directories: %s", ", ".join(p))
    if any([not pa.exists() or not pa.is_dir() for pa in parents]):
        raise ValueError("At least one parent does not exist or is invalid")
    origin = os.environ.get("COMPARED_BRANCH", "main")
    current = os.environ.get("CI_COMMIT_SHA", "HEAD")
    run_molecule_tests(
        get_subdirs(
            parents=parents,
            potential_children=get_diff(origin, current),
        )
    )


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(__file__)
    subp = p.add_subparsers()
    testp = subp.add_parser("test")
    testp.add_argument(
        "-p",
        "--parent",
        action="append",
        help="Parent directory on which we should check for changes",
    )
    testp.set_defaults(func=_test_changed_roles)
    return p


def run_command(
    cmd: Sequence[str], *, cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    logging.info("running command: %s", shlex.join(cmd))
    try:
        return subprocess.run(cmd, capture_output=True, check=True, text=True, cwd=cwd)
    except subprocess.CalledProcessError as e:
        logging.error(e.stdout)
        logging.error(e.stderr)
        raise e


def get_diff(origin: str, current: str) -> Sequence[Path]:
    """Return paths of changed files between two git branch / hash, that list
    is simply based on git diff result"""
    return [
        Path(f)
        for f in (
            run_command(
                ["git", "diff-tree", "--name-only", "-r", origin, current]
            ).stdout.splitlines()
        )
    ]


def get_subdirs(
    parents: Sequence[Path], potential_children: Sequence[Path]
) -> Set[str]:
    """Return names set direct sub directory (one level under any parents) for
    which there is at least one entry on potential_children.

    >>> parent_locations = [Path('r/f/')]
    >>> potential_children = [Path('r/f/good/foo'), Path('t/'), Path('r/b/')]
    >>> get_subdirs(parent_locations, potential_children)
    {'good'}
    """
    subdir = set()
    for ch in potential_children:
        for p in parents:
            try:
                subdir.add(ch.relative_to(p).parts[0])
            except ValueError:
                # relative_to throw a ValueError
                # if the two path aren't on same hierarchy
                logging.info("%s is not under (parent) %s", str(ch), str(p))
    return subdir


def run_molecule_tests(roles: Set[str]) -> None:
    """Execute molecule tests for a specific set of roles"""
    for role in roles:
        logging.info("execute scenario / tests for roles %s", role)
        run_command(["molecule", "test", "--scenario-name", role])


def main() -> None:
    logging.basicConfig(level="INFO", format="%(levelname)s - %(message)s")
    p = parser()
    args = p.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
