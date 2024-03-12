from .proto import gateway_pb2_grpc as pb2_grpc
import grpc


class GatewayClient:

    def __init__(self, server_addr: str,
                 server_port: int,
                 server_cert_path: str = '',
                 client_cert_path: str = '',
                 client_key_path: str = '',
                 ssl_config: str = ''):
        self.server_addr = server_addr
        self.server_port = server_port
        self._stub = None

    @property
    def server(self):
        return f"{self.server_addr}:{self.server_port}"

    @property
    def stub(self):
        if not self._stub:
            raise AttributeError("client stub not initialised. Use the connect() method before using the stub")
        return self._stub

    def connect(self):
        """Connect to the GRPC endpoint

        For the purposes of simplicity we're just using insecure mode. If the target is unavailable
        a grpc._channel._InactiveRpcError will be thrown and will need to be caught. Hint a normal try/except didn't catch it!
        """

        channel = grpc.insecure_channel(self.server)
        self._stub = pb2_grpc.GatewayStub(channel)
