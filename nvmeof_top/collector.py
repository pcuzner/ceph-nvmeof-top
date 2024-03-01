import asyncio
import threading
import nvmeof_top.proto.gateway_pb2 as pb2
import time
import grpc
import logging

event = threading.Event()
logger = logging.getLogger(__name__)


class Health:
    def __init__(self):
        self.rc = 0
        self.msg = ''


class IOStatCounter:
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
    def __init__(self, bdev: str):
        self.bdev = bdev
        self.read_ops = IOStatCounter()
        self.read_bytes = IOStatCounter()
        self.read_secs = IOStatCounter()
        self.write_ops = IOStatCounter()
        self.write_bytes = IOStatCounter()
        self.write_secs = IOStatCounter()


class DataCollector:

    def __init__(self, client, delay: int, subsystem: str):
        self.client = client
        self.delay = delay
        self.subsystem = subsystem
        self.namespaces = None
        self.subsystems = None
        self.connections = None
        self.iostats = {}
        self.iostats_lock = threading.Lock()
        self.lock = threading.Lock()
        self.gw_info = None
        self.timestamp = None
        self._min_sample_count = 2
        self._sample_count = 0
        self.health = Health()

    @property
    def ready(self) -> bool:
        return self.health.rc == 0

    def initialise(self):
        self.set_gw_info()

    @property
    def samples_ready(self) -> bool:
        return self._sample_count == self._min_sample_count

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
        # TODO add log message for len(namespace_info.namespaces)

        async with asyncio.TaskGroup() as tg:
            for ns in self.namespaces:
                tg.create_task(asyncio.to_thread(self._get_ns_iostats, ns))

            self.subsystems = tg.create_task(asyncio.to_thread(self._get_subsystems))
            self.connections = tg.create_task(asyncio.to_thread(self._get_connections))

    def _get_ns_iostats(self, ns):
        logger.debug(f"fetching iostats for namespace {ns.nsid}")
        with self.iostats_lock:
            if ns.bdev_name not in self.iostats:
                self.iostats[ns.bdev_name] = PerformanceStats(ns.bdev_name)
            stats = self.client.stub.namespace_get_io_stats(pb2.namespace_get_io_stats_req(
                subsystem_nqn=self.subsystem, nsid=ns.nsid))

            iostats = self.iostats[ns.bdev_name]
            iostats.read_ops.update(stats.num_read_ops)
            iostats.read_bytes.update(stats.bytes_read)
            iostats.read_secs.update((stats.read_latency_ticks / stats.tick_rate))
            iostats.write_ops.update(stats.num_write_ops)
            iostats.write_bytes.update(stats.bytes_written)
            iostats.write_secs.update((stats.write_latency_ticks / stats.tick_rate))

    def _get_namespaces(self):
        return self.call_grpc_api('list_namespaces', pb2.list_namespaces_req(subsystem=self.subsystem))

    def _get_subsystems(self):
        return self.call_grpc_api('list_subsystems', pb2.list_subsystems_req())

    def _get_connections(self):
        return self.call_grpc_api('list_connections', pb2.list_connections_req(subsystem=self.subsystem))

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
            event.wait(self.delay)

    def run(self):
        if self.ready:
            asyncio.run(self.start())
