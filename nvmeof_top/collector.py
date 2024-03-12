import asyncio
import threading
import nvmeof_top.proto.gateway_pb2 as pb2
import time
import random
import grpc
import logging
from .utils import lb_group, bytes_to_MB
from typing import Dict

event = threading.Event()
logger = logging.getLogger(__name__)


class Health:
    def __init__(self):
        self.rc = 0
        self.msg = ''


class Counter:
    def __init__(self):
        self.current = 0.0
        self.last = 0.0

    def update(self, new_value: float):
        """Update the stats maintaining current and last"""
        self.last = self.current
        self.current = new_value

    def rate(self, interval: float):
        """Calculate the per second change rate"""
        return (self.current - self.last) / interval


class PerformanceStats:
    def __init__(self, bdev: str, delay: int):
        self.bdev = bdev
        self.read_ops = Counter()
        self.read_bytes = Counter()
        self.read_secs = Counter()
        self.write_ops = Counter()
        self.write_bytes = Counter()
        self.write_secs = Counter()

        self.read_ops_rate = 0
        self.write_ops_rate = 0
        self.read_bytes_rate = 0
        self.write_bytes_rate = 0
        self.total_ops_rate = 0
        self.total_bytes_rate = 0
        self.rareq_sz = 0.0
        self.wareq_sz = 0.0
        self.r_await = 0.0
        self.w_await = 0.0

    def calculate(self, delay: int):
        self.read_ops_rate = self.read_ops.rate(delay)
        self.read_bytes_rate = self.read_bytes.rate(delay)
        self.read_secs_rate = self.read_secs.rate(delay)
        self.write_ops_rate = self.write_ops.rate(delay)
        self.write_bytes_rate = self.write_bytes.rate(delay)
        self.write_secs_rate = self.write_secs.rate(delay)

        self.total_ops_rate = self.read_ops_rate + self.write_bytes_rate
        self.total_bytes_rate = self.read_bytes_rate + self.write_bytes_rate

        if self.read_ops_rate:
            self.rareq_sz = (int(self.read_bytes_rate / self.read_ops_rate) / 1024)
            self.r_await = ((self.read_secs_rate / self.read_ops_rate) * 1000)  # for ms
        else:
            self.rareq_sz = 0.0
            self.r_await = 0.0
        if self.write_ops_rate:
            self.wareq_sz = (int(self.write_bytes_rate / self.write_ops_rate) / 1024)
            self.w_await = ((self.write_secs_rate / self.write_ops_rate) * 1000)  # for ms
        else:
            self.wareq_sz = 0.0
            self.w_await = 0.0


class ThreadCPUStats:
    def __init__(self, thread_name: str):
        self.name = thread_name

        # values stored by the counter object should be the value / tick_rate
        self.busy = Counter()

        self.busy_rate = 0.0

    def calculate(self, delay: int) -> None:
        self.busy_rate = self.busy.rate(delay)


# class CPUResourceUsage:
#     def __init__(self):
#         self.busy = {}

#     @property
#     def min_cpu(self) -> float:
#         return min(self.busy)

#     @property
#     def max_cpu(self) -> float:
#         return max(self.busy)

#     def avg_cpu(self) -> float:
#         return sum(self.busy) / len(self.busy.keys())


class Collector:

    def __init__(self, parent):
        self.parent = parent
        self.client = self.parent.client
        self.subsystem_nqn = self.parent.subsystem_nqn
        self.nqn_list = []
        self.namespaces = []
        self.subsystems = None
        self.connection_info = None
        self.cpustats_enabled = False
        self.thread_stats = {}
        self.iostats = {}
        self.iostats_lock = threading.Lock()
        self.lock = threading.Lock()
        self.gw_info = None
        self.timestamp = time.time()
        self._min_sample_count = 2
        self._sample_count = 0
        self.health = Health()

    def update_subsystem(self, new_subsystem_nqn: str) -> None:
        logger.info(f"updating subsystem to scan from {self.subsystem_nqn} to {new_subsystem_nqn}")
        self.subsystem_nqn = new_subsystem_nqn

    @property
    def total_iops(self):
        return int(sum([stats.total_ops_rate for _, stats in self.iostats.items()]))

    @property
    def total_bandwidth(self):
        return sum([stats.total_bytes_rate for _, stats in self.iostats.items()])

    @property
    def connections_defined(self):
        if self.connection_info:
            return len(self.connection_info.connections)
        logger.debug("request for connections_defined but the connection_info is not set")
        return 0

    @property
    def connections_active(self):
        if self.connection_info:
            return len([con.traddr for con in self.connection_info.connections if con.connected])
        logger.debug("request for connections_active but the connection_info is not set")
        return 0

    @property
    def ready(self) -> bool:
        return self.health.rc == 0

    @property
    def samples_ready(self) -> bool:
        return self._sample_count == self._min_sample_count

    @property
    def total_namespaces_defined(self) -> int:
        return len(self.namespaces)

    @property
    def total_subsystems(self) -> int:
        return len(self.nqn_list)

    @property
    def reactor_cores(self) -> int:
        return len(self.thread_stats.keys())

    def log_connection(self):
        logger.info(f"Connected to {self.parent.args.server_addr}")
        logger.info(f"Gateway has {self.total_subsystems} subsystems")

    def get_sorted_namespaces(self, sort_pos: int, active_only: bool = False):
        ns_data = []
        for ns in self.namespaces:

            rbd_info = f"{ns.rbd_pool_name}/{ns.rbd_image_name}"
            bdev_name = ns.bdev_name

            perf_stats = self.iostats[bdev_name]
            perf_stats.calculate(self.parent.delay)

            ns_data.append((
                ns.nsid,
                rbd_info,
                int(perf_stats.total_ops_rate),
                int(perf_stats.read_ops_rate),
                f"{bytes_to_MB(perf_stats.read_bytes_rate):3.2f}",
                f"{perf_stats.r_await:3.2f}",
                f"{perf_stats.rareq_sz:4.2f}",
                int(perf_stats.write_ops_rate),
                f"{bytes_to_MB(perf_stats.write_bytes_rate):3.2f}",
                f"{perf_stats.w_await:3.2f}",
                f"{perf_stats.wareq_sz:4.2f}",
                lb_group(ns.load_balancing_group),
                self.qos_enabled(ns)
            ))

        ns_data.sort(key=lambda t: t[sort_pos], reverse=self.parent.reverse_sort)
        return ns_data

    def get_cpu_stats(self) -> Dict[str, ThreadCPUStats]:
        for name, stats in self.thread_stats.items():
            stats.calculate(self.parent.delay)
        return self.thread_stats

    def qos_enabled(self, ns) -> str:
        if (ns.rw_ios_per_second or ns.rw_mbytes_per_second or ns.r_mbytes_per_second or ns.w_mbytes_per_second):
            return 'Yes'
        return 'No'

    def initialise(self):
        raise NotImplementedError(f"class {self.__class__.__name__} is missing initialise() method")

    def run(self):
        raise NotImplementedError(f"class {self.__class__.__name__} is missing run() method")


class DataCollector(Collector):

    def initialise(self):
        self.set_gw_info()
        if self.health.rc > 0:
            logger.error('Unable to retrieve gataway information')
            return

        subsys_info = self._get_all_subsystems()
        if subsys_info.status > 0:
            logger.error(f"Call to list_subsystems failed, RC={subsys_info.status}, MSG={subsys_info.error_message}")
            self.health.rc = 8
            self.health.msg = "Unable to retrieve a list of subsystems"
            return

        self.nqn_list = [subsys.nqn for subsys in subsys_info.subsystems]
        if self.total_subsystems == 0:
            self.health.rc = 8
            self.health.msg = 'No subsystems found'
            return

        self.log_connection()

    def call_grpc_api(self, method_name, request):
        logger.debug(f"calling gprc method {method_name}")
        try:
            func = getattr(self.client.stub, method_name)
            data = func(request)
        except grpc._channel._InactiveRpcError:
            self.health.rc = 8
            self.health.msg = f"RPC endpoint unavailable at {self.client.server}"
            logger.error(f"gprc call to {method_name} failed: {self.health.msg}")
            return None

        self.health.msg = f"{method_name} success"
        logger.debug(f"call to {method_name} successful")
        return data

    def set_gw_info(self):
        """Grab the gateway metadata"""
        self.gw_info = self.call_grpc_api('get_gateway_info', pb2.get_gateway_info_req())

    async def collect_data(self):
        if not self._sample_count == self._min_sample_count:
            self._sample_count += 1
        namespace_info = self._get_namespaces()
        if not self.ready:
            return

        # TODO namespace_info.status should be 0
        self.namespaces = namespace_info.namespaces
        logger.debug(f"Subsystem '{self.subsystem_nqn}' has {self.total_namespaces_defined} namespaces")

        async with asyncio.TaskGroup() as tg:
            for ns in self.namespaces:
                tg.create_task(asyncio.to_thread(self._get_ns_iostats, ns))

            subsystem_task = tg.create_task(asyncio.to_thread(self._get_subsystems))
            connections_task = tg.create_task(asyncio.to_thread(self._get_connections))

        self.subsystems = subsystem_task.result()
        self.connection_info = connections_task.result()

        logger.debug("tasks completed")

    def _get_ns_iostats(self, ns):
        logger.debug(f"fetching iostats for namespace {ns.nsid}")
        with self.iostats_lock:
            logger.debug('iostats lock acquired')
            if ns.bdev_name not in self.iostats:
                self.iostats[ns.bdev_name] = PerformanceStats(ns.bdev_name, self.parent.delay)
            logger.debug('calling namespace_get_io_stats')
            stats = self.call_grpc_api('namespace_get_io_stats',
                                       pb2.namespace_get_io_stats_req(
                                           subsystem_nqn=self.parent.subsystem_nqn,
                                           nsid=ns.nsid))
            logger.debug(stats)

            iostats = self.iostats[ns.bdev_name]
            iostats.read_ops.update(stats.num_read_ops)
            iostats.read_bytes.update(stats.bytes_read)
            iostats.read_secs.update((stats.read_latency_ticks / stats.tick_rate))
            iostats.write_ops.update(stats.num_write_ops)
            iostats.write_bytes.update(stats.bytes_written)
            iostats.write_secs.update((stats.write_latency_ticks / stats.tick_rate))

    def _get_namespaces(self):
        return self.call_grpc_api('list_namespaces', pb2.list_namespaces_req(subsystem=self.subsystem_nqn))

    def _get_subsystems(self):
        return self.call_grpc_api('list_subsystems', pb2.list_subsystems_req(subsystem_nqn=self.subsystem_nqn))

    def _get_all_subsystems(self):
        return self.call_grpc_api('list_subsystems', pb2.list_subsystems_req())

    def _get_connections(self):
        return self.call_grpc_api('list_connections', pb2.list_connections_req(subsystem=self.subsystem_nqn))

    def get_cpu_stats(self):
        raise NotImplementedError

    async def start(self):
        while not event.is_set():
            with self.lock:
                start = time.time()
                await self.collect_data()
                logger.info(f"data collection took: {(time.time() - start):3.3f} secs")

                if not self.ready:
                    logger.error("Error encounted during data collection, terminating async loop")
                    return
                self.timestamp = time.time()
                logger.debug(f"event loop waiting for {self.parent.delay}s")
            event.wait(self.parent.delay)

    def run(self):
        if self.ready:
            asyncio.run(self.start())


class DummyObject:
    pass


class DummyPerformance:
    def calculate(self, delay: int):
        pass


class DummyCollector(Collector):
    """Dummy class to provide just enough data to validate batch and console modes"""

    def __init__(self, parent, namespace_count):
        super().__init__(parent)
        self.cpustats_enabled = True
        self.namespace_count = namespace_count

    def initialise(self):
        gw = DummyObject()
        gw.version = '1.0.0'
        gw.name = 'made-up'
        gw.spdk_version = '23.01.1'
        self.gw_info = gw
        self.nqn_list = [
            'nqn.2016-06.io.spdk:cnode1',
            'nqn.2016-06.io.spdk:cnode2'
        ]

        self.log_connection()

    def _get_namespaces(self):
        namespaces = []
        for n in range(1, self.namespace_count + 1, 1):
            ns = DummyObject()
            ns.nsid = n
            ns.bdev_name = f"bdev_{n}"
            ns.rbd_pool_name = 'rbd'
            ns.rbd_image_name = f"image_{n}"
            ns.load_balancing_group = 0
            ns.rw_ios_per_second = 0
            ns.rw_mbytes_per_second = 0
            ns.r_mbytes_per_second = 0
            ns.w_mbytes_per_second = 0
            namespaces.append(ns)
        return namespaces

    def _get_subsystems(self):
        subsystem_list = []
        subsystem = DummyObject()
        subsystem.nqn = 'nqn.2016-06.io.spdk:cnode1'
        subsystem.max_namespaces = 256
        subsystem_list.append(subsystem)
        return subsystem_list

    def _get_connections(self):
        connection_info = DummyObject()
        connection_info.status = 0
        connection_info.error_message = ''
        connection_info.subsystem_nqn = 'nqn.2016-06.io.spdk:cnode1'
        connection_info.connections = []
        client = DummyObject()
        client.nqn = 'nqn.2014-08.org.nvmexpress:uuid:ee889718-8c69-40d3-8e78-5be049f966a6'
        client.traddr = '192.168.1.1'
        client.connected = True
        connection_info.connections.append(client)
        client = DummyObject()
        client.nqn = 'nqn.2014-08.org.nvmexpress:uuid:ee889718-8c69-40d3-8e78-deadbeef00001'
        client.traddr = '192.168.1.2'
        client.connected = False
        connection_info.connections.append(client)
        return connection_info

    def get_cpu_stats(self):
        logger.debug("in dummy collecter get_cpu_stats method")
        for thread_name in ['app_thread', 'nvmf_tgt_poll_group_0', 'nvmf_tgt_poll_group_1', 'nvmf_tgt_poll_group_2', 'nvmf_tgt_poll_group_0']:
            busy = random.randint(1, 100)

            self.thread_stats[thread_name] = ThreadCPUStats(thread_name)
            stats = self.thread_stats[thread_name]
            stats.busy_rate = busy
        return self.thread_stats

    def collect_data(self):
        if not self._sample_count == self._min_sample_count:
            self._sample_count += 1
        self.namespaces = self._get_namespaces()
        logger.debug(f"Subsystem '{self.subsystem_nqn}' has {self.total_namespaces_defined} namespaces")
        io_sizes = [4, 8, 16]
        for ns in self.namespaces:
            self.iostats[ns.bdev_name] = DummyPerformance()
            iostats = self.iostats[ns.bdev_name]
            iostats.bdev_name = ns.bdev_name
            iostats.read_ops_rate = random.randint(500, 9000)
            iostats.write_ops_rate = random.randint(100, 4000)
            iostats.rareq_sz = random.choice(io_sizes)
            iostats.wareq_sz = random.choice(io_sizes)
            iostats.read_bytes_rate = (iostats.read_ops_rate * (iostats.rareq_sz * 1024))
            iostats.write_bytes_rate = (iostats.write_ops_rate * (iostats.wareq_sz * 1024))
            iostats.total_ops_rate = iostats.read_ops_rate + iostats.write_ops_rate
            iostats.total_bytes_rate = iostats.read_bytes_rate + iostats.write_ops_rate
            iostats.rareq_sz = random.choice(io_sizes)
            iostats.wareq_sz = random.choice(io_sizes)
            iostats.r_await = (1 / iostats.read_ops_rate) * 1000
            iostats.w_await = (1 / iostats.write_ops_rate) * 1000

        self.subsystems = self._get_subsystems()
        self.connection_info = self._get_connections()

    def run(self):
        event = threading.Event()
        while not event.is_set():
            self.collect_data()
            self.timestamp = time.time()
            logger.debug(f"event loop waiting for {self.parent.delay}s")
            event.wait(self.parent.delay)
