import os
import sys
import time
import struct
import socket
import argparse
import traceback
import threading
import contextlib

from . import utils

# 全局变量
prefix = b'\xef\x5a'
running = True
stats_lock = threading.Lock()
stats = {
    'tx_bytes': 0,      # TUN -> UDP 发送字节数
    'rx_bytes': 0,      # UDP -> TUN 接收字节数
    'tx_packets': 0,    # 发送包数
    'rx_packets': 0,    # 接收包数
    'last_reset': time.time()
}

def report_stats(interval=5):
    """定期汇报流量统计"""
    global stats
    while True:
        time.sleep(interval)
        with stats_lock:
            now = time.time()
            elapsed = now - stats['last_reset']
            tx_rate = stats['tx_bytes'] / elapsed if elapsed > 0 else 0
            rx_rate = stats['rx_bytes'] / elapsed if elapsed > 0 else 0
            
            tx = f"{stats['tx_packets']} pkts {utils.format_bytes(stats['tx_bytes'], precision='.2f')} {utils.format_bytes(tx_rate, precision=' 7.1f', postfix='/s')}"
            rx = f"{stats['rx_packets']} pkts {utils.format_bytes(stats['rx_bytes'], precision='.2f')} {utils.format_bytes(rx_rate, precision=' 7.1f', postfix='/s')}"
            print(f"[*] {elapsed:06.1f}s TX [{tx}] - RX [{rx}]")
            
            # 重置统计（可选，注释掉则累计）
            # stats['tx_bytes'] = 0
            # stats['rx_bytes'] = 0
            # stats['tx_packets'] = 0
            # stats['rx_packets'] = 0
            # stats['last_reset'] = now

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

def forward_tun_to_udp(tun, sock:socket.socket, args:dict):
    """将 TUN 读取的数据通过 UDP 转发到远端，并统计流量"""
    # 发送初始握手包
    sock.sendto(prefix + b"Hello", args.remote)

    global stats
    global running
    while running:
        try:
            packet = tun.read(tun.mtu)
            if packet:
                args.debug and print_packet(packet, refix='[TUN -> UDP]')
                sent = sock.sendto(packet, args.remote)
                with stats_lock:
                    stats['tx_bytes'] += len(packet)
                    stats['tx_packets'] += 1
        except TimeoutError:
            continue
        except Exception as e:
            if not running:
                return
            print(f"[!] Error in TUN -> UDP: {traceback.format_exc()}")

def forward_udp_to_tun(tun, sock:socket.socket, args:dict):
    """接收远端 UDP 数据，写回 TUN 接口，并统计流量"""
    with contextlib.suppress(Exception):
        data, args.remote = sock.recvfrom(65535)
        if data and data.startswith(prefix + b"Hello"):
            print(f"[*] Peer connected from {args.remote}")
        else:
            print("[!] Warning: Received unexpected data on control channel")

    global stats
    global running
    while running:
        try:
            data, _ = sock.recvfrom(65535)
            if data:
                args.debug and print_packet(data, refix='[UDP -> TUN]')
                tun.write(data)
                with stats_lock:
                    stats['rx_bytes'] += len(data)
                    stats['rx_packets'] += 1
        except ConnectionResetError as e:
            time.sleep(1)
            continue
        except Exception as e:
            if not running:
                return
            print(f"[!] Error in UDP -> TUN: {traceback.format_exc()}")

def create_tun(name, addr, mtu=1500):
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

def main():
    parser = argparse.ArgumentParser(description="Create a simple TUN to forward IP packets to remote peers")
    parser.add_argument("--name", default="tun0", help="Interface name")
    parser.add_argument("--addr", default="fd00::1", help="IPv6 Address") 
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--stats-interval", type=int, default=5, help="Traffic report interval in seconds (default: 5)")
    parser.add_argument("--no-stats", action="store_true", help="Disable traffic statistics reporting")
    parser.add_argument("--remote", default="127.0.0.1:5001", help="Forward packets to remote endpoint")
    parser.add_argument("--listen", default="0.0.0.0:0", help="Listen for incoming packets")
    args = parser.parse_args()
    
    if args.debug:
        print(f"[*] Debug: Starting with arguments: {args}")
        input("Press Enter to continue...")

    host, port = args.remote.split(':')
    args.remote = (host if host else '127.0.0.1', int(port))

    host, port = args.listen.split(':')
    args.listen = (host if host else '0.0.0.0', int(port))
    
    # 创建 UDP Socket 并绑定到随机端口以便接收回包
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(args.listen)
    
    args.listen = sock.getsockname()
    print(f"[+] UDP socket bound to {args.listen}")

    tun = create_tun(args.name, args.addr)
    print(f"[+] Interface {tun.name} is UP")
    print(f"[+] IP Address: {args.addr}")
    
    # 启动转发线程
    t1 = threading.Thread(target=forward_tun_to_udp, args=(tun, sock, args))
    t1.daemon = True
    t1.start()

    t2 = threading.Thread(target=forward_udp_to_tun, args=(tun, sock, args))
    t2.daemon = True
    t2.start()
    
    # 启动统计报告线程（如果不禁用）
    if not args.no_stats:
        t_stats = threading.Thread(target=report_stats, args=(args.stats_interval,))
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
            with stats_lock:
                print(f"     Total TX: {utils.format_bytes(stats['tx_bytes'])} ({stats['tx_packets']} packets)")
                print(f"     Total RX: {utils.format_bytes(stats['rx_bytes'])} ({stats['rx_packets']} packets)")
                print(f"     Total: {utils.format_bytes(stats['tx_bytes'] + stats['rx_bytes'])}")

        global running
        running = False
        tun.down()
        tun.close()
        sock.close()
        print("[+] Cleanup complete.")


if __name__ == "__main__":
    main()
