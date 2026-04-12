#! python
# -*- coding: utf-8 -*-
#
# This file is part of the PyUtilScripts project.
# Copyright (c) 2020-2026 zero <zero.kwok@foxmail.com>
#
# For the full copyright and license information, please view the LICENSE
# file that was distributed with this source code.

import time
import struct
import socket
import threading

class AnyEndpoint:
    def __init__(self):
        self.sock = None
        self.peers = None

        self.tx_bytes = 0       # 发送字节数   
        self.rx_bytes = 0       # 接收字节数
        self.tx_packets = 0     # 发送包数
        self.rx_packets = 0     # 接收包数
        self.stats_time = time.time()
        self.stats_lock = threading.Lock()

    def add_tx(self, tx_bytes=0, tx_packets=1):
        with self.stats_lock:
            self.tx_bytes += tx_bytes
            self.tx_packets += tx_packets

    def add_rx(self, rx_bytes=0, rx_packets=1):
        with self.stats_lock:
            self.rx_bytes += rx_bytes
            self.rx_packets += rx_packets

    def stats(self, reset_timer:bool=True):
        with self.stats_lock:
            elapsed = time.time() - self.stats_time
            if reset_timer:
                self.stats_time = time.time()
            tx_rate = self.tx_bytes / elapsed if elapsed > 0 else 0
            rx_rate = self.rx_bytes / elapsed if elapsed > 0 else 0
            return (elapsed, (self.tx_packets, self.tx_bytes, tx_rate), (self.rx_packets, self.rx_bytes, rx_rate))


class UDPEndpoint(AnyEndpoint):
    def __init__(self, addr, peers = None):
        super().__init__()
        self.type = 'UDP'
        self.addr = addr
        self.peers = peers

    def listen(self):
        if self.sock:
            self.sock.close()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(self.addr)
        self.addr = self.sock.getsockname()

    def establish(self):
        self.send_packet(b'')   # 发送空包以传送对端地址

    def close(self):
        if self.sock:
            self.sock.close()

    def send_packet(self, data):
        try:
            self.sock.sendto(data, self.peers)
            self.add_tx(len(data))
            return True
        except Exception as e:
            return False

    def recv_packet(self):
        try:
            data, addr = self.sock.recvfrom(65535)
            self.add_rx(len(data))
            if not self.peers:  # 第一次接收数据, 存储对端地址
                self.peers = addr
            return data
        except ConnectionResetError as e: # 对端未监听端口
            return None
        except Exception as e:
            return None



class TCPEndpoint(AnyEndpoint):
    def __init__(self, addr, peers = None, timeout=5):
        super().__init__()
        self.type = 'TCP'
        self.addr = addr
        self.peers = peers
        self.timeout = timeout
        self.connected = False
        self.listen_sock = None

    def listen(self):
        if self.connected or self.listen_sock or not self.addr:
            return True
        try:
            self.listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.listen_sock.settimeout(self.timeout)
            self.listen_sock.bind(self.addr)
            self.listen_sock.listen(backlog=1)
            return True
        except Exception as e:
            return False

    def connect(self):
        if self.connected:
            return True
        try:
            if self.sock:
                self.sock.close()
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(self.timeout)
            self.sock.connect(self.peers)
            self.connected = True
            return True
        except Exception as e:
            return False

    def accept(self):
        if not self.listen_sock:
            return False
        if self.connected:
            return True
        try:
            if self.sock:
                self.sock.close()
            self.sock, self.peers = self.listen_sock.accept()
            self.sock.settimeout(self.timeout)
            self.connected = True
            return True
        except Exception as e:
            return False

    def establish(self):
        if not self.connected:
            if self.listen_sock:
                self.accept()
            else:
                self.connect()

    def close(self):
        self.connected = False
        if self.sock:
            self.sock.close()

    def release(self):
        self.close()
        if self.listen_sock:
            self.listen_sock.close()

    def send_packet(self, data):
        self.establish()
        try:
            self.sock.sendall(struct.pack('!I', len(data)) + data)
            self.add_tx(len(data))
            return True
        except Exception as e:
            self.connected = False
            return False

    def recv_packet(self):
        self.establish()
        try:
            length = self._recv_exact(4)
            if not length:
                return None
            length = struct.unpack('!I', length)[0]
            data = self._recv_exact(length)
            self.add_rx(len(data))
            return data
        except Exception as e:
            self.connected = False
            return None

    def _recv_exact(self, size):
        data = b''
        count = 0
        while len(data) < size:
            try:
                chunk = self.sock.recv(size - len(data))
                if not chunk: # EOF
                    self.connected = False
                    return None
                data += chunk
            except socket.timeout:
                count += 1
                if count < 2:  # 连续多次超时则认为连接断开
                    continue
                self.connected = False
                return None
        return data
