import logging
import os
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Set


def run_command(
    cmd: Sequence[str], *, stdout: int | None = subprocess.PIPE, cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    logging.info("running command: %s", cmd)
    return subprocess.run(cmd, stdout=stdout, check=True, text=True, cwd=cwd)


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
    origin = os.environ.get("COMPARED_BRANCH", "main")
    current = os.environ.get("CI_COMMIT_SHA", "HEAD")
    # list of directories in which we should watch for changes to define
    # the list of testable roles. Currently this is hardcoded, but the
    # idea is to give more control to user and add flags
    # (probably --parent-dir) for those who don't use standard roles and
    # molecule location.
    parents = [Path("roles/"), Path("molecule/")]
    run_molecule_tests(
        get_subdirs(
            parents,
            potential_children=get_diff(origin, current),
        )
    )


if __name__ == "__main__":
    main()
