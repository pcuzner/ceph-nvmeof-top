import os
from packaging import version

delay = 3
server_addr = os.environ.get('SERVER_ADDR', '')
server_port = os.environ.get('SERVER_PORT', 5500)
log_level = 'info'
min_version = version.Version('1.0.0')
