from ._control import utils
import os


json_dir = os.path.join(
    os.path.abspath(os.curdir), "resources", "controls"
)


ctl_dict = {
    "gear": os.path.join(json_dir, "gear.json")
}


def create(ctl_type, name="ctl", size=1):
    json_path = ctl_dict.get(ctl_type)
    if json_path:
        return utils.create_ctl_from_json(json_path, name, ctl_size=size)
