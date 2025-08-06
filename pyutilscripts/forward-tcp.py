#! python
# -*- coding: utf-8 -*-
#
# This file is part of the PyUtilScripts project.
# Copyright (c) 2020-2025 zero <zero.kwok@foxmail.com>
#
# For the full copyright and license information, please view the LICENSE
# file that was distributed with this source code.

import sys
import time
import socket
import argparse
import threading

listen_host = "0.0.0.0"
listen_port = 8081

target_host = "127.0.0.1"
target_port = 1081

verbose = False

def log(message):
    """Log messages if verbose mode is enabled."""
    if verbose:
        print(message)

def run():
    threading.Thread(target=server, daemon=True).start()
    try:
        print(f"Press [Ctrl + C] to exit ...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:  
        print(f"KeyboardInterrupt: Aborting ...") 

def server(*settings):
    try:
        dock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        dock_socket.bind((listen_host, listen_port)) # listen
        dock_socket.listen(5)
        log("*** listening on %s:%i" % ( listen_host, listen_port ))
        while True:
            client_socket, client_address = dock_socket.accept()
            
            log("*** from %s:%i to %s:%i" % ( client_address, listen_port, target_host, target_port ))
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.connect((target_host, target_port))
            threading.Thread(target=forward, args=(client_socket, server_socket, f"client -> server, {client_address}" ), daemon=True).start()
            threading.Thread(target=forward, args=(server_socket, client_socket, f"server -> client, {client_address}" ), daemon=True).start()
    finally:
        dock_socket.close()
        time.sleep(1)
        threading.Thread(target=server, daemon=True).start()

def forward(source, destination, description):
    data = ' '
    try:
        while data:
            data = source.recv(4096)
            log(f"*** {description}, data length: {len(data)}")
            if data:
                destination.sendall(data)
            else:
                source.shutdown(socket.SHUT_RD)
                destination.shutdown(socket.SHUT_WR)
    except socket.error as e:
        print(f"*** {description} {e.strerror}")
        source.shutdown(socket.SHUT_RD)
        destination.shutdown(socket.SHUT_WR)

def main():
    parser = argparse.ArgumentParser(description='Forward TCP traffic from source to destination')  
    parser.add_argument('--src', '-s', required=True, type=str, help='The source IP address and port to listen on (e.g. 0.0.0.0:8081)')
    parser.add_argument('--dst', '-d', required=True, type=str, help='The destination IP address and port to forward traffic to (e.g. 127.0.0.1:1081)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    
    args = parser.parse_args()

    # 解析后的参数
    listen_host = args.src.split(':')[0]
    listen_port = int(args.src.split(':')[1])
    target_host = args.dst.split(':')[0]
    target_port = int(args.dst.split(':')[1])
    verbose = args.verbose

    run()

if __name__ == '__main__':
    main()