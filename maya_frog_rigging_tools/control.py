from ._control import utils
import os
from pathlib import Path
import logging

# Get the current working directory
cwd = Path.cwd()
parent_dir = os.path.dirname(cwd)
json_dir = os.path.join(parent_dir, "resources", "controls")

LOGGER = logging.getLogger("Rig Controls")


def create(ctl_type, name="ctl", size=1):
    LOGGER.info(json_dir)
    json_path = os.path.join(json_dir, f"{ctl_type}.json")
    if json_path:
        return utils.create_ctl_from_json(json_path, name, ctl_size=size)
