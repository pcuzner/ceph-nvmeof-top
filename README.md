# nvmeof-top
A top-like tool to display nvmeof gateway performance data

## Testing
The easiest way to test the tool is via a container image

Show the command options
```
# podman run --rm --interactive --tty --net host quay.io/pcuzner/nvmeof-top:latest -h
usage: nvmeof-top.py [-h] [--delay DELAY] [--mode {batch,console}] --subsystem SUBSYSTEM [--server-addr SERVER_ADDR] [--server-port SERVER_PORT]
                     [--with-timestamp] [--no-headings] [--count COUNT]

options:
  -h, --help            show this help message and exit
  --delay DELAY, -d DELAY
                        Refresh interval (secs) [3]
  --mode {batch,console}, -m {batch,console}
                        Run time mode [batch]
  --subsystem SUBSYSTEM, -n SUBSYSTEM
                        NQN of the subsystem to monitor (REQUIRED)
  --server-addr SERVER_ADDR, -a SERVER_ADDR
                        Gateway server IP address
  --server-port SERVER_PORT, -p SERVER_PORT
                        Gateway server control path port
  --with-timestamp      Prefix namespaces statistics with a timestamp in batch mode
  --no-headings         Omit column headings in batch mode
  --count COUNT, -c COUNT
                        Number of interations for stats gathering
```

Run the tool against the subsystem 'nqn.2016-06.io.spdk:cnode1' on gateway at 192.168.122.48
```
# podman run --rm --interactive --tty --net host -e SERVER_ADDR=192.168.122.48 quay.io/pcuzner/nvmeof-top:latest -n nqn.2016-06.io.spdk:cnode1 --with-timestamp
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
alias nvmeof-top='podman run --rm --interactive --tty --net host -e SERVER_ADDR=192.168.122.48 quay.io/pcuzner/nvmeof-top:latest'
```
then just run `nvmeof-top` :) 

## TO-DO List
- [x] test out dependencies in a virt env  
- [ ] build a container and push to quay.io
- [ ] Add logging
- [ ] Add timing to the log for each collect cycle
- [ ] Add a simple urwid implementation
