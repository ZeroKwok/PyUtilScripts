#! python
# -*- coding: utf-8 -*-
#
# This file is part of the PyUtilScripts project.
# Copyright (c) 2020-2026 zero <zero.kwok@foxmail.com>
#
# For the full copyright and license information, please view the LICENSE
# file that was distributed with this source code.

import sys
import time
import logging
import argparse
import traceback
import threading

from .utils import *
from .ntraffic import UDPEndpoint, TCPEndpoint, AnyEndpoint

running = True

def create_tun(name:str, addr: tuple, mtu=1400):
    try:
        import pytun_pmd3 as pytun
        if sys.platform == 'win32':
            tun = pytun.TunTapDevice(name=name)
        else:
            tun = pytun.TunTapDevice(name=name, flags=pytun.linux.IFF_NO_PI | pytun.linux.IFF_TUN)
        tun.addr = addr
        tun.mtu = mtu
        tun.up()
        return tun
    except ImportError:
        print('[!] pytun module not found. Please install "pytun-pmd3" using pip.')
    except Exception as e:
        print(f"[!] Error creating TUN device: {e}")
    exit(1)

def forward_tun_to_peers(tun, endpoint:AnyEndpoint, args:dict):
    """将 TUN 读取的数据通过 UDP 转发到远端，并统计流量"""
    global running
    while running:
        try:
            packet = tun.read(tun.mtu)
            if packet:
                args.debug and print_packet(packet, refix='[TUN -> PEER]')
                endpoint.send_packet(packet)
        except TimeoutError:
            continue
        except Exception as e:
            if running:
                print(f"[!] Error in [TUN -> PEER]: {traceback.format_exc()}")

def forward_peers_to_tun(tun, endpoint:AnyEndpoint, args:dict):
    """接收远端 UDP 数据，写回 TUN 接口，并统计流量"""
    global running
    while running:
        try:
            data = endpoint.recv_packet()
            if data:
                args.debug and print_packet(data, refix='[TUN <- PEER]')
                tun.write(data)
            else:
                time.sleep(1)
        except Exception as e:
            print(f"[!] Error in [TUN <- PEER]: {traceback.format_exc()}")

def print_packet(packet, refix=''):
    src = dst = "N/A"
    version = packet[0] >> 4
    if version == 4:
        src, dst = packet[12:16], packet[16:20]
        src, dst = ".".join(map(str, src)), ".".join(map(str, dst))
    elif version == 6:
        src, dst = packet[8:24], packet[24:40]
        src, dst = src.hex(':'), dst.hex(':')
    print(f"{refix}: {src} -> {dst} (len={len(packet)})")

def report_stats(args, endpoint: AnyEndpoint):
    while True:
        time.sleep(args.stats_interval)
        (elapsed, (tx_packets, tx_bytes, tx_rate), (rx_packets, rx_bytes, rx_rate)) = endpoint.stats()
        tx = f"{tx_packets} pkts {format_bytes(tx_bytes, precision='.2f')} {format_bytes(tx_rate, precision=' 7.1f', postfix='/s')}"
        rx = f"{rx_packets} pkts {format_bytes(rx_bytes, precision='.2f')} {format_bytes(rx_rate, precision=' 7.1f', postfix='/s')}"
        print(f"[*] {elapsed:06.1f}s TX [{tx}] - RX [{rx}]")

def main():
    parser = argparse.ArgumentParser(description="Create a simple TUN to forward IP packets to remote peers")
    parser.add_argument("--name", default="tun0", help="Interface name (default: tun0)")
    parser.add_argument("--addr", default="fd00::1", help="IPv6 Address (default: fd00::1)") 
    parser.add_argument("--protocol", default="udp", help="Transport protocol (udp/tcp)") 
    parser.add_argument("--remote", type=str, default=None, help="Forward packets to remote endpoint")
    parser.add_argument("--listen", type=str, default='0.0.0.0:8001', help="Listen for incoming packets (default: 0.0.0.0:8001)")
    parser.add_argument("--stats-interval", type=int, default=5, help="Traffic report interval in seconds (default: 5)")
    parser.add_argument("--no-stats", action="store_true", help="Disable traffic statistics reporting")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()
    
    if args.debug:
        print(f"[*] Debug: Starting with arguments: {args}")
        input("Press Enter to continue...")
        logging.root.addHandler(logging.StreamHandler())
        logging.root.setLevel(logging.DEBUG)
        logging.debug("[*] Debug: Logging enabled")

    def parse_addr(addr, default=None):
        if addr is None:
            return None
        host, port = addr.split(':')
        host = host if host else default[0]
        port = port if port else default[1]
        return (host, int(port))

    args.remote = parse_addr(args.remote, default=('127.0.0.1', 0))
    args.listen = parse_addr(args.listen, default=('0.0.0.0', 0))

    if args.protocol.lower() != 'udp':
        Endpoint = TCPEndpoint
    else:
        Endpoint = UDPEndpoint

    endpoint = Endpoint(addr=args.listen, peers=args.remote)
    
    if not args.remote:
        endpoint.listen()
    endpoint.establish()
    print(f"[+] {endpoint.type} socket listen to {endpoint.addr}")

    tun = create_tun(args.name, args.addr)
    print(f"[+] Interface {tun.name} is UP")
    print(f"[+] IP Address: {args.addr}")

    # 启动转发线程
    t1 = threading.Thread(target=forward_tun_to_peers, args=(tun, endpoint, args))
    t1.daemon = True
    t1.start()

    t2 = threading.Thread(target=forward_peers_to_tun, args=(tun, endpoint, args))
    t2.daemon = True
    t2.start()
    
    # 启动统计报告线程（如果不禁用）
    if not args.no_stats:
        t_stats = threading.Thread(target=report_stats, args=(args, endpoint))
        t_stats.daemon = True
        t_stats.start()
        print(f"[+] Traffic statistics reporting every {args.stats_interval}s")
    else:
        print("[*] Traffic statistics reporting disabled")

    print(f"[*] Tunnel is running. Press Ctrl+C to exit.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[!] Shutting down...")
    finally:
        # 最终报告
        if not args.no_stats:
            print("\n[!] Final Traffic Summary:")
            (_, (tx_packets, tx_bytes, _), (rx_packets, rx_bytes, _)) = endpoint.stats()
            print(f"     Total TX: {format_bytes(tx_bytes)} ({tx_packets} packets)")
            print(f"     Total RX: {format_bytes(rx_bytes)} ({rx_packets} packets)")
            print(f"     Total: {format_bytes(tx_bytes + rx_bytes)}")

        global running
        running = False
        tun.down()
        tun.close()
        endpoint.release()
        print("[+] Cleanup complete.")


if __name__ == "__main__":
    main()
