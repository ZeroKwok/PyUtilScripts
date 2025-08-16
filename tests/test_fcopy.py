import os
import sys
import types
import pytest
import filecmp
import tempfile
from unittest import mock
from pyutilscripts.fcopy import main

@pytest.fixture
def file_manifest(monkeypatch):
    manifest = tempfile.mktemp()
    monkeypatch.setattr(sys, "argv", ["fcopy.py", "-s", ".", "-l", manifest, "--update-list"])
    monkeypatch.setattr("builtins.input", lambda args=None: "y")
    code = main()
    assert code == 0
    return manifest

def dircmp(dir1, dir2):
    result = filecmp.dircmp(dir1, dir2)
    if not (
        len(result.left_only) == 0
        and len(result.right_only) == 0
        and len(result.diff_files) == 0 ):
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
    monkeypatch.setattr(sys, "argv", ["fcopy.py", "-s", ".", "-l", file_manifest, "-t", target])
    code = main()
    assert code == 0

    assert os.path.isdir(target)
    result = dircmp('.', target)
    assert result
    
    # rename mode
    monkeypatch.setattr(sys, "argv", ["fcopy.py", "-s", ".", "-l", file_manifest, "-t", target, "-m", "r"])
    code = main()
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


