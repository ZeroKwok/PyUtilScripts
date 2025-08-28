import os
import re
import sys
import types
import pytest
import filecmp
import tempfile
from unittest import mock
from pyutilscripts import fcopy

@pytest.fixture
def file_manifest(monkeypatch):
    manifest = tempfile.mktemp()
    monkeypatch.setattr(sys, "argv", ["fcopy.py", "-s", ".", "-l", manifest, "--update-list"])
    monkeypatch.setattr("builtins.input", lambda args=None: "y")
    code = fcopy.main()
    assert code == 0
    return manifest

def dircmp(dir1, dir2):
    result = filecmp.dircmp(dir1, dir2)
    if not (
        len(result.left_only) == 0
        and len(result.right_only) == 0
        and len(result.diff_files) == 0 ):
        print(f"Directory comparison failed: {result.left_only}, {result.right_only}, {result.diff_files}")
        return False
    for dir in result.common_dirs:
        if not dircmp(os.path.join(dir1, dir), os.path.join(dir2, dir)):
            return False
    return True

def test_update_list(monkeypatch, file_manifest):
    stat = os.stat(file_manifest)
    assert stat.st_size > 0

def test_copy_files_with_update_and_rename(monkeypatch, file_manifest):
    target = tempfile.mktemp()
    monkeypatch.setattr(sys, "argv", ["fcopy.py", "-s", ".", "-l", file_manifest, "-t", target, "-vv"])
    code = fcopy.main()
    assert code == 0

    assert os.path.isdir(target)
    result = dircmp('.', target)
    assert result
    
    # rename mode
    monkeypatch.setattr(sys, "argv", ["fcopy.py", "-s", ".", "-l", file_manifest, "-t", target, "-m", "r"])
    code = fcopy.main()
    assert code == 0

    # Compare file counts: target should have twice as many files as the source directory
    def count_files(directory):
        count = 0
        for root, dirs, files in os.walk(directory):
            count += len(files)
        return count

    source_count = count_files('.')
    target_count = count_files(target)
    assert target_count == 2 * source_count


def test_update_list_with_filter(monkeypatch, file_manifest):
    manifest = tempfile.mktemp()
    monkeypatch.setattr(sys, "argv", ["fcopy.py", "-s", ".", "-l", manifest, "--update-list", "--filter", "filter.txt"])

    # Patch update_file_list
    called = {}
    def fake_read_file_filter(args):
        called['ok'] = True
        return [re.compile(line) for line in ['^file.txt$', '^.+__pycache__.+$', '^\.git.+$']]
    monkeypatch.setattr("pyutilscripts.fcopy.read_file_filter", fake_read_file_filter)
    code = fcopy.main()
    assert code == 0
    assert called.get('ok')
    
    left = fcopy.read_file_list(file_manifest)
    right = fcopy.read_file_list(manifest)
    diff = set(left) - set(right)
    assert diff
    assert 'file.txt' in diff
    assert len(diff) > 2

def test_copy_files_with_filter(monkeypatch, file_manifest):
    target = tempfile.mktemp()
    monkeypatch.setattr(sys, "argv", ["fcopy.py", "-s", ".", "-l", file_manifest, "-t", target, "--filter", "filter.txt"])
    
    # Patch update_file_list
    called = {}
    def fake_read_file_filter(args):
        called['ok'] = True
        return [re.compile(line) for line in ['^file.txt$', '^.+__pycache__.+$', '^\.git.+$']]
    monkeypatch.setattr("pyutilscripts.fcopy.read_file_filter", fake_read_file_filter)
    
    code = fcopy.main()
    assert code == 0

    # Compare file counts: target should have twice as many files as the source directory
    def count_files(directory):
        count = 0
        for root, dirs, files in os.walk(directory):
            count += len(files)
        return count

    source_count = count_files('.')
    target_count = count_files(target)
    assert source_count - target_count > 2