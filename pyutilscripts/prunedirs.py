#! python
# -*- coding: utf-8 -*-
#
# This file is part of the PyUtilScripts project.
# Copyright (c) 2020-2025 zero <zero.kwok@foxmail.com>
#
# For the full copyright and license information, please view the LICENSE
# file that was distributed with this source code.

# 删除空目录
# 注意: -rl递归列出要删除的空目录时, 结果可能比实际的少
#       因为可能出现子文件夹是空目录, 删除后父目录也可以删除的情况.

import os
import sys
import argparse

def DoRemoveEmpty(directory:str, args):
    for f in os.listdir(directory):
        t = os.path.join(directory, f)
        if not os.path.isdir(t):
            continue
        
        # 若是目录则先递归一次
        if args.recursion:
            DoRemoveEmpty(t, args)

        # 再看是否为空目录
        if len(os.listdir(t)) == 0:
            if args.list:
                print(f'To be removed: {t}')
            else:
                print(f'Removed: {t}')
                os.rmdir(t)
            args.count = args.count + 1
            continue

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--list', action='store_true', help='it is listed but not deleted')
    parser.add_argument('-d', '--directory', type=str, default=os.getcwd(), help='specifies the directory on which to perform this operation')
    parser.add_argument('-r', '--recursion', action='store_true', help='recursive file directory')
    args = parser.parse_args()

    if not args.list:
        opt = input('Do you want to remove an empty directory (Yes/No)?')
        if opt.lower() != 'yes':
            exit(0)

    args.count = 0
    DoRemoveEmpty(args.directory, args)
    print(f'Total: {args.count}')

if __name__ == "__main__":
    main()