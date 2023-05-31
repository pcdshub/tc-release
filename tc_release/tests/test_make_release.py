from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest
import requests

from ..tc_release import Repo
from ..tc_release import dirname as main_dirname
from ..tc_release import initialize_repo, main, make_release


def set_git_identity(repo: Repo) -> None:
    """
    Sets a local git username/email for commits for a repo.

    This is required or else the GHA CI fails due to no identity.
    """
    repo.config_writer().set_value("user", "name", "pytest").release()
    repo.config_writer().set_value("user", "email", "pytest@test.com").release()


@pytest.mark.parametrize(
    "reponame,plcproj",
    [
        ('lcls-plc-lfe-vac', 'plc_lfe_vac'),
        ('lcls-plc-lfe-motion', None),
        ('lcls-plc-tmo-optics', None),
        ('lcls-twincat-common-components', None),
        ('lcls-twincat-general', None),
        ('lcls-twincat-motion', None),
        ('lcls-twincat-physics', None),
        ('lcls-twincat-pmps', None),
        ('lcls-twincat-vacuum', None),
    ],
)
def test_dry_run(
    monkeypatch: pytest.MonkeyPatch,
    reponame: str,
    plcproj: str | None,
):
    """
    Test that the dry run works on a few repositories.
    """
    # Sanity check: did we pick a real public repo?
    # If not, the git commands may ask for auth during pytest...
    url = f'https://github.com/pcdshub/{reponame}'
    assert requests.head(url).status_code == 200
    # Drop into the subfolder to do the work here
    monkeypatch.chdir(Path(__file__).parent / 'artifacts')
    # Remove any pre-existing folder
    if os.path.exists(reponame):
        shutil.rmtree(reponame)
    # Run the part of the release up to but not including git push
    working_dir = os.path.join(os.getcwd(), reponame)
    repo = initialize_repo(working_dir=working_dir)
    set_git_identity(repo=repo)
    repo_url = f'https://github.com/pcdshub/{reponame}'
    version = '999.999.999'
    major, minor, fix = version.split('.')
    make_release(
        repo=repo,
        working_dir=working_dir,
        full_version_string=f'v{version}',
        repo_url=repo_url,
        select_plcproj=plcproj,
        dry_run=True,
    )
    # Find our version string in the two places it belongs
    # It should be in a file with extension .plcproj embedded in the xml
    if plcproj is None:
        plcproj_path = next(Path(working_dir).rglob('*.plcproj'))
    else:
        plcproj_path = next(Path(working_dir).rglob(f'{plcproj}.plcproj'))
    with plcproj_path.open() as fd:
        assert f'<ProjectVersion>{version}</ProjectVersion>' in fd.read()
    # It should also be in a file named Global_Version.TcGVL with ST struct
    global_version = next(Path(working_dir).rglob('Global_Version.TcGVL'))
    with global_version.open() as fd:
        assert (
            f': ST_LibVersion := (iMajor := {major}, iMinor := {minor}, '
            f"iBuild := {fix}, iRevision := 0, sVersion := '{version}');"
        ) in fd.read()


def test_dry_run_from_main(monkeypatch: pytest.MonkeyPatch):
    """
    For at least one case, go through the full main input.

    This is just to check for exceptions/typos in the invokation of inner
    utilites, which should be tested independently of running through
    main.
    """
    reponame = 'lcls-twincat-general'
    # Sanity check: did we pick a real public repo?
    # If not, the git commands may ask for auth during pytest...
    url = f'https://github.com/pcdshub/{reponame}'
    assert requests.head(url).status_code == 200
    # Drop into the subfolder to do the work here
    monkeypatch.chdir(Path(__file__).parent / 'artifacts')
    # Remove any pre-existing folder
    full_workdir = os.path.join(os.getcwd(), main_dirname)
    if os.path.exists(full_workdir):
        shutil.rmtree(full_workdir)
    # monkeypatch a local git username/email to help the ci

    def local_repo_init(working_dir: str) -> Repo:
        repo = initialize_repo(working_dir=working_dir)
        set_git_identity(repo=repo)
        return repo
    monkeypatch.setattr("tc_release.tc_release.initialize_repo", local_repo_init)
    # Hope for no issues
    assert main([
        '--dry-run',
        'v888.888.888',
        url,
    ]) == 0
