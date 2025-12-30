#! python
# -*- coding: utf-8 -*-

import time
import argparse
import sys
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn

class RateLimitHandler(SimpleHTTPRequestHandler):
    # Default value
    SPEED_LIMIT = -1 

    def copyfile(self, source, outputfile):
        """Override copyfile to implement rate limiting. If unlimited, use the original efficient method."""
        # If unlimited, call parent class method (which uses shutil.copyfileobj internally and is more efficient)
        if self.SPEED_LIMIT <= 0:
            return super().copyfile(source, outputfile)

        chunk_size = 1024 * 64  # 64KB chunk size
        try:
            start_time = time.time()
            bytes_sent = 0
            while True:
                data = source.read(chunk_size)
                if not data:
                    break
                outputfile.write(data)
                bytes_sent += len(data)

                # Rate limiting calculation
                elapsed = time.time() - start_time
                expected_time = bytes_sent / self.SPEED_LIMIT

                if elapsed < expected_time:
                    # 最小睡眠时间设为 0.5 秒, 因此理论最低速度约为 0.5 * 64kb = 128KB/s
                    time.sleep(min(expected_time - elapsed, 0.5)) 
        except (ConnectionResetError, BrokenPipeError):
            print(f"\n[!] Client {self.client_address[0]} disconnected")

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

def parse_speed(speed_str):
    """Parse speed string; support negative for unlimited."""
    s = speed_str.upper()
    try:
        # Handle unlimited cases
        if s == '-1' or s == '0' or s == 'UNLIMITED':
            return -1
        
        if s.endswith('MB'):
            return int(float(s[:-2]) * 1024 * 1024)
        elif s.endswith('KB'):
            return int(float(s[:-2]) * 1024)
        else:
            return int(s)
    except ValueError:
        raise argparse.ArgumentTypeError("Invalid speed format. Use '1MB', '500KB', '-1' (unlimited), or a byte value.")

def main():
    parser = argparse.ArgumentParser(description="Multithreaded HTTP file server with rate limiting")
    parser.add_argument('--port', '-p', type=int, default=8000, help='Port to listen on (default: 8000)')
    parser.add_argument('--bind', '-b', default='0.0.0.0', help='Bind address (default: 0.0.0.0)')
    parser.add_argument('--limit', '-l', default='-1', help="Rate limit (e.g., 1MB, 500KB). Use -1 for unlimited")
    parser.add_argument('--dir', '-d', default='.', help='Root directory to serve (default: current directory)')

    args = parser.parse_args()

    # 1. Verify directory exists
    if not os.path.isdir(args.dir):
        print(f"[ERROR] Directory does not exist: {args.dir}")
        sys.exit(1)
    
    # 2. Change to and record absolute path
    abs_path = os.path.abspath(args.dir)
    os.chdir(abs_path)

    # 3. Parse rate limit
    limit_bps = parse_speed(args.limit)
    limit_display = f"{args.limit}/s ({limit_bps})" if limit_bps > 0 else "Unlimited"

    # 4. Dynamic handler class
    HandlerClass = type('CustomHandler', (RateLimitHandler,), {'SPEED_LIMIT': limit_bps})

    server_address = (args.bind, args.port)
    httpd = ThreadedHTTPServer(server_address, HandlerClass)

    print(f"{'='*45}")
    print(f"[*] HTTP server started")
    print(f"[*] Listening on: http://{args.bind}:{args.port}")
    print(f"[*] Serving directory: {abs_path}")
    print(f"[*] Speed limit: {limit_display}")
    print(f"{'='*45}")
    print("[!] Press Ctrl+C to stop the server\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] Shutting down server...")
        httpd.server_close()

if __name__ == "__main__":
    main()