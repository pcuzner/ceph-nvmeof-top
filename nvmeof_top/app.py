import argparse
from .grpc import GatewayClient
from nvmeof_top.collector import DataCollector
from nvmeof_top.utils import bytes_to_MB, lb_group
import threading
import time
from typing import List
import sys
import logging

logger = logging.getLogger(__name__)


class NVMeoFTop:
    text_headers = ['NSID', 'RBD pool/image', 'r/s', 'rMB/s', 'r_await', 'rareq-sz', 'w/s', 'wMB/s', 'w_await', 'wareq-sz', 'LBGrp', 'QoS']
    text_template = "{:>4}  {:<32}    {:>6}   {:>6}  {:>7}  {:>8}  {:>6}  {:>6}  {:>7}  {:>8}  {:^5}   {:>3}\n"

    def __init__(self, args: argparse.Namespace, client: GatewayClient):
        self.client = client
        self.args = args
        self.collector: DataCollector

    def to_stdout(self):
        """Dump information to stdout"""
        logger.debug("writing stats to stdout")
        with self.collector.lock:
            ns_data = self.collector.namespaces

        rows = []
        if self.args.with_timestamp:
            tstamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.collector.timestamp))
            rows.append(f"{tstamp}\n")
        if not self.args.no_headings:
            rows.append(NVMeoFTop.text_template.format(*NVMeoFTop.text_headers))
        if ns_data:
            ns_data.sort(key=lambda x: x.nsid, reverse=False)
            for ns in ns_data:
                row = self.build_ns_row(ns)
                rows.append(NVMeoFTop.text_template.format(*row))
        else:
            rows.append("<no namespaces defined>")

        print(''.join(rows), end='')

    def build_ns_row(self, ns) -> List[str]:

        rbd_info = f"{ns.rbd_pool_name}/{ns.rbd_image_name}"
        bdev_name = ns.bdev_name

        perf_stats = self.collector.iostats[bdev_name]
        logger.debug(f"building row for namespace {ns.nsid} from {self.args.subsystem}")

        read_ops = perf_stats.read_ops.rate(self.args.delay)
        read_secs = perf_stats.read_secs.rate(self.args.delay)
        read_bytes = perf_stats.read_bytes.rate(self.args.delay)
        write_ops = perf_stats.write_ops.rate(self.args.delay)
        write_secs = perf_stats.write_secs.rate(self.args.delay)
        write_bytes = perf_stats.write_bytes.rate(self.args.delay)

        if read_ops:
            rareq_sz = (int(read_bytes / read_ops) / 1024)
            r_await = ((read_secs / read_ops) * 1000)  # for ms
        else:
            rareq_sz = 0.0
            r_await = 0.0
        if write_ops:
            wareq_sz = (int(write_bytes / write_ops) / 1024)
            w_await = ((write_secs / write_ops) * 1000)  # for ms
        else:
            wareq_sz = 0.0
            w_await = 0.0

        return [
            ns.nsid,
            rbd_info,
            int(read_ops),
            f"{bytes_to_MB(read_bytes):3.2f}",
            f"{r_await:3.2f}",
            f"{rareq_sz:4.2f}",
            int(write_ops),
            f"{bytes_to_MB(write_bytes):3.2f}",
            f"{w_await:3.2f}",
            f"{wareq_sz:4.2f}",
            lb_group(ns.load_balancing_group),
            self.qos_enabled(ns)
        ]

    def qos_enabled(self, ns) -> str:
        if (ns.rw_ios_per_second or ns.rw_mbytes_per_second or ns.r_mbytes_per_second or ns.w_mbytes_per_second):
            return "Yes"
        return "No"

    def console_mode(self):
        logger.info(f"Running in console mode: {self.args.subsystem}")
        pass

    def batch_mode(self):
        logger.info(f"Running in batch mode: {self.args.subsystem}")
        event = threading.Event()
        ctr = 0
        try:
            print("waiting for samples...")
            while not event.is_set():
                if not self.collector.ready:
                    self.abort(self.collector.health.rc, self.collector.health.msg)

                if self.collector.samples_ready:
                    self.to_stdout()
                    if self.args.count:
                        ctr += 1
                        if ctr > self.args.count:
                            break
                event.wait(self.args.delay)

        except KeyboardInterrupt:
            logger.info("nvmeof-top stopped by user")

        print("\nnvmeof-top stopped.")

    def abort(self, rc: int, msg: str):
        logger.critical(f"collector has hit a problem: {self.collector.health.msg}")
        print(msg)
        sys.exit(rc)

    def run(self):
        self.collector = DataCollector(self.client, self.args.delay, self.args.subsystem)
        self.collector.initialise()
        if not self.collector.ready:
            self.abort(self.collector.health.rc, self.collector.health.msg)

        t = threading.Thread(target=self.collector.run, daemon=True)
        t.start()

        if self.args.mode == "batch":
            self.batch_mode()
        else:
            self.console_mode()
