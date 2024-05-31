from pymel import core as pm
from capito.maya.rig.icons import RigIcons
from maya_frog_rigging_tools import utils as rig_utils
from maya_frog_menu import asset


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


def build_basic_rig(rig_geo=None, name=None):
    if not rig_geo:
        rig_geo = pm.ls(sl=1)
    if not name:
        if isinstance(rig_geo, list):
            name = rig_geo[0].name().split(":")[-1]  # don't consider namespace
        else:
            name = rig_geo.name().split(":")[-1]

    # ToDo: This should be a class later, doing those for speed now
    local_0_ctl_dict, local_1_ctl_dict, main_ctl_dict, main_ctl_grp, scale = build_main_ctl(name, rig_geo)

    lattice_base, lattice_low_dict, lattice_mid_dict, lattice_shape, lattice_upper_dict, low_grp, mid_grp, up_grp = build_lattice(
        local_1_ctl_dict, main_ctl_dict, name, rig_geo, scale)

    ctl_grp = pm.group(
        f"{lattice_mid_dict['null']}",
        f"{lattice_upper_dict['null']}",
        f"{lattice_low_dict['null']}",
        main_ctl_grp,
        name=f"{name}_ctl"
    )

    no_transform_grp = pm.group(
        lattice_shape,
        lattice_base,
        low_grp,
        mid_grp,
        up_grp,
        name=f"{name}_rig_no_transform"
    )

    root_grp = asset.create_asset()

    pm.setAttr(f"{no_transform_grp}.visibility", 0)

    pm.parent(ctl_grp, root_grp)
    pm.parent(no_transform_grp, root_grp)
    pm.parent(rig_geo, root_grp)

    pm.addAttr(
        main_ctl_dict['ctl'],
        ln="hideCtlOnPlayback",
        attributeType='bool',
        defaultValue=True,
        keyable=True
    )

    pm.connectAttr(f"{main_ctl_dict['ctl']}.hideCtlOnPlayback", f"{ctl_grp}.drawOverride.hideOnPlayback")

    for ctl in [local_0_ctl_dict["ctl"], local_1_ctl_dict["ctl"]]:
        for attr in ["scaleX", "scaleY", "scaleZ"]:
            pm.setAttr(f"{ctl}.{attr}", lock=1, k=0)

    pm.setAttr(f"{rig_geo}.overrideEnabled", 1)
    pm.setAttr(f"{rig_geo}.overrideDisplayType", 2)
    pm.select(clear=True)


def build_lattice(local_1_ctl_dict, main_ctl_dict, name, rig_geo, scale):
    pm.select(rig_geo)
    lattice, lattice_shape, lattice_base = pm.animation.lattice(
        dv=(2, 3, 2), oc=True, name=f"{name}_ffd"
    )
    lattice_shape.rename(f"{name}_lattice")
    lattice_base.rename(f"{name}_lattice_base")
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
    pm.skinCluster(
        jnt_list, lattice_shape, toSelectedBones=True, name=f"{lattice_shape}_cluster"
    )
    lattice_ctl_scale = [scale[0] * 0.7, scale[0] * 0.7, scale[0] * 0.7]
    lattice_upper_dict = create_ctl_structure(
        1, f"{name}_upper_ctl", scale=lattice_ctl_scale, color_index=9
    )
    lattice_mid_dict = create_ctl_structure(
        1, f"{name}_mid_ctl", scale=lattice_ctl_scale, color_index=9
    )
    lattice_low_dict = create_ctl_structure(
        1, f"{name}_low_ctl", scale=lattice_ctl_scale, color_index=9
    )
    rig_utils.match_transforms(up_grp, lattice_upper_dict["null"])
    rig_utils.match_transforms(mid_grp, lattice_mid_dict["null"])
    rig_utils.match_transforms(low_grp, lattice_low_dict["null"])
    for ctl_dict, rig_grp in [(lattice_low_dict, low_grp), (lattice_mid_dict, mid_grp), (lattice_upper_dict, up_grp)]:
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
    for target in [lattice_low_dict['srt'], lattice_upper_dict['srt']]:
        ctl = local_1_ctl_dict['ctl']
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
        lattice_low_dict['ctl'],
        lattice_upper_dict['ctl'],
        lattice_mid_dict['srt'],
        mo=True,
        weight=1,
        name=f"{lattice_low_dict['ctl']}_{lattice_upper_dict['ctl']}_{lattice_mid_dict['srt']}_parent_constraint"
    )
    stretch_dist = pm.createNode(
        "distanceBetween",
        name=f"{name}_stretch_dist"
    )
    pm.connectAttr(
        f"{lattice_low_dict['ctl']}.worldMatrix",
        f"{stretch_dist}.inMatrix1",
        force=True
    )
    pm.connectAttr(
        f"{lattice_upper_dict['ctl']}.worldMatrix",
        f"{stretch_dist}.inMatrix2",
        force=True
    )
    initial_dist = pm.getAttr(f"{stretch_dist}.distance")
    stretch_scale = pm.createNode(
        "multiplyDivide",
        name=f"{name}_stretch_scale"
    )
    adjust_scale = pm.createNode(
        "multiplyDivide",
        name=f"{name}_adjust_scale"
    )
    pm.setAttr(f"{adjust_scale}.input1X", initial_dist)
    pm.connectAttr(f"{main_ctl_dict['ctl']}.scale", f"{adjust_scale}.input2")
    pm.setAttr(f"{stretch_scale}.operation", 2)
    pm.connectAttr(f"{stretch_dist}.distance", f"{stretch_scale}.input2X")
    pm.connectAttr(f"{adjust_scale}.output", f"{stretch_scale}.input1")
    pm.connectAttr(f"{stretch_scale}.outputX", f"{lattice_mid_dict['srt']}.scaleX")
    pm.connectAttr(f"{stretch_scale}.outputX", f"{lattice_mid_dict['srt']}.scaleY")
    pm.connectAttr(f"{stretch_scale}.outputX", f"{lattice_mid_dict['srt']}.scaleZ")
    pm.scaleConstraint(
        main_ctl_dict['ctl'],
        lattice_mid_dict['null'],
        mo=True,
        weight=1,
        name=f"{main_ctl_dict['ctl']}_{lattice_mid_dict['null']}_scale_constraint"
    )
    return lattice_base, lattice_low_dict, lattice_mid_dict, lattice_shape, lattice_upper_dict, low_grp, mid_grp, up_grp


def build_main_ctl(name, rig_geo):
    main_ctl_dict = create_ctl_structure(
        11, f"{name}_main_ctl", match_bb=rig_geo, color_index=2
    )
    scale = main_ctl_dict["scale"]
    local_0_scale = [scale[0] * 0.85, scale[0] * 0.85, scale[0] * 0.85]
    local_1_scale = [scale[0] * 0.7, scale[0] * 0.7, scale[0] * 0.7]
    local_0_ctl_dict = create_ctl_structure(
        3, f"{name}_local_0_ctl", scale=local_0_scale, color_index=4
    )
    local_1_ctl_dict = create_ctl_structure(
        3, f"{name}_local_1_ctl", scale=local_1_scale, color_index=5
    )
    pm.connectAttr(
        f"{main_ctl_dict['ctl']}.worldMatrix",
        f"{local_0_ctl_dict['srt']}.offsetParentMatrix"
    )
    pm.connectAttr(
        f"{local_0_ctl_dict['ctl']}.worldMatrix",
        f"{local_1_ctl_dict['srt']}.offsetParentMatrix"
    )
    main_ctl_grp = pm.group(
        main_ctl_dict['null'],
        local_0_ctl_dict['null'],
        local_1_ctl_dict['null'],
        name=f"{name}_main_ctl"
    )
    return local_0_ctl_dict, local_1_ctl_dict, main_ctl_dict, main_ctl_grp, scale
