
import os
import shlex
import pytest
from unittest import mock
from pyutilscripts import fcopy

valid = [
'c file1.txt',
'c file3.txt -> file(3).txt',
' s file2.txt  -> file(2).txt',
' s "fi le2.txt"  -> "fi le(2).txt"',
" s 'fi le2.txt'  -> 'fi le(2).txt'",
' s "fi le2.txt"',
" s 'fi #le2.txt'",
'o file2.txt',
'o sss\\file2.txt',
'o sss//file2.txt',

'o sss//file2##.txt',
'o sss//file2##.txt # comment here',
'o sss//file2##.txt #comment here',
" s 'fi le2.txt'  -> 'fi le(2).txt' #comment",
]

invalid = [
' s fi le2.txt"',
' s "fi le2.txt',
]

def debug_actions_parse():
    for index, line in enumerate(valid + invalid, 0):
        try:
            fields = shlex.split(line, posix=os.name != 'nt')
            print(f'{index} fields: {fields}')

            # remove comments fields
            result = []
            for f in fields:
                if f.startswith('#'):
                    break
                result.append(f)
            fields = result

            if len(fields) == 2: 
                action, file1, file2 = fields + ['']
            elif len(fields) >= 4 and '->' in fields:
                action, file1, _, file2 = fields
            else:
                print(f'    Invalid line: {line}')
                continue

            print('    parse as: ', action, file1, file2)
        except Exception as e:
            print(f'    Invalid line: {line}, error: {e}')
            continue

def test_actions_parse(monkeypatch):
    files = fcopy.parse_actions(valid)
    assert len(files) == len(valid)
    with pytest.raises(ValueError):
        files = fcopy.parse_actions(invalid)

