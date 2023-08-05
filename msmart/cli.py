import asyncio
import argparse
import logging

from msmart.const import OPEN_MIDEA_APP_ACCOUNT, OPEN_MIDEA_APP_PASSWORD
from msmart.discover import Discover
from msmart import __version__

_LOGGER = logging.getLogger(__name__)


async def _discover(ip: str, count: int, account: str, password: str, china: bool, **_kwargs):
    """Discover Midea devices and print configuration information."""

    _LOGGER.info(f"msmart version: {__version__}")
    _LOGGER.info(
        f"Only supports AC devices. Only supports MSmartHome and 美的美居.")

    if china and (account == OPEN_MIDEA_APP_ACCOUNT or password == OPEN_MIDEA_APP_PASSWORD):
        _LOGGER.error(
            "To use China server set account (phone number) and password of 美的美居.")
        exit(1)

    if ip is None or ip == "":
        devices = await Discover.discover(account=account, password=password, discovery_packets=count)
    else:
        dev = await Discover.discover_single(ip, account=account, password=password, discovery_packets=count)
        devices = [dev]

    if len(devices) == 0:
        _LOGGER.error("No devices found.")

    for device in devices:
        _LOGGER.info("Found device:\n%s", device)


def main():
    parser = argparse.ArgumentParser(description="Discover Midea devices and print device information.",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        "-d", "--debug", help="Enable debug logging.", action="store_true")
    parser.add_argument(
        "-a", "--account", help="MSmartHome or 美的美居 account username.", default=OPEN_MIDEA_APP_ACCOUNT)
    parser.add_argument(
        "-p", "--password", help="MSmartHome or 美的美居 account password.", default=OPEN_MIDEA_APP_PASSWORD)
    parser.add_argument(
        "-i", "--ip", help="IP address of a device. Useful if broadcasts don't work, or to query a single device.")
    parser.add_argument(
        "-c", "--count", help="Number of broadcast packets to send.", default=3, type=int)
    parser.add_argument("--china", help="Use China server.",
                        action="store_true")
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    try:
        asyncio.run(_discover(**vars(args)))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
