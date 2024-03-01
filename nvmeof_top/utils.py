import sys
import uuid
import regex
import argparse
import logging
logger = logging.getLogger(__name__)


def abort(rc: int, msg: str):
    logger.critical(f"nvmeof-top has hit a problem: {msg}")
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
        raise argparse.ArgumentTypeError("nqn length is invalid. must be between 11-223 characters in length")

    if not nqn.startswith("nqn."):
        raise argparse.ArgumentTypeError("nqn name must begin with nqn")

    dot_qualifiers = nqn.split('.')
    if not nqn.count('.') == 3:
        raise argparse.ArgumentTypeError("nqn must consist of 3 main qualifiers")

    valid_date = regex.findall(r"\d{4}-\d{2}", dot_qualifiers[1])  # YYYY-MM
    if not valid_date:
        raise argparse.ArgumentTypeError("The 2nd qualifer of an nqn must be of the form YYYY-MM")

    colon_qualifiers = nqn.split(':')
    if not 0 < len(colon_qualifiers) < 3:
        raise argparse.ArgumentTypeError("a valid nqn has either 1 or 2 ':' symbols")

    if len(colon_qualifiers) == 3:
        if colon_qualifiers[1] == 'uuid' and not valid_uuid(colon_qualifiers[2]):
            raise argparse.ArgumentTypeError("nqn contains an invalid uuid suffix")

    return nqn


def valid_uuid(uuid_str: str) -> bool:
    """Test that a given UUID string is correctly formatted"""
    try:
        uuid.UUID(uuid_str)
    except ValueError:
        return False
    return True
