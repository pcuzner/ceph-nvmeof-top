## Building the protobuf files
The project includes the protobuf files compatible with 1.x

However to rebuild
1. grab the latest .proto file from the main ceph-nvmeof 
2. install python3-grpcio-tools package
3. cd nvmeof-top/proto
4. Run 
```
python3 -m grpc_tools.protoc --proto_path=/home/paul/src/ceph-nvmeof-top/nvmeof_top/proto --python_out=. --grpc_python_out
=. gateway.proto
```

^^ needs revision. the resulting gateway_pb2_grpc.py file is not using the correct import path to pick up gateway_pb2.py
needed a prefix of nvmeof_top.proto