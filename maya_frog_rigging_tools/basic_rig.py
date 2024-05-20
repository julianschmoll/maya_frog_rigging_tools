from pymel import core as pm
from capito.maya.rig.icons import RigIcons


def create_ctl_structure(index, name, match_bb=None, scale=None, freeze_transforms=True):
    main_ctl = RigIcons().create_rig_icon(index, name)
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


def build_basic_rig(rig_geo):
    main_ctl_dict = create_ctl_structure(
        11, f"{rig_geo}_main_ctl", match_bb=rig_geo
    )

    scale = main_ctl_dict["scale"]
    local_0_scale = [scale[0] * 0.85, scale[0] * 0.85, scale[0] * 0.85]
    local_1_scale = [scale[0] * 0.7, scale[0] * 0.7, scale[0] * 0.7]

    local_0_ctl_dict = create_ctl_structure(
        3, f"{rig_geo}_local_0_ctl", scale=local_0_scale
    )
    local_1_ctl_dict = create_ctl_structure(
        3, f"{rig_geo}_local_1_ctl", scale=local_1_scale
    )

    pm.connectAttr(
        f"{main_ctl_dict['ctl']}.worldMatrix",
        f"{local_0_ctl_dict['srt']}.offsetParentMatrix"
    )
    pm.connectAttr(
        f"{local_0_ctl_dict['ctl']}.worldMatrix",
        f"{local_1_ctl_dict['srt']}.offsetParentMatrix"
    )

    ctl_grp = pm.group(
        main_ctl_dict['null'],
        local_0_ctl_dict['null'],
        local_1_ctl_dict['null'],
        name=f"{rig_geo}_ctl"
    )

    pm.select(rig_geo)
    lattice, lattice_shape, lattice_base = pm.animation.lattice(
        dv=(2, 2, 2), oc=True, name=f"{rig_geo}_ffd"
    )

    lattice_shape.rename(f"{rig_geo}_lattice")
    lattice_base.rename(f"{rig_geo}_lattice_base")


if __name__ == "__main__":
    selection = pm.ls(sl=True)[0]
    build_basic_rig(selection)
