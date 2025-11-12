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


class TCPForwarder:
    def __init__(self, listen_host, listen_port, target_host, target_port, verbose=False):
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.target_host = target_host
        self.target_port = target_port
        self.verbose = verbose

    def log(self, message):
        """Log messages if verbose mode is enabled."""
        if self.verbose:
            print(message)

    def run(self):
        threading.Thread(target=self.server, daemon=True).start()
        try:
            print("Press [Ctrl + C] to exit ...")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("KeyboardInterrupt: Aborting ...")

    def server(self):
        dock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        dock_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            dock_socket.bind((self.listen_host, self.listen_port))
            dock_socket.listen(5)
            self.log(f"*** listening on {self.listen_host}:{self.listen_port}")
            while True:
                client_socket, client_address = dock_socket.accept()
                addr_str = f"{client_address[0]}:{client_address[1]}"
                self.log(
                    f"*** from {addr_str} to {self.target_host}:{self.target_port}")
                try:
                    server_socket = socket.socket(
                        socket.AF_INET, socket.SOCK_STREAM)
                    server_socket.connect((self.target_host, self.target_port))
                except Exception as e:
                    self.log(
                        f"*** could not connect to target {self.target_host}:{self.target_port} -> {e}")
                    client_socket.close()
                    continue

                threading.Thread(target=self.forward, args=(
                    client_socket, server_socket, f"client -> server, {addr_str}"), daemon=True).start()
                threading.Thread(target=self.forward, args=(
                    server_socket, client_socket, f"server -> client, {addr_str}"), daemon=True).start()
        except Exception as e:
            self.log(f"*** server exception: {e}")
        finally:
            try:
                dock_socket.close()
            except Exception:
                pass

    def forward(self, source, destination, description):
        try:
            while True:
                data = source.recv(4096)
                if not data:
                    # orderly shutdown when remote closed
                    try:
                        source.shutdown(socket.SHUT_RD)
                    except Exception:
                        pass
                    try:
                        destination.shutdown(socket.SHUT_WR)
                    except Exception:
                        pass
                    break
                self.log(f"*** {description}, data length: {len(data)}")
                destination.sendall(data)
        except socket.error as e:
            # socket.error may not have strerror on all platforms; use str(e)
            self.log(f"*** {description} {e}")
        finally:
            for s in (source, destination):
                try:
                    s.close()
                except Exception:
                    pass


def main():
    parser = argparse.ArgumentParser(
        description='Forward TCP traffic from source to destination')
    parser.add_argument('--src', '-s', required=True, type=str,
                        help='The source IP address and port to listen on (e.g. 0.0.0.0:8081)')
    parser.add_argument('--dst', '-d', required=True, type=str,
                        help='The destination IP address and port to forward traffic to (e.g. 127.0.0.1:1081)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose output')

    args = parser.parse_args()

    listen_host, listen_port = args.src.split(
        ':')[0], int(args.src.split(':')[1])
    target_host, target_port = args.dst.split(
        ':')[0], int(args.dst.split(':')[1])
    verbose = args.verbose

    forwarder = TCPForwarder(listen_host, listen_port,
                             target_host, target_port, verbose=verbose)
    forwarder.run()


if __name__ == '__main__':
    main()
