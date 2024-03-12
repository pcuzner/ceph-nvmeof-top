# nvmeof-top
A top-like tool to display [Ceph](https://ceph.io) nvmeof gateway performance data.

## Running `nvmeof-top`
The easiest way to use the tool is via a container.

Show the command options
```
# podman run --rm --interactive --tty --net host quay.io/cuznerp/nvmeof-top:latest -h
usage: nvmeof-top.py [-h] [--delay DELAY] [--batch] [--subsystem SUBSYSTEM]
                     [--server-addr SERVER_ADDR] [--server-port SERVER_PORT]
                     [--with-timestamp] [--no-headings] [--count COUNT]
                     [--log-level {debug,info,warning,error,critical}]
                     [--server-cert SERVER_CERT] [--client-cert CLIENT_CERT]
                     [--client-key CLIENT_KEY] [--ssl-config SSL_CONFIG]

options:
  -h, --help            show this help message and exit
  --delay DELAY, -d DELAY
                        Refresh interval (secs) [3]
  --batch, -b           Run in batch mode with output returned to stdout
  --subsystem SUBSYSTEM, -n SUBSYSTEM
                        NQN of the subsystem to monitor (REQUIRED)
  --server-addr SERVER_ADDR, -a SERVER_ADDR
                        Gateway server IP address
  --server-port SERVER_PORT, -p SERVER_PORT
                        Gateway server control path port
  --with-timestamp      Prefix namespaces statistics with a timestamp in batch
                        mode
  --no-headings         Omit column headings in batch mode
  --count COUNT, -c COUNT
                        Number of interations for stats gathering
  --log-level {debug,info,warning,error,critical}
                        Logging level [info]
  --server-cert SERVER_CERT
                        Path to server cert (root certificate)
  --client-cert CLIENT_CERT
                        Path to client cert
  --client-key CLIENT_KEY
                        Path to client key
  --ssl-config SSL_CONFIG
                        YAML file that contains the certs and keys inline
```

Run the tool against the subsystem 'nqn.2016-06.io.spdk:cnode1' on gateway at 192.168.122.48
```
# podman run --rm --interactive --tty --net host -e SERVER_ADDR=192.168.122.48 quay.io/cuznerp/nvmeof-top:latest -n nqn.2016-06.io.spdk:cnode1 -b --with-timestamp
waiting for samples...
2024-02-29 22:25:32
NSID  RBD pool/image                         r/s    rMB/s  r_await  rareq-sz     w/s   wMB/s  w_await  wareq-sz  LBGrp   QoS
   1  rbd/datastore-4                         21     0.08     0.53      4.00       0    0.00     0.00      0.00   N/A     No
   2  rbd/datastore-5                          0     0.00     0.00      0.00      31    0.25     4.84      8.00   N/A     No
   3  rbd/datastore-3                         31     0.49     0.72     16.00      31    0.49     4.44     16.00   N/A     No
   4  rbd/datastore-1                          0     0.00     0.00      0.00       0    0.00     0.00      0.00   N/A     No
   5  rbd/datastore-2                          0     0.00     0.00      0.00       0    0.00     0.00      0.00   N/A     No
2024-02-29 22:25:35
NSID  RBD pool/image                         r/s    rMB/s  r_await  rareq-sz     w/s   wMB/s  w_await  wareq-sz  LBGrp   QoS
   1  rbd/datastore-4                         21     0.08     0.51      4.00       0    0.00     0.00      0.00   N/A     No
   2  rbd/datastore-5                          0     0.00     0.00      0.00      31    0.25     4.41      8.00   N/A     No
   3  rbd/datastore-3                         31     0.49     0.65     16.00      31    0.49     4.32     16.00   N/A     No
   4  rbd/datastore-1                          0     0.00     0.00      0.00       0    0.00     0.00      0.00   N/A     No
   5  rbd/datastore-2                          0     0.00     0.00      0.00       0    0.00     0.00      0.00   N/A     No
2024-02-29 22:25:38
NSID  RBD pool/image                         r/s    rMB/s  r_await  rareq-sz     w/s   wMB/s  w_await  wareq-sz  LBGrp   QoS
   1  rbd/datastore-4                         21     0.08     0.53      4.00       0    0.00     0.00      0.00   N/A     No
   2  rbd/datastore-5                          0     0.00     0.00      0.00      31    0.24     4.47      8.00   N/A     No
   3  rbd/datastore-3                         31     0.49     0.64     16.00      31    0.49     4.38     16.00   N/A     No
   4  rbd/datastore-1                          0     0.00     0.00      0.00       0    0.00     0.00      0.00   N/A     No
   5  rbd/datastore-2                          0     0.00     0.00      0.00       0    0.00     0.00      0.00   N/A     No
^C
nvmeof-top stopped.
```

To make it easier to run, just set up an alias in your .bashrc file  
```
alias nvmeof-top='podman run --rm --interactive --tty --net host -e SERVER_ADDR=192.168.122.48 quay.io/cuznerp/nvmeof-top:latest'
```
then just run `nvmeof-top` :wink: 

### Development Mode
Some features of the tool may not be supported by the current GRPC server within the gateway. To look at all the features of the tool, it includes a data generator. This dem modemay be used during UI development. To run the nvmeof-top with autogenerated data:  
```
# python3 ./nvmeof-top.py  --log-level=debug --demo=10
```
In the above example demo is set to 10, so the display will show activity across 10 namespaces. Note that, in this mode, you also don't need to provide an nqn since this is also autogenerated :smile:  

## Example Output


https://github.com/pcuzner/ceph-nvmeof-top/assets/3703087/f5b2aa72-592b-4f57-b1f1-4870b3c41843




## TO-DO List
- [x] test out dependencies in a virt env  
- [x] build a container and push to quay.io
- [x] Add logging
- [x] Add timing to the log for each collect cycle
- [x] Add a simple urwid implementation
- [x] Add a help screen
- [x] Add a runtime options panel
- [x] Add table sort support
- [x] Add ability to change refresh delay
- [x] Add latency thresholds
- [ ] Add SSL support to the client stub
- [ ] Create an spec for rpm based deployment
- [ ] Add a setup.py for local installs using setuptools


## GRPC Changes Needed
At the time of writing the nvmeof GRPC methods do not provide all the data that is needed to support this tool. The list below describes the further work needed in the core nvmeof grpc code.
1. The subsystem info is using the older grpc call (cli) and is missing max_namespaces (currently highlighted yellow)
2. grpc is not exposing a method to fetch all iostats, so the code has to repeatedly fetch data for each namespace
3. grpc does not provide a method which provides the reactor cpu thread statistics


## Issues
1. The UI hardcodes the default max namespaces per subsystem (256), since the actual value is not exposed by the grpc calls. This value is highlighted in yellow.
2. SSL mode has not really been tested

