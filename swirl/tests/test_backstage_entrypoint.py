"""
Regression tests for the SWIRL for Backstage container entrypoint.

Defect: `docker compose restart` brought daphne and Redis back but not Celery,
so /swirl/sapi/health/backstage/ stayed on 503 forever. swirl.py writes ./.swirl
in the app directory and refuses to start a service named in it; that file lives
in the container's writable layer, which a restart keeps, so the second start
saw the previous run's pids and gave up:

    entrypoint: starting celery
      celery-worker is already running - remove .swirl if this is incorrect

The fix is docker/backstage/clear_stale_pids.sh, called by the entrypoint before
`swirl.py start`. These tests run that script for real against a throwaway
directory, and check the entrypoint calls it in the right place.

Run with: pytest swirl/tests/test_backstage_entrypoint.py -v
"""

import json
import os
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPT = os.path.join(ROOT, "docker", "backstage", "clear_stale_pids.sh")
ENTRYPOINT = os.path.join(ROOT, "docker", "backstage", "entrypoint.sh")


def run(app_dir):
    return subprocess.run(["sh", SCRIPT, str(app_dir)],
                          capture_output=True, text=True, timeout=30)


def test_the_script_ships_with_the_image():
    assert os.path.exists(SCRIPT)


def test_a_stale_swirl_pid_file_is_removed(tmp_path):
    """The exact state a restarted container is in: pids from the last run."""
    stale = tmp_path / ".swirl"
    stale.write_text(json.dumps({"celery-worker": 41, "celery-beats": 54}))

    result = run(tmp_path)

    assert result.returncode == 0, result.stderr
    assert not stale.exists()
    assert ".swirl" in result.stdout


def test_a_stale_celerybeat_pid_file_is_removed(tmp_path):
    """celery beat refuses to start on its own leftover pid file."""
    stale = tmp_path / "celerybeat.pid"
    stale.write_text("54\n")

    result = run(tmp_path)

    assert result.returncode == 0, result.stderr
    assert not stale.exists()


def test_a_live_pid_in_the_file_does_not_save_it(tmp_path):
    """A pid that names a live process is still cleared.

    Inside a container pids restart at 1 and are reused, so a pid written by
    the previous run very often names an unrelated live process in the next
    one. Validating liveness would keep the wedge rather than clear it, which
    is why the script does not.
    """
    stale = tmp_path / ".swirl"
    stale.write_text(json.dumps({"celery-worker": os.getpid()}))

    assert run(tmp_path).returncode == 0
    assert not stale.exists()


def test_nothing_to_clear_is_not_an_error(tmp_path):
    result = run(tmp_path)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ""


def test_a_missing_app_dir_is_not_an_error(tmp_path):
    result = run(tmp_path / "no-such-directory")
    assert result.returncode == 0, result.stderr


def test_the_entrypoint_clears_the_pid_state_before_starting_celery():
    with open(ENTRYPOINT, "r", encoding="utf-8") as handle:
        body = handle.read()

    assert "clear_stale_pids.sh" in body
    assert body.index("clear_stale_pids.sh") < body.index("swirl.py start"), (
        "the pid state has to be cleared before swirl.py start, or swirl.py "
        "refuses to start the worker")


def test_the_entrypoint_and_the_script_are_executable():
    assert os.access(ENTRYPOINT, os.X_OK)
    assert os.access(SCRIPT, os.X_OK)
