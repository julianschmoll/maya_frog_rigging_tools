from pymel import core as pm
import logging
import re

from pymel.core.nodetypes import DependNode

from . import control

BND_PATTERN = "_bnd"
LOGGER = logging.getLogger("Rigging Utils")


class LimbSetup:
    def __init__(self, root_bnd, prefix_name="limb"):
        self.log = logging.getLogger("Limb Setup")
        self.log.info("Initializing LimbSetup")
        self.root = root_bnd
        self.prefix = prefix_name

    def build_structure(self):
        self.log.info("Building Joint Structure")
        self._create_joint_structure()
        self._create_ctl_guides()

    def build_ctl_rig(self):
        self.log.info("Building Control Structure")
        self._create_ctl_from_guides()
        self._connect_fk_chain()
        self._constrain_fk_ik()
        self._create_ik_handle()
        self._setup_stretch()

    def _create_joint_structure(self):
        self.log.info("Duplicating Joint Chain")
        self.root_chain = [self.root] + self.root.listRelatives(allDescendents=True)
        if not len(self.root_chain) > 2:
            raise RuntimeError(
                "Can't Setup Limb, please input chain with at least 2 elements!"
            )
        self.fk_chain = duplicate_and_rename_hierarchy(
            self.root, BND_PATTERN, "_fk"
        )
        self.ik_chain = duplicate_and_rename_hierarchy(
            self.root, BND_PATTERN, "_ik"
        )
        self.stretch_chain = duplicate_and_rename_hierarchy(
            self.root, BND_PATTERN, "_stretch"
        )

    def _create_ctl_guides(self):
        self.log.info("Creating Controls")
        guides_grp = pm.group(em=True, name=f"{self.prefix}_guides")
        self.guide_mapping = {
            "host_guide": {"ctl_shape": "gear"},
            "fk_1_guide": {"joint": self.fk_chain[0], "ctl_shape": "circle"},
            "fk_2_guide": {"joint": self.fk_chain[2], "ctl_shape": "circle"},
            "fk_3_guide": {"joint": self.fk_chain[1], "ctl_shape": "circle"},
            "pole_guide": {"joint": self.ik_chain[2], "ctl_shape": "sphere"},
            "root_guide": {"joint": self.root, "ctl_shape": "needle"},
            "ik_guide": {"joint": self.ik_chain[1], "ctl_shape": "box"}
        }
        for guide_name, guide_info in self.guide_mapping.items():
            joint = guide_info.get("joint")
            guide = pm.createNode("locator", name=f"{self.prefix}_{guide_name}Shape")
            guides_grp.addChild(f"{self.prefix}_{guide_name}")
            if joint is not None:
                pm.matchTransform(guide, joint)
            self.log.info(f"Created {guide}")

    def _create_ctl_from_guides(self):
        self.log.info("Creating Controls from Guides")
        self.ctl_data = {}
        controls_grp = pm.group(em=True, name=f"{self.prefix}_ctl")
        for guide, guide_info in self.guide_mapping.items():
            guide_node = pm.PyNode(f"{self.prefix}_{guide}")
            clean_name = guide.removesuffix("_guide")
            ctl_name = f"{self.prefix}_{clean_name}_ctl"
            ctl = control.create(
                guide_info.get("ctl_shape"),
                name=ctl_name,
            )
            srt_grp = pm.group(ctl, name=f"{ctl_name}_srt")
            null_grp = pm.group(srt_grp,  name=f"{ctl_name}_null")
            controls_grp.addChild(null_grp)
            pm.matchTransform(null_grp, guide_node)
            self.ctl_data[ctl_name] = {
                "node": ctl,
                "subcomponent": clean_name.split("_")[0],
                "srt": srt_grp,
                "null": null_grp
            }

    def _connect_fk_chain(self):
        self.log.info("Connecting FK Chain")

    def _constrain_fk_ik(self):
        self.log.info("Constraining IK FK Structure")
        for index, constrained in enumerate(self.root_chain):
            pm.parentConstraint(
                self.fk_chain[index],
                self.ik_chain[index],
                constrained,
                maintainOffset=True
            )
            # add node connection to parent constraint (ik and reverse fk)

    def _create_ik_handle(self):
        self.log.info("Created IK Handle")

    def _setup_stretch(self):
        self.log.info("Making Limb Stretchy")


def duplicate_and_rename_hierarchy(root_joint, old_name_pattern, new_name_pattern):
    dupl_list: list[DependNode] = [pm.duplicate(root_joint, renameChildren=True)[0]]
    renamed_list = []

    for node in dupl_list[0].listRelatives(allDescendents=True):
        dupl_list.append(node)

    for node in dupl_list:
        old_name = node.name()
        new_name = re.sub(old_name_pattern, new_name_pattern, old_name)
        if new_name.endswith("1"):
            new_name = new_name[:-1]
        LOGGER.debug(f"Renaming {old_name} to {new_name}")
        renamed_list.append(node.rename(new_name))

    return renamed_list


"""
Use like this:
import sys
import importlib

sys.path.append("maya_frog_rigging_tools")
from maya_frog_rigging_tools import limb_setup

importlib.reload(maya_frog_rigging_tools)
importlib.reload(limb_setup)

root = pm.PyNode("shoulder_r_bnd")
limb_setup = limb_setup.LimbSetup(root, "arm_r")
limb_setup.build_joint_structure()
# Then place locators
limb_setup.build_ctl_rig()
"""
