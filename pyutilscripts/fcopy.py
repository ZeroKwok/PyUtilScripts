#! python
# -*- coding: utf-8 -*-
#
# This file is part of the PyUtilScripts project.
# Copyright (c) 2020-2025 zero <zero.kwok@foxmail.com>
#
# For the full copyright and license information, please view the LICENSE
# file that was distributed with this source code.
#
# ###
#
# 1. 以tree -aif命令输出的内容作为文件清单(如下).
# 2. 通过脚本将(directory)原目录下的匹配文件, 拷贝到(output)目标目录.
#
# 语法如下
# fcopy.py [-l,--list FILE] [-d,--directory DIRECTORY] <-o,--output DIRECTORY>
#
# CMD
# python fcopy.py -l ../fcopy.list -d . -o "\\192.168.1.230\2024-01-26 1625"

import os
import sys
import stat
import shutil
import filecmp
import argparse
import traceback
from   termcolor import cprint

def copy_files(source_directory, target_directory, manifest, report:dict):
    for file in manifest:
        source = os.path.normpath(os.path.join(source_directory, file))
        target = os.path.normpath(os.path.join(target_directory, file))

        try:
            fs = os.stat(source)
            if fs.st_mode & stat.S_IFDIR:
                continue
        except FileNotFoundError:
            cprint(f'Failed: SourceFileNotFound -> {source}', 'red', file=sys.stderr)
            report[0].setdefault('SourceFileNotFound', []).append(source)
            continue
        
        if os.path.exists(target):
            if filecmp.cmp(source, target):
                print(f'Skip: SameFile -> {source} -> {target}')
                report[1].setdefault('SkipSameFile', []).append(source)
                continue
            else:
                print(f'Update: {source} -> {target}')
                report[1].setdefault('Update', []).append(source)
        else:
            print(f'Copy: {source} -> {target}')
            report[1].setdefault('Copy', []).append(source)
            os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copy2(source, target)

def read_file_list(file_path):
    with open(file_path, 'r') as file:
        return [line.strip() for line in file.readlines() if not line[0].isdigit()]

def main():
    try:
        parser = argparse.ArgumentParser(description='Copy files from source directory to target directory.')
        parser.add_argument('-l', '--list', default='fcopy.list', help='File containing the list of files to copy.')
        parser.add_argument('-d', '--directory', default='.', help='Source directory where the files are located.')
        parser.add_argument('-o', '--output', required=True, help='Target directory where the files will be copied.')
        parser.add_argument('-v', '--verbose', action='store_true', default=False)
        args = parser.parse_args()
 
        # argparse 默认会保留字符串中的引号
        for key in args.__dict__:
            if type(args.__dict__[key]) == str:
                args.__dict__[key] = args.__dict__[key].strip(' \'"')

        if not args.list or not args.directory or not args.output:
            print("Error: Please provide the required arguments.")
            parser.print_help()
            return

        report = { 0 : {}, 1 : {} }
        manifest = read_file_list(args.list)
        copy_files(args.directory, args.output, manifest, report)

        failed = {}
        success = {}
        for key in report[0]:
            failed[key] = failed.setdefault(key, 0) + len(report[0][key])
        for key in report[1]:
            success[key] = success.setdefault(key, 0) + len(report[1][key])
        failed  = [f'{i}: {failed[i]}' for i in failed]
        success = [f'{i}: {success[i]}' for i in success]

        print()
        if args.verbose:
            print()
            for key in report[0]:
                for f in report[0][key]:
                    cprint(f'{key}: {f}', 'red')
            if 'Update' in report[1]:
                for f in report[1]['Update']:
                    cprint(f'{key}: {f}', 'green')
        cprint(f'{", ".join(success)} {", ".join(failed)}', 'yellow' if failed else 'green')

    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
