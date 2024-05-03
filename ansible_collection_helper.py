import argparse
import logging
import os
import shlex
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Set

import yaml
from ansible.cli.doc import DocCLI
from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader((Path(__file__).parent / "templates")))
template = env.get_template("readme.jinja2")


def generate_role_documentation(
    role_name: str, role_spec_file: Path, molecule_dir: Path, doc_dir: Path
) -> None:
    """Reads roles metadata and molecule converge playbooks to generate README
    files for a specific role.
    """
    playbook = molecule_dir / role_name / "converge.yml"
    doc = doc_dir / f"role_{role_name}_doc.md"
    with (
        role_spec_file.open() as f_spec,
        playbook.open() as f_play,
        doc.open("w") as f_doc,
    ):
        logging.info("generate README for %s", role_name)
        spec = yaml.safe_load(f_spec)["argument_specs"]["main"]
        options: Sequence[str] = []
        DocCLI.add_fields(options, spec["options"], limit=120, opt_indent="  ")
        f_doc.write(
            template.render(
                role_name=role_name,
                spec=spec,
                options=options,
                example=f_play.read().strip(),
            )
        )


def generate_documentation(
    *, roles_dir: Path, molecule_dir: Path, doc_dir: Path
) -> None:
    """Generates documention (README) for all roles stored on the specified directory.

    To generate them, we parse the argument_specs.yml and the converge.yml
    playbook we use for our molecule tests (on the role named scenario directory).
    """
    logging.info("start generating READMEs")
    for r_spec in roles_dir.glob("*/meta/argument_specs.yml"):
        generate_role_documentation(
            r_spec.parent.parent.parts[-1], r_spec, molecule_dir, doc_dir
        )


def _test_changed_roles(*, parents: Sequence[Path] | None) -> None:
    parents = parents if parents else [Path("molecule"), Path("roles")]
    logging.info(
        "inspect for change based on directories: %s",
        ", ".join([str(p) for p in parents]),
    )
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
        dest="parents",
        type=Path,
        action="append",
        help="Parent directory on which we should check for changes",
    )
    testp.set_defaults(func=_test_changed_roles)
    docp = subp.add_parser("document")
    docp.add_argument(
        "-r",
        "--roles-dir",
        action="store",
        required=True,
        type=Path,
        help="Directory on which roles are stored",
    )
    docp.add_argument(
        "-m",
        "--molecule-dir",
        action="store",
        required=True,
        type=Path,
        help="Directory on which molecule scenario are stored",
    )
    docp.add_argument(
        "-d",
        "--doc-dir",
        action="store",
        default="docs",
        type=Path,
        help="Directory on which we should write documentation pages",
    )
    docp.set_defaults(func=generate_documentation)
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
    is simply based on git diff result
    """
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
    args = vars(p.parse_args())
    if func := args.pop("func", None):
        func(**args)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
