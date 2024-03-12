import os
import sys
import uuid
import regex
import logging
import yaml
from typing import Tuple
logger = logging.getLogger(__name__)


def certs_ok(args) -> Tuple[bool, str]:

    ssl_cert_files = [args.server_cert, args.client_cert, args.client_key]

    # if none of the cert options are set just return true
    if not args.server_cert and not args.client_cert and not args.client_key:
        return True, "ok"

    # if any of the server/client/key paramters are set they must all be
    if not all(ssl_cert_files) and not args.ssl_config:
        return False, "For a secure connection to a gateway, all SSL parameters are required: server-cert, client-cert, client-key"

    # if ssl-config is given and any of the certs - abort
    if args.ssl_config and any(ssl_cert_files):
        return False, "Use ssl-config OR individual cert key file names, not both"

    if all(ssl_cert_files):
        if not all([os.path.exists(f) for f in ssl_cert_files]):
            return False, "One or more cert files not found, please check the paths provided"

    # if server/client/key parameters ensure the files all exist
    if args.ssl_config:
        ok, msg = validate_ssl_config()
        if not ok:
            return False, msg
    return True, "ok"


def validate_ssl_config(filename: str) -> Tuple[bool, str]:
    required_keys = ['server-cert', 'client-cert', 'client-key']

    if not os.path.exists(filename):
        return False, f"{filename} does not exist"
    if not os.path.isfile(filename):
        return False, f"{filename} exists, but is not a file"

    with open(file=filename, mode='r') as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError:
            return False, f"{filename} contains invalid YAML"

    if not all([key in data for key in required_keys]):
        return False, f"{filename} must contain keys: {','.join(required_keys)}"

    return True, "ok"


def abort(rc: int, msg: str):
    logger.critical(f"nvmeof-top has encountered an error: {msg}")
    print(msg)
    sys.exit(rc)


def lb_group(grp_id: int):
    """Provide a meaningful default when load-balancing is not in use"""
    return "N/A" if grp_id == 0 else f"{grp_id}"


def bytes_to_MB(bytes: int, si: int = 1024):
    """Simple conversion of bytes to with MiB or MB"""
    return (bytes / si) / si


def valid_nqn(nqn: str) -> str:
    """Perform basic validation on the nqn string"""
    # Examples:
    #   nqn.2016-06.io.spdk:cnode1
    #   nqn.2014-08.org.nvmexpress:uuid:ee889718-8c69-40d3-8e78-5be049f966a6

    if not 11 < len(nqn) < 224:
        raise ValueError("nqn length is invalid. must be between 11-223 characters in length")

    if not nqn.startswith("nqn."):
        raise ValueError("nqn name must begin with nqn")

    dot_qualifiers = nqn.split('.')
    if not nqn.count('.') == 3:
        raise ValueError("nqn must consist of 3 main qualifiers")

    valid_date = regex.findall(r"\d{4}-\d{2}", dot_qualifiers[1])  # YYYY-MM
    if not valid_date:
        raise ValueError("The 2nd qualifer of an nqn must be of the form YYYY-MM")

    colon_qualifiers = nqn.split(':')
    if not 0 < len(colon_qualifiers) < 3:
        raise ValueError("a valid nqn has either 1 or 2 ':' symbols")

    if len(colon_qualifiers) == 3:
        if colon_qualifiers[1] == 'uuid' and not valid_uuid(colon_qualifiers[2]):
            raise ValueError("nqn contains an invalid uuid suffix")

    return nqn


def valid_uuid(uuid_str: str) -> bool:
    """Test that a given UUID string is correctly formatted"""
    try:
        uuid.UUID(uuid_str)
    except ValueError:
        return False
    return True
