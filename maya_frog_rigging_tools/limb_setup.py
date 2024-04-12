from pymel import core as pm
import logging
import re

from pymel.core.nodetypes import DependNode

from maya_frog_rigging_tools import control

BND_PATTERN = "_bnd"
LOGGER = logging.getLogger("Rigging Utils")


class LimbSetup:
    def __init__(self, root_bnd, prefix_name="limb"):
        self.log = logging.getLogger("Limb Setup")
        self.log.info("Initializing LimbSetup")
        self.root = root_bnd
        self.prefix = prefix_name

    def build_joint_structure(self):
        self.log.info("Building Joint Structure")
        self._create_joint_structure()
        self._create_ctl_guides()

    def build_ctl_rig(self):
        self.log.info("Building Control Structure")
        self._create_ctl_from_guides()
        self._constrain_fk_ik()
        self._create_ik_handle()
        self._setup_stretch()

    def _create_joint_structure(self):
        self.log.info("Duplicating Joint Chain")
        self.root_chain = [self.root] + self.root.listRelatives(allDescendents=True)
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
            "host_guide": None,
            "fk_1_guide": self.fk_chain[0],
            "fk_2_guide": self.fk_chain[2],
            "fk_3_guide": self.fk_chain[1],
            "pole_guide": self.ik_chain[2],
            "root_guide": self.root,
            "ik_guide": self.ik_chain[1]
        }
        for guide_name, joint in self.guide_mapping.items():
            guide = pm.createNode("locator", name=f"{self.prefix}_{guide_name}Shape")
            guides_grp.addChild(f"{self.prefix}_{guide_name}")
            if joint is not None:
                pm.matchTransform(guide, joint)
            self.log.info(f"Created {guide}")

    def _create_ctl_from_guides(self):
        self.log.info("Creating Controls from Guides")
        self.ctl_mapping = {
            "host_guide": "gear",
            "fk_1_guide": "circle",
            "fk_2_guide": "circle",
            "fk_3_guide": "circle",
            "pole_guide": self.ik_chain[2],
            "root_guide": self.root,
            "ik_guide": self.ik_chain[1]
        }
        for guide in self.guide_mapping.keys():
            guide_node = pm.PyNode(f"{self.prefix}_{guide}")
            clean_name = guide.removesuffix("_guide")
            ctl = control.create(
                self.ctl_mapping.get(guide),
                name=f"{self.prefix}_{clean_name}_ctl",
                size=guide_node.scaleX.get()
            )
            pm.matchTransform(guide_node, ctl)

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
