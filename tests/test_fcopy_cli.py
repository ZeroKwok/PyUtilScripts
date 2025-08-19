import sys
import types
import pytest
from unittest import mock
from pyutilscripts import fcopy


@pytest.fixture
def patch_common(monkeypatch):
    # Patch cprint to avoid terminal output
    monkeypatch.setattr("pyutilscripts.fcopy.cprint", lambda *a, **kw: None)
    # Patch print to avoid clutter
    monkeypatch.setattr("builtins.print", lambda *a, **kw: None)

def test_cli_missing_required_args(monkeypatch, patch_common):
    monkeypatch.setattr(sys, "argv", ["fcopy.py"])
    with pytest.raises(SystemExit):
        fcopy.main()

def test_cli_source_dir_not_exist(monkeypatch, patch_common):
    monkeypatch.setattr(sys, "argv", ["fcopy.py", "-s", "notfound", "-t", "target"])
    monkeypatch.setattr("os.path.isdir", lambda p: False)
    code = fcopy.main()  # Should print error and return 1
    assert code == 1

def test_cli_update_list(monkeypatch, patch_common):
    monkeypatch.setattr(sys, "argv", ["fcopy.py", "-s", "src", "--update-list"])
    monkeypatch.setattr("os.path.isdir", lambda p: True)
    # Patch update_file_list to check it's called
    called = {}
    def fake_update(args):
        called['ok'] = True
        return 0
    monkeypatch.setattr("pyutilscripts.fcopy.update_file_list", fake_update)
    code = fcopy.main()
    assert called.get('ok')
    assert code == 0

def test_cli_copy_files_dry_run(monkeypatch, patch_common):
    monkeypatch.setattr(sys, "argv", ["fcopy.py", "-s", "src", "-t", "target", "--dry-run"])
    monkeypatch.setattr("os.path.isdir", lambda p: True)
    # Patch read_file_list to return a manifest
    monkeypatch.setattr("pyutilscripts.fcopy.read_file_list", lambda f,c,k: ["file1.txt"])
    # Patch make_actions to return actions
    monkeypatch.setattr("pyutilscripts.fcopy.make_actions", lambda args: [fcopy.Action("c", "file1.txt", "")])
    # Patch copy_files to check it's called
    called = {}
    def fake_copy(args):
        called['ok'] = True
        return 0
    monkeypatch.setattr("pyutilscripts.fcopy.copy_files", fake_copy)
    code = fcopy.main()
    assert called.get('ok')
    assert code == 0

def test_cli_target_missing(monkeypatch, patch_common):
    monkeypatch.setattr(sys, "argv", ["fcopy.py", "-s", "src"])
    monkeypatch.setattr("os.path.isdir", lambda p: True)
    code = fcopy.main()  # Should print error and return
    assert code == 1

def test_cli_debug_mode(monkeypatch, patch_common):
    monkeypatch.setattr(sys, "argv", ["fcopy.py", "-s", "src", "-t", "target", "--debug"])
    monkeypatch.setattr("os.path.isdir", lambda p: True)
    monkeypatch.setattr("builtins.input", lambda *a, **kw: "")
    monkeypatch.setattr("pyutilscripts.fcopy.copy_files", lambda args: None)
    fcopy.main()
