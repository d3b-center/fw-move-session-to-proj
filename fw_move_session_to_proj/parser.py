"""Parser module to parse gear config.json."""
from typing import Tuple

from flywheel_gear_toolkit import GearToolkitContext
from fw_core_client import CoreClient

from . import __version__, pkg_name


def parse_config(
    gear_context: GearToolkitContext,
) -> Tuple[dict, CoreClient]:
    """Get api-key as well as config options."""
    api_key_in = gear_context.get_input("api-key")
    fw = CoreClient(
        api_key=api_key_in.get("key"), client_name=pkg_name, client_version=__version__
    )

    return fw
