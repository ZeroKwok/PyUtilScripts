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
import logging
import threading
import contextlib

prefix = b'\xef\x5a'
logger = logging.getLogger(__name__)

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
        self.closed = True

    def listen(self):
        self.close()
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(self.addr)
            self.addr = self.sock.getsockname()
            self.closed = False
        except OSError as e:
            logger.error(f"UDPEndpoint listen failed on {self.addr}: {e}")
            self.close()
            return False

    def establish(self) -> bool:
        if self.closed or not self.sock:
            logger.error("UDPEndpoint establish: socket not ready")
            return False
        self.send_packet(prefix + b'HELLO') # 握手, 目的是传送地址
        return True

    def close(self):
        if self.sock:
            self.closed = True
            with contextlib.suppress(Exception):
                self.sock.close()
            self.sock = None

    def release(self):
        self.close()

    def send_packet(self, data):
        if not self.sock:
            logger.error("UDPEndpoint send: socket not created")
            return False
        if self.peers is None:
            logger.debug("UDPEndpoint send: no peers address")
            return False

        try:
            self.sock.sendto(data, self.peers)
            self.add_tx(len(data))
            return True
        except Exception as e:
            logger.error(f"UDPEndpoint send failed to {self.peers}: {e}")
            return False

    def recv_packet(self):
        if not self.sock or self.closed:
            return None
        
        try:
            data, addr = self.sock.recvfrom(65535)
            self.add_rx(len(data))

            if data.startswith(prefix):
                if data[2:] == b'HELLO':
                    self.peers = addr
                    logger.debug(f"UDPEndpoint recv HELLO from {addr}")
            return data
        except socket.timeout:
            return None
        except ConnectionResetError as e: # 对端未监听端口
            return None
        except OSError as e:
            if not self.closed:
                logger.error(f"UDPEndpoint recv error: {e}")
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
        if self.listen_sock:
            return True
        if self.connected or not self.addr:
            return False
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(self.timeout)
            sock.bind(self.addr)
            sock.listen(1)
            self.listen_sock = sock
            return True
        except OSError as e:
            logger.error(f"TCP listen failed on {self.addr}: {str(e)}", exc_info=True)
            if 'sock' in locals() and sock:
                sock.close()
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
        except OSError  as e:
            logger.error(f"TCPEndpoint connect failed to {self.peers}: {e}")
            if self.sock:
                self.close()
            return False

    def accept(self):
        if not self.listen_sock:
            logger.error("TCPEndpoint accept: no listen socket")
            return False
        if self.connected:
            return True
        try:
            if self.sock:
                self.close()

            self.sock, self.peers = self.listen_sock.accept()
            self.sock.settimeout(self.timeout)
            self.connected = True
            return True
        except OSError as e:
            logger.error(f"TCPEndpoint accept error: {e}")
            if self.sock:
                self.close()
            return False

    def establish(self) -> bool:
        if not self.connected:
            if self.listen_sock:
                return self.accept()
            else:
                return self.connect()
        return True

    def close(self):
        self.connected = False
        if self.sock:
            with contextlib.suppress(Exception):
                self.sock.close()
            self.sock = None

    def release(self):
        self.close()
        if self.listen_sock:
            with contextlib.suppress(Exception):
                self.listen_sock.close()

    def send_packet(self, data):
        if not self.establish():
            logger.error("TCPEndpoint send packet: failed to establish connection")
            return False
        try:
            self.sock.sendall(struct.pack('!I', len(data)) + data)
            self.add_tx(len(data))
            return True
        except OSError as e:
            logger.error(f"TCPEndpoint send failed to {self.peers}: {e}")
            self.close()
            return False

    def recv_packet(self):
        if not self.establish():
            logger.error("TCPEndpoint recv packet: failed to establish connection")
            return None
        try:
            length = self._recv_exact(4)
            if not length:
                return None
            length = struct.unpack('!I', length)[0]
            data = self._recv_exact(length)
            self.add_rx(len(data))
            return data
        except OSError as e:
            logger.error(f"TCPEndpoint recv failed from {self.peers}: {e}")
            self.close()
            return None

    def _recv_exact(self, size):
        data = b''
        while len(data) < size:
            try:
                chunk = self.sock.recv(size - len(data))
                if not chunk: # EOF
                    self.close()
                    return None
                data += chunk
            except socket.timeout:
                logger.warning(f"TCPEndpoint recv timeout, peer={self.peers}")
                self.close()
                return None
        return data
