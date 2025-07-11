#!/usr/bin/env python
"""The run script."""
import logging
import sys

from flywheel_gear_toolkit import GearToolkitContext

from fw_move_session_to_proj.main import run
from fw_move_session_to_proj.parser import parse_config

log = logging.getLogger(__name__)

def main(context: GearToolkitContext) -> None:  # pragma: no cover
    """Parse config and run."""
    fw = parse_config(context)

    e_code = run(fw, context)

    sys.exit(e_code)

if __name__ == "__main__":  # pragma: no cover
    with GearToolkitContext() as gear_context:
        gear_context.init_logging()
        main(gear_context)
