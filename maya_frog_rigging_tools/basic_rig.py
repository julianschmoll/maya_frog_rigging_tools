import logging

from capito.maya.rig.icons import RigIcons
from pymel import core as pm


class BasicRig:
    """Building a basic squash and stretch rig."""

    log = logging.getLogger("Basic Rigger")
    scale = 1
    ctl_data = {}
    jnt_data = {}
    lattice_data = {}

    def __init__(self, rig_geo=None, name=None):
        self.rig_geo = rig_geo or pm.ls(sl=1)
        if name:
            self.name = name
            return

        if isinstance(self.rig_geo, list):
            self.name = self.rig_geo[0].name().split(":")[-1]
        else:
            self.name = self.rig_geo.name().split(":")[-1]

    def build(self):
        self.log.info(f"Building basic rig {self.name}")
        self._build_main_ctl()
        self._build_lattice()
        ctl_grp, geo_parent = self._order_outliner()
        self._add_anim_attributes(ctl_grp, geo_parent)
        pm.select(clear=True)

    def _order_outliner(self):
        ctl_grp = pm.group(
            self.main_ctl_grp,
            self.ctl_data['lattice_low']['null'],
            self.ctl_data['lattice_mid']['null'],
            self.ctl_data['lattice_up']['null'],
            name=f"{self.name}_ctl"
        )

        no_transform_grp = pm.group(
            self.lattice_data["shape"],
            self.lattice_data["base"],
            self.jnt_data["low"],
            self.jnt_data["mid"],
            self.jnt_data["up"],
            name=f"{self.name}_rig_no_transform"
        )

        root_grp = pm.group(empty=True, name=f"{self.name}_rig")
        no_transform_grp.visibility.set(0)

        for ctl in [self.ctl_data["local_0"]["ctl"], self.ctl_data["local_1"]["ctl"]]:
            for attr in ["scaleX", "scaleY", "scaleZ"]:
                pm.setAttr(f"{ctl}.{attr}", lock=1, k=0)

        geo_parent = self.rig_geo[0].fullPath().split("|")[1]

        pm.parent(ctl_grp, root_grp)
        pm.parent(no_transform_grp, root_grp)
        pm.parent(geo_parent, root_grp)

        return ctl_grp, geo_parent

    def _add_anim_attributes(self, ctl_grp, rig_parent):
        main_ctl = self.ctl_data["main"]["ctl"]
        pm.addAttr(
            main_ctl,
            ln="hideCtlOnPlayback",
            attributeType='bool',
            defaultValue=True,
            keyable=True
        )
        pm.addAttr(
            main_ctl,
            ln="geoUnselectable",
            attributeType='bool',
            defaultValue=True,
            keyable=True
        )
        pm.connectAttr(f"{main_ctl}.hideCtlOnPlayback", f"{ctl_grp}.drawOverride.hideOnPlayback")
        pm.setAttr(f"{rig_parent}.overrideDisplayType", 2)
        pm.connectAttr(f"{main_ctl}.geoUnselectable", f"{rig_parent}.overrideEnabled")

    def _build_lattice(self):
        pm.select(self.rig_geo)
        lattice, lattice_shape, lattice_base = pm.animation.lattice(
            dv=(2, 3, 2), oc=True, name=f"{self.name}_ffd"
        )

        self.lattice_data["lattice"] = lattice
        self.lattice_data["shape"] = lattice_shape
        self.lattice_data["base"] = lattice_base

        lattice_shape.rename(f"{self.name}_lattice")
        lattice_base.rename(f"{self.name}_lattice_base")

        lattice_bb = pm.exactWorldBoundingBox(lattice_shape)
        pos_list = get_corner_positions(lattice_bb)
        jnt_list = []

        for index, position in enumerate(pos_list):
            bnd_jnt = pm.createNode("joint", name=f"{lattice_shape}_{index}_bnd")
            pm.move(*position, bnd_jnt, absolute=True, worldSpace=True)
            jnt_list.append(bnd_jnt)

        low_grp = pm.group(jnt_list[:4], name=f"{lattice_shape}_lower_bnd")
        mid_grp = pm.group(jnt_list[4:8], name=f"{lattice_shape}_middle_bnd")
        up_grp = pm.group(jnt_list[8:], name=f"{lattice_shape}_upper_bnd")

        self.jnt_data["low"] = low_grp
        self.jnt_data["mid"] = mid_grp
        self.jnt_data["up"] = up_grp

        pm.skinCluster(
            jnt_list, lattice_shape, toSelectedBones=True, name=f"{lattice_shape}_cluster"
        )

        lattice_ctl_scale = [self.scale * 0.7, self.scale * 0.7, self.scale * 0.7]

        lattice_up_ctl_data = create_ctl_structure(
            1, f"{self.name}_upper_ctl", scale=lattice_ctl_scale, color_index=9
        )
        self.ctl_data["lattice_up"] = lattice_up_ctl_data

        lattice_mid_ctl_data = create_ctl_structure(
            1, f"{self.name}_mid_ctl", scale=lattice_ctl_scale, color_index=9
        )
        self.ctl_data["lattice_mid"] = lattice_mid_ctl_data

        lattice_low_ctl_data = create_ctl_structure(
            1, f"{self.name}_low_ctl", scale=lattice_ctl_scale, color_index=9
        )
        self.ctl_data["lattice_low"] = lattice_low_ctl_data

        match_transforms(up_grp, lattice_up_ctl_data["null"])
        match_transforms(mid_grp, lattice_mid_ctl_data["null"])
        match_transforms(low_grp, lattice_low_ctl_data["null"])

        constraint_list = [
            (lattice_low_ctl_data, low_grp),
            (lattice_mid_ctl_data, mid_grp),
            (lattice_up_ctl_data, up_grp)
        ]

        for ctl_dict, rig_grp in constraint_list:
            ctl = ctl_dict["ctl"]
            pm.parentConstraint(
                ctl,
                rig_grp,
                mo=True,
                weight=1,
                name=f"{ctl}_{low_grp}_parent_constraint"
            )

            pm.scaleConstraint(
                ctl,
                rig_grp,
                mo=True,
                weight=1,
                name=f"{ctl}_{low_grp}_scale_constraint"
            )

        for target in [lattice_low_ctl_data['srt'], lattice_up_ctl_data['srt']]:
            ctl = self.ctl_data["local_1"]['ctl']
            pm.parentConstraint(
                ctl,
                target,
                mo=True,
                weight=1,
                name=f"{ctl}_{target}_parent_constraint"
            )
            pm.scaleConstraint(
                ctl,
                target,
                mo=True,
                weight=1,
                name=f"{ctl}_{target}_scale_constraint"
            )
        pm.parentConstraint(
            lattice_low_ctl_data['ctl'],
            lattice_up_ctl_data['ctl'],
            lattice_mid_ctl_data['srt'],
            mo=True,
            weight=1,
            name=f"{lattice_low_ctl_data['ctl']}_{lattice_up_ctl_data['ctl']}_{lattice_mid_ctl_data['srt']}_parent_constraint"
        )
        stretch_dist = pm.createNode(
            "distanceBetween",
            name=f"{self.name}_stretch_dist"
        )
        pm.connectAttr(
            f"{lattice_low_ctl_data['ctl']}.worldMatrix",
            f"{stretch_dist}.inMatrix1",
            force=True
        )
        pm.connectAttr(
            f"{lattice_up_ctl_data['ctl']}.worldMatrix",
            f"{stretch_dist}.inMatrix2",
            force=True
        )
        initial_dist = pm.getAttr(f"{stretch_dist}.distance")
        stretch_scale = pm.createNode(
            "multiplyDivide",
            name=f"{self.name}_stretch_scale"
        )

        sq_str_blend = pm.createNode(
            "blendColors",
            name=f"{self.name}_sqstr_blend"
        )

        adjust_scale = pm.createNode(
            "multiplyDivide",
            name=f"{self.name}_adjust_scale"
        )
        pm.setAttr(f"{adjust_scale}.input1X", initial_dist)
        pm.connectAttr(f"{self.ctl_data['main']['ctl']}.scale", f"{adjust_scale}.input2")
        pm.setAttr(f"{stretch_scale}.operation", 2)
        pm.connectAttr(f"{stretch_dist}.distance", f"{stretch_scale}.input2X")
        pm.connectAttr(f"{adjust_scale}.output", f"{stretch_scale}.input1")

        pm.connectAttr(f"{stretch_scale}.outputX", f"{sq_str_blend}.color1R")
        pm.connectAttr(f"{stretch_scale}.outputX", f"{sq_str_blend}.color1G")
        pm.connectAttr(f"{stretch_scale}.outputX", f"{sq_str_blend}.color1B")

        pm.setAttr(f"{sq_str_blend}.color2R", 1)
        pm.setAttr(f"{sq_str_blend}.color2G", 1)
        pm.setAttr(f"{sq_str_blend}.color2B", 1)

        pm.connectAttr(f"{sq_str_blend}.output", f"{lattice_mid_ctl_data['srt']}.scale")

        pm.addAttr(
            self.ctl_data['main']['ctl'],
            ln="sqStrFac",
            attributeType='float',
            defaultValue=1,
            minValue=0,
            maxValue=1,
            keyable=True
        )
        pm.connectAttr(f"{self.ctl_data['main']['ctl']}.sqStrFac", f"{sq_str_blend}.blender")

        pm.scaleConstraint(
            self.ctl_data["main"]['ctl'],
            lattice_mid_ctl_data['null'],
            mo=True,
            weight=1,
            name=f"{self.ctl_data['main']['ctl']}_{lattice_mid_ctl_data['null']}_scale_constraint"
        )

    def _build_main_ctl(self):
        main_ctl_data = create_ctl_structure(
            11, f"{self.name}_main_ctl", match_bb=self.rig_geo, color_index=2
        )
        self.ctl_data["main"] = main_ctl_data

        self.scale = main_ctl_data["scale"][0]

        local_0_scale = [self.scale * 0.85, self.scale * 0.85, self.scale * 0.85]
        local_1_scale = [self.scale * 0.7, self.scale * 0.7, self.scale * 0.7]

        local_0_ctl_data = create_ctl_structure(
            3, f"{self.name}_local_0_ctl", scale=local_0_scale, color_index=4
        )
        self.ctl_data["local_0"] = local_0_ctl_data

        local_1_ctl_data = create_ctl_structure(
            3, f"{self.name}_local_1_ctl", scale=local_1_scale, color_index=5
        )
        self.ctl_data["local_1"] = local_1_ctl_data

        pm.connectAttr(
            f"{main_ctl_data['ctl']}.worldMatrix",
            f"{local_0_ctl_data['srt']}.offsetParentMatrix"
        )
        pm.connectAttr(
            f"{local_0_ctl_data['ctl']}.worldMatrix",
            f"{local_1_ctl_data['srt']}.offsetParentMatrix"
        )

        self.main_ctl_grp = pm.group(
            main_ctl_data['null'],
            local_0_ctl_data['null'],
            local_1_ctl_data['null'],
            name=f"{self.name}_main_ctl"
        )


def match_transforms(source_obj, target_obj, **kwargs):
    constraint = pm.parentConstraint(source_obj, target_obj, **kwargs)
    pm.delete(constraint)


def match_bounding_box_scale(to, frm, scale=True):
    to = pm.ls(to, flatten=True)
    frm = pm.ls(frm, flatten=True)

    x_min, y_min, z_min, x_max, y_max, z_max = pm.exactWorldBoundingBox(frm)
    ax, ay, az = [x_max - x_min, y_max - y_min, z_max - z_min]

    result = []
    for obj in to:

        x_min, y_min, z_min, x_max, y_max, z_max = pm.exactWorldBoundingBox(obj)
        bx, by, bz = [x_max - x_min, y_max - y_min, z_max - z_min]

        old_x, old_y, old_z = pm.xform(obj, q=1, s=1, r=1)
        diffx, diffy, diff_z = [ax / bx, ay / by, az / bz]
        b_scale_new = [old_x * diffx, old_y * diffy, old_z * diff_z]
        [result.append(i) for i in b_scale_new]

        if scale:
            pm.xform(obj, scale=b_scale_new)

    return result


def get_corner_positions(coordinates):
    x_min, y_min, z_min, x_max, y_max, z_max = coordinates
    y_mid = (y_max + y_min) / 2

    return [
        [x_min, y_min, z_min],
        [x_min, y_min, z_max],
        [x_max, y_min, z_min],
        [x_max, y_min, z_max],
        [x_min, y_mid, z_min],
        [x_min, y_mid, z_max],
        [x_max, y_mid, z_min],
        [x_max, y_mid, z_max],
        [x_min, y_max, z_min],
        [x_min, y_max, z_max],
        [x_max, y_max, z_min],
        [x_max, y_max, z_max],
    ]


def create_ctl_structure(index, name, match_bb=None, scale=None, freeze_transforms=True, color_index=2):
    icon = RigIcons()
    main_ctl = icon.create_rig_icon(index, name)
    pm.select(main_ctl)
    icon.colorize_selected_curves(color_index)
    main_ctl.rename(name)

    srt = main_ctl.listRelatives(parent=True)[0]
    srt.rename(f"{name}_srt")

    null = srt.listRelatives(parent=True)[0]
    null.rename(f"{name}_null")

    if match_bb:
        scale = match_bounding_box_scale(null, match_bb, scale=False)
        scale[0] = scale[0] * 2.5
        scale[1] = 0
        scale[2] = scale[0]
        pm.xform(null, scale=scale)

    if scale:
        pm.xform(null, scale=scale)

    if freeze_transforms:
        pm.makeIdentity(null, apply=True, t=1, r=1, s=1, n=0)

    return {"null": null, "srt": srt, "ctl": main_ctl, "scale": scale}


if __name__ == "__main__":
    BasicRig().build()
