import os
import shutil
from pathlib import Path

import pytest

from tc_release.tc_release import initialize_repo, main, make_release


@pytest.mark.parametrize(
    "reponame",
    [
        'lcls-plc-kfe-vacuum',
        'lcls-plc-lfe-motion',
        'lcls-plc-tmo-optics',
        'lcls-twincat-common-components',
        'lcls-twincat-general',
        'lcls-twincat-motion',
        'lcls-twincat-physics',
        'lcls-twincat-pmps',
        'lcls-twincat-vacuum',
    ],
)
def test_dry_run(
    monkeypatch: pytest.MonkeyPatch,
    reponame: str,
):
    """
    Test that the dry run works on a few repositories.
    """
    # Drop into the subfolder to do the work here
    monkeypatch.chdir('artifacts')
    # Remove any pre-existing folder
    if os.path.exists(reponame):
        shutil.rmtree(reponame)
    # Run the part of the release up to but not including git push
    working_dir = os.getcwd()
    repo = initialize_repo(working_dir=working_dir)
    repo_url = f'https://github.com/pcdshub/{reponame}'
    version = '999.999.999'
    major, minor, fix = version.split('.')
    make_release(
        repo=repo,
        working_dir=working_dir,
        full_version_string=f'v{version}',
        repo_url=repo_url,
        dry_run=True,
    )
    # Find our version string in the two places it belongs
    # It should be in a file with extension .plcproj embedded in the xml
    plcproj = next(Path(working_dir).rglob('*.plcproj'))
    with plcproj.open() as fd:
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
    # Drop into the subfolder to do the work here
    monkeypatch.chdir('artifacts')
    # Remove any pre-existing folder
    if os.path.exists(reponame):
        shutil.rmtree(reponame)
    # Hope for no issues
    assert main([
        'tc-release',
        'v888.888.888',
        'https://github.com/pcdshub/lcls-twincat-general',
    ]) == 0
