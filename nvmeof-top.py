#!/usr/bin/env python3
import sys
import argparse
from nvmeof_top import NVMeoFTop
from nvmeof_top.grpc import GatewayClient
from nvmeof_top.utils import valid_nqn
import nvmeof_top.defaults as DEFAULT


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--delay", "-d", type=int, default=DEFAULT.delay, help=f"Refresh interval (secs) [{DEFAULT.delay}]")
    parser.add_argument("--mode", "-m", type=str, choices=['batch', 'console'], default='batch', help=f"Run time mode [{DEFAULT.mode}]")
    parser.add_argument("--subsystem", "-n", type=valid_nqn, help="NQN of the subsystem to monitor (REQUIRED)", required=True)
    parser.add_argument("--server-addr", "-a", type=str, help="Gateway server IP address", default=DEFAULT.server_addr)
    parser.add_argument("--server-port", "-p", type=int, help="Gateway server control path port", default=DEFAULT.server_port)
    parser.add_argument("--with-timestamp", action='store_true', default=False, help="Prefix namespaces statistics with a timestamp in batch mode")
    parser.add_argument("--no-headings", action='store_true', default=False, help="Omit column headings in batch mode")
    parser.add_argument("--count", "-c", type=int, help="Number of interations for stats gathering")

    args = parser.parse_args()

    return args


if __name__ == "__main__":
    args = parse_arguments()

    if not args.server_addr or not args.server_port:
        print("IP and port required: Either set SERVER_ADDR and SERVER_PORT environment variables or provide them as parameters")
        sys.exit(4)

    gateway_client = GatewayClient(
        server_addr=args.server_addr,
        server_port=args.server_port
    )
    gateway_client.connect()

    app = NVMeoFTop(args, gateway_client)

    app.run()
