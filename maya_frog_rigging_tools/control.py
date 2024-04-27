from ._control import json_control
import os
import logging

from maya_frog_rigging_tools import utils

LOGGER = logging.getLogger("Rig Control")


def create(ctl_type, name="ctl", size=1):
    root_path = utils.get_project_root()
    json_dir = os.path.join(root_path, "resources", "controls")
    json_path = os.path.join(json_dir, f"{ctl_type}.json")
    if json_path:
        LOGGER.info(f"Creating {ctl_type} control from json")
        return json_control.create_ctl_from_json(json_path, name, ctl_size=size)
