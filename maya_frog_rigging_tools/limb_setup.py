from pymel import core as pm
import logging
import re

from pymel.core.nodetypes import DependNode

from . import control

BND_PATTERN = "_bnd"
LOGGER = logging.getLogger("Rigging Utils")


class LimbSetup:
    def __init__(self, root_bnd, prefix_name="limb", primary_axis="X", secondary_axis="Y", up_axis="Z", ctl_scale=1):
        self.log = logging.getLogger("Limb Setup")
        self.log.info("Initializing LimbSetup")
        self.primary_axis = primary_axis
        self.secondary_axis = secondary_axis
        self.up_axis = up_axis
        self.ctl_scale = ctl_scale
        self.root = root_bnd
        self.prefix = prefix_name

    def build_structure(self):
        self.log.info("Building Joint Structure")
        self._create_joint_structure()
        self._create_ctl_guides()

    def build_ctl_rig(self):
        self.log.info("Building Control Structure")
        self._create_ctl_from_guides()
        self._build_fk_chain()
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
        self.jnt_grp = pm.group(self.fk_chain[0], self.ik_chain[0], self.stretch_chain[0], name=f"{self.prefix}")

    def _create_ctl_guides(self):
        self.log.info("Creating Controls")
        self.guides_grp = pm.group(em=True, name=f"{self.prefix}_guides")
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
            self.guides_grp.addChild(f"{self.prefix}_{guide_name}")
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
                "joint": guide_info.get("joint"),
                "subcomponent": clean_name.split("_")[0],
                "srt": srt_grp,
                "null": null_grp
            }

    def _build_fk_chain(self):
        self.log.info("Building FK Chain")
        fk_subcomponents = {key: value for key, value in self.ctl_data.items() if value['subcomponent'] == 'fk'}
        root_components = {key: value for key, value in self.ctl_data.items() if value['subcomponent'] == 'root'}
        ordered_chain = dict(sorted(fk_subcomponents.items(), key=lambda x: int(x[0].split('_')[-2])))
        previous_chain_element_key, previous_chain_element_value = next(iter(root_components.items()))

        for next_chain_element_key, next_chain_element_value in ordered_chain.items():
            next_ctl = next_chain_element_value.get("node")
            next_jnt = next_chain_element_value.get("joint")

            prev_ctl = previous_chain_element_value.get("node")
            next_srt = next_chain_element_value.get("srt")

            self.log.info(f"Constraining {next_srt} to {prev_ctl}")
            translate_constraint = pm.parentConstraint(
                prev_ctl,
                next_srt,
                mo=True,
                skipRotate=['x', 'y', 'z'],
                weight=1,
                name=f"{prev_ctl}_{next_srt}_trl_constr"
            )
            rotate_constraint = pm.parentConstraint(
                prev_ctl,
                next_srt,
                mo=True,
                skipTranslate=['x', 'y', 'z'],
                weight=1,
                name=f"{prev_ctl}_{next_srt}_rot_constr"
            )

            self.log.debug(f"Add Space switching attributes on {next_ctl}")
            pm.addAttr(
                next_ctl,
                longName="FollowTranslation",
                attributeType='float',
                minValue=0,
                maxValue=1,
                defaultValue=1,
                keyable=True
            )
            pm.addAttr(
                next_ctl,
                longName="FollowRotation",
                attributeType='float',
                minValue=0,
                maxValue=1,
                defaultValue=1,
                keyable=True
            )

            pm.connectAttr(
                f"{next_ctl}.FollowTranslation",
                translate_constraint.attr('w0'),
                force=True
            )
            pm.connectAttr(
                f"{next_ctl}.FollowRotation",
                rotate_constraint.attr('w0'),
                force=True
            )

            self.log.info(f"Constraining {next_jnt} to {next_ctl}")
            pm.parentConstraint(
                next_ctl,
                next_jnt,
                mo=True,
                weight=1,
                name=f"{next_ctl}_{next_jnt}_jnt_constr"
            )

            previous_chain_element_value = next_chain_element_value

    def _constrain_fk_ik(self):
        self.log.info("Constraining IK FK Structure")

        host_component = next((value for value in self.ctl_data.values() if value['subcomponent'] == 'host'), None)
        host_node = host_component.get("node")

        pm.pointConstraint(self.root_chain[2], host_node, mo=True)

        pm.addAttr(
            host_node,
            longName="IkFkSwitch",
            attributeType='float',
            minValue=0,
            maxValue=1,
            defaultValue=1,
            keyable=True
        )
        fk_ik_reverse = pm.createNode("reverse", name=f"{self.prefix}_fk_ik_reverse")
        pm.connectAttr(
            host_node.attr("IkFkSwitch"),
            fk_ik_reverse.attr('inputX'),
            force=True
        )

        for index, constrained in enumerate(self.root_chain):
            joint_constraint = pm.parentConstraint(
                self.fk_chain[index],
                self.ik_chain[index],
                constrained,
                maintainOffset=True,
                name=f"{self.fk_chain[index]}{self.ik_chain[index]}{constrained}_constr"
            )

            self.log.debug(f"Add IK FK Switch Attribute for {joint_constraint}")
            pm.connectAttr(
                host_node.attr("IkFkSwitch"),
                joint_constraint.attr('w0'),
                force=True
            )
            pm.connectAttr(
                fk_ik_reverse.attr('outputX'),
                joint_constraint.attr('w1'),
                force=True
            )

        self.log.info("Setting up IK FK visibility")
        for ctl, control_data in self.ctl_data.items():
            if control_data.get("subcomponent") == "fk":
                pm.connectAttr(
                    host_node.attr("IkFkSwitch"),
                    control_data.get("node").attr('visibility'),
                    force=True
                )
            elif control_data.get("subcomponent") in ["ik", "pole"]:
                pm.connectAttr(
                    fk_ik_reverse.attr('outputX'),
                    control_data.get("node").attr('visibility'),
                    force=True
                )

    def _create_ik_handle(self):
        self.log.info("Creating IK Handle")
        root_component = next((value for value in self.ctl_data.values() if value['subcomponent'] == 'root'), None)
        pole_component = next((value for value in self.ctl_data.values() if value['subcomponent'] == 'pole'), None)
        ik_component = next((value for value in self.ctl_data.values() if value['subcomponent'] == 'ik'), None)
        ik_handle = pm.ikHandle(
            name=f"{root_component['joint']}_to_{ik_component['joint']}_hndl",
            sj=self.ik_chain[0],
            ee=ik_component['joint'],
            sol='ikRPsolver'
        )[0]

        pm.setAttr(f"{ik_handle}.visibility", 0)

        pm.parentConstraint(ik_component['node'], ik_handle)
        pm.poleVectorConstraint(pole_component['node'], ik_handle)

        root_ctl = root_component.get("node")
        pm.pointConstraint(root_ctl, self.jnt_grp, mo=True)

    def _setup_stretch(self):
        self.log.info("Making Limb Stretchy")
        ik_component = next((value for value in self.ctl_data.values() if value['subcomponent'] == 'ik'), None)
        host_component = next((value for value in self.ctl_data.values() if value['subcomponent'] == 'host'), None)

        chain_start = self.stretch_chain[0]
        ik_start = self.ik_chain[0]
        chain_middle = self.stretch_chain[2]
        ik_middle = self.ik_chain[2]
        chain_end = self.stretch_chain[1]

        dist_1 = pm.createNode("distanceBetween", name=f"{chain_start}_{chain_middle}_dist")
        dist_2 = pm.createNode("distanceBetween", name=f"{chain_middle}_{chain_end}_dist")

        pm.connectAttr(f"{chain_start}.worldMatrix[0]", f"{dist_1}.inMatrix1", force=True)
        pm.connectAttr(f"{chain_middle}.worldMatrix[0]", f"{dist_1}.inMatrix2", force=True)
        pm.connectAttr(f"{chain_middle}.worldMatrix[0]", f"{dist_2}.inMatrix1", force=True)
        pm.connectAttr(f"{chain_end}.worldMatrix[0]", f"{dist_2}.inMatrix2", force=True)

        base_length = pm.createNode("addDoubleLinear", name=f"{self.prefix}_length")
        pm.connectAttr(f"{dist_1}.distance", f"{base_length}.input1")
        pm.connectAttr(f"{dist_2}.distance", f"{base_length}.input2")

        loc_name = f"{self.prefix}_end"
        pm.createNode("locator", name=f"{loc_name}Shape")
        pm.matchTransform(loc_name, ik_component.get("node"))
        pm.parent(loc_name, ik_component.get("node"))
        stretch_length = pm.createNode("distanceBetween", name=f"{chain_start}_{loc_name}_dist")
        pm.connectAttr(f"{chain_start}.worldMatrix[0]", f"{stretch_length}.inMatrix1", force=True)
        pm.connectAttr(f"{loc_name}.worldMatrix[0]", f"{stretch_length}.inMatrix2", force=True)

        condition = pm.createNode("condition", name=f"{self.prefix}_stretch_cond")
        pm.setAttr(f"{condition}.operation", 2)
        pm.connectAttr(f"{stretch_length}.distance", f"{condition}.firstTerm", force=True)

        calc_scale = pm.createNode("multiplyDivide", name=f"{self.prefix}_stretch_scale")
        pm.setAttr(f"{calc_scale}.operation", 2)
        pm.connectAttr(f"{base_length}.output", f"{calc_scale}.input2.input2X", force=True)
        pm.connectAttr(f"{stretch_length}.distance", f"{calc_scale}.input1.input1X", force=True)
        pm.connectAttr(f"{calc_scale}.output.outputX", f"{condition}.colorIfTrue.colorIfTrueR", force=True)

        host_node = host_component.get("node")
        pm.addAttr(
            host_node,
            longName="maxStretch",
            attributeType='float',
            minValue=1,
            maxValue=10,
            defaultValue=1.5,
            keyable=True
        )
        pm.addAttr(
            host_node,
            longName="maxSquash",
            attributeType='float',
            minValue=0,
            maxValue=1,
            defaultValue=0,
            keyable=True
        )
        squash_reverse = pm.createNode("reverse", name=f"{self.prefix}_squash_reverse")
        pm.connectAttr(f"{host_node}.maxSquash", squash_reverse.attr('inputX'), force=True)

        max_stretch_condition = pm.createNode("condition", name=f"{self.prefix}_max_stretch_cond")

        pm.setAttr(f"{max_stretch_condition}.operation", 2)
        pm.connectAttr(
            f"{condition}.outColor.outColorR", f"{max_stretch_condition}.colorIfTrue.colorIfTrueR", force=True
        )
        pm.connectAttr(f"{host_node}.maxStretch", f"{max_stretch_condition}.colorIfFalse.colorIfFalseR", force=True)

        pm.connectAttr(f"{condition}.outColor.outColorR", f"{max_stretch_condition}.secondTerm", force=True)
        pm.connectAttr(f"{host_node}.maxStretch", f"{max_stretch_condition}.firstTerm", force=True)

        calc_squash_scale = pm.createNode("multiplyDivide", name=f"{self.prefix}_squash_scale")
        pm.connectAttr(f"{squash_reverse}.output.outputX", f"{calc_squash_scale}.input1.input1X", force=True)
        pm.connectAttr(f"{squash_reverse}.output.outputX", f"{condition}.colorIfFalse.colorIfFalseR", force=True)
        pm.connectAttr(f"{base_length}.output", f"{calc_squash_scale}.input2.input2X", force=True)
        pm.connectAttr(f"{calc_squash_scale}.output.outputX", f"{condition}.secondTerm", force=True)

        pm.connectAttr(
            f"{max_stretch_condition}.outColor.outColorR", f"{ik_start}.scale.scale{self.primary_axis}", force=True
        )
        pm.connectAttr(
            f"{max_stretch_condition}.outColor.outColorR", f"{ik_middle}.scale.scale{self.primary_axis}", force=True
        )

        pm.setAttr(f"{loc_name}.visibility", 0)

    def cleanup(self):
        self.log.info("Cleaning Up Setup")
        pm.delete(self.guides_grp)


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
