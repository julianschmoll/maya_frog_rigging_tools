import pymel.core as pm

from maya_frog_rigging_tools import control
from maya_frog_rigging_tools import utils

import logging

LOGGER = logging.getLogger("Ribbon")


def add_pins_to_ribbon(ribbon, number_of_pins):
    param_length_u = ribbon.getShape().minMaxRangeU.get()

    pin_list = []

    for i in range(number_of_pins):
        u_pos = (i/float(number_of_pins-1)) * param_length_u[1]
        pin_list.append(pin_to_surface(ribbon, u_pos=u_pos, name_suf=str(i)))

    return pin_list


def create_bezier_ribbon(
        jnt_chain, host_node, prim_axis="x", offset_up=(0, 0, 1), offset_low=(0, 0, -1), name="bezier_rbbn"
):
    pins = {
        "start_pin": {"parent": jnt_chain[0], "curve_points": [0, 1]},
        "end_pin": {"parent": jnt_chain[-1], "curve_points": [5, 6]},
        "mid_pin": {"match_transforms": jnt_chain[1], "curve_points": [3], "tangent": True},
        "start_mid": {"match_transforms": jnt_chain[1], "pos": 2, "curve_points": [2], "tangent": True},
        "end_mid": {"match_transforms": jnt_chain[1], "pos": 4, "curve_points": [4], "tangent": True},
    }

    bezier_points = get_bezier_points(jnt_chain)

    bezier_curve = pm.curve(p=bezier_points, bezier=True, name=f"{name}_bezier")
    up_curve = pm.curve(p=bezier_points, bezier=True, name=f"{name}_up_loft_bezier")
    low_curve = pm.curve(p=bezier_points, bezier=True, name=f"{name}_low_loft_bezier")

    tangent_grp = pm.group(name=f"{name}_tangent", empty=True)
    tangent_null = pm.group(tangent_grp, name=f"{name}_tangent_null")
    utils.match_transforms(jnt_chain[1], tangent_null)

    pin_grp = pm.group(tangent_null, name=f"{name}_pins")
    parent_group = pm.group(pin_grp, bezier_curve, up_curve, low_curve, name=f"{name}_null")

    for pin, pin_data in pins.items():
        pin_node = control.create("sphere", f"{name}_{pin}")
        srt_grp = pm.group(pin_node, name=f"{pin_node}_srt")
        null_grp = pm.group(srt_grp, name=f"{pin_node}_null")

        pm.setAttr(f"{pin_node}.visibility", 0)
        curve_points = pin_data.get("curve_points")

        if pin_data.get("parent"):
            pm.parentConstraint(pin_data.get("parent"), srt_grp, name=f"{pin_data.get('parent')}_{pin}_constraint")

        if pin_data.get("match_transforms"):
            utils.match_transforms(pin_data.get("match_transforms"), srt_grp)

        if pin_data.get("pos"):
            pm.xform(srt_grp, t=bezier_points[pin_data.get("pos")], ws=True)

        if pin_data.get("tangent"):
            pm.parent(null_grp, tangent_grp)
        else:
            pm.parent(null_grp, pin_grp)

        upper_pin = pm.duplicate(pin_node, name=f"{name}_up_{pin}")[0]
        lower_pin = pm.duplicate(pin_node, name=f"{name}_low_{pin}")[0]

        pm.parent(upper_pin, pin_node)
        pm.parent(lower_pin, pin_node)

        pm.move(*offset_up, upper_pin, relative=True, objectSpace=True)
        pm.move(*offset_low, lower_pin, relative=True, objectSpace=True)

        for curve_point in curve_points:
            decompose_matrix = pm.createNode("decomposeMatrix", name=f"{pin_node}_{curve_point}_dcmp")
            upper_decompose_matrix = pm.createNode("decomposeMatrix", name=f"{pin_node}_{curve_point}_up_dcmp")
            lower_decompose_matrix = pm.createNode("decomposeMatrix", name=f"{pin_node}_{curve_point}_low_dcmp")

            pm.connectAttr(
                f"{pin_node}.worldMatrix[0]",
                f"{decompose_matrix}.inputMatrix", f=True
            )
            pm.connectAttr(
                f"{upper_pin}.worldMatrix[0]",
                f"{upper_decompose_matrix}.inputMatrix", f=True
            )
            pm.connectAttr(
                f"{lower_pin}.worldMatrix[0]",
                f"{lower_decompose_matrix}.inputMatrix", f=True
            )

            pm.connectAttr(
                f"{decompose_matrix}.outputTranslate",
                f"{bezier_curve}.controlPoints[{curve_point}]", f=True
            )
            pm.connectAttr(
                f"{upper_decompose_matrix}.outputTranslate",
                f"{up_curve}.controlPoints[{curve_point}]", f=True
            )
            pm.connectAttr(
                f"{lower_decompose_matrix}.outputTranslate",
                f"{low_curve}.controlPoints[{curve_point}]", f=True
            )

    tangent = constrain_tangent(jnt_chain, name, tangent_null)

    lofted_surface = pm.loft(
        bezier_curve, up_curve, low_curve,
        ch=1, u=1, c=0, ar=1, d=3, ss=1, rn=0, po=0, rsn=True, name=name
    )

    pm.parent(lofted_surface, parent_group)

    LOGGER.info(f"Created {lofted_surface}")

    pm.addAttr(
        host_node,
        longName="roundness",
        attributeType='float',
        minValue=0,
        maxValue=2,
        defaultValue=0,
        keyable=True
    )
    pm.addAttr(
        host_node,
        longName="roundTangent",
        attributeType='float',
        minValue=0,
        maxValue=1,
        defaultValue=0.5,
        keyable=True
    )

    pm.connectAttr(
        f"{host_node}.roundness",
        f"{tangent_null}.scale.scale{prim_axis.upper()}",
        force=True
    )

    pm.connectAttr(
        f"{host_node}.roundTangent",
        f"{tangent}.blender",
        force=True
    )

    return lofted_surface[0]


def constrain_tangent(jnt_chain, name, tangent_null):
    pm.pointConstraint(jnt_chain[1], tangent_null, name=f"{name}_{tangent_null}_point_constraint")
    chain_start_matrix = pm.createNode("decomposeMatrix", name=f"{name}_{jnt_chain[0]}_tang_dcmp")
    chain_middle_matrix = pm.createNode("decomposeMatrix", name=f"{name}_{jnt_chain[1]}_tang_dcmp")
    blend_rotation = pm.createNode("blendColors", name=f"{name}_{jnt_chain[0]}_{jnt_chain[1]}_tang_blend")
    pm.connectAttr(
        f"{jnt_chain[0]}.worldMatrix[0]", f"{chain_start_matrix}.inputMatrix", f=True
    )
    pm.connectAttr(
        f"{jnt_chain[1]}.worldMatrix[0]", f"{chain_middle_matrix}.inputMatrix", f=True
    )
    pm.connectAttr(
        f"{chain_start_matrix}.outputRotate", f"{blend_rotation}.color1", f=True
    )
    pm.connectAttr(
        f"{chain_middle_matrix}.outputRotate", f"{blend_rotation}.color2", f=True
    )
    pm.connectAttr(
        f"{blend_rotation}.output", f"{tangent_null}.rotate", f=True
    )
    return blend_rotation


def get_bezier_points(joints):
    point_list = []

    for joint in joints:
        point_list.append(
            tuple(joint.getTranslation(space='world'))
        )

    point_list.insert(0, point_list[0])
    point_list.insert(3, point_list[3])
    point_list.insert(2, utils.get_center([point_list[0], point_list[2]]))
    point_list.insert(4, utils.get_center([point_list[3], point_list[4]]))

    return point_list


def pin_to_surface(nurbs_surface, u_pos=0.5, v_pos=0.5, name_suf="#"):
    # Adjusted from Chris Lesage (https://gist.github.com/chris-lesage/0dd01f1af56c00668f867393bb68c4d7)
    point_on_surface = pm.createNode("pointOnSurfaceInfo", name=f"{nurbs_surface.name()}_pin_{name_suf}_pos")
    nurbs_surface.getShape().worldSpace.connect(point_on_surface.inputSurface)

    param_length_u = nurbs_surface.getShape().minMaxRangeU.get()
    param_length_v = nurbs_surface.getShape().minMaxRangeV.get()

    pin_name = f"{nurbs_surface.name()}_pin_{name_suf}"
    pin_locator = pm.spaceLocator(name=pin_name).getShape()
    pin_locator.addAttr('parameterU', at='double', keyable=True, dv=u_pos)
    pin_locator.addAttr('parameterV', at='double', keyable=True, dv=v_pos)

    pin_locator.parameterU.setMin(param_length_u[0])
    pin_locator.parameterV.setMin(param_length_v[0])
    pin_locator.parameterU.setMax(param_length_u[1])
    pin_locator.parameterV.setMax(param_length_v[1])
    pin_locator.parameterU.connect(point_on_surface.parameterU)
    pin_locator.parameterV.connect(point_on_surface.parameterV)

    mtx = pm.createNode("fourByFourMatrix", name=f"{pin_name}_mtx")
    out_matrix = pm.createNode("decomposeMatrix", name=f"{pin_name}_dcmp")
    mtx.output.connect(out_matrix.inputMatrix)
    out_matrix.outputTranslate.connect(pin_locator.getTransform().translate)
    out_matrix.outputRotate.connect(pin_locator.getTransform().rotate)

    point_on_surface.normalizedTangentUX.connect(mtx.in00)
    point_on_surface.normalizedTangentUY.connect(mtx.in01)
    point_on_surface.normalizedTangentUZ.connect(mtx.in02)
    mtx.in03.set(0)

    point_on_surface.normalizedNormalX.connect(mtx.in10)
    point_on_surface.normalizedNormalY.connect(mtx.in11)
    point_on_surface.normalizedNormalZ.connect(mtx.in12)
    mtx.in13.set(0)

    point_on_surface.normalizedTangentVX.connect(mtx.in20)
    point_on_surface.normalizedTangentVY.connect(mtx.in21)
    point_on_surface.normalizedTangentVZ.connect(mtx.in22)
    mtx.in23.set(0)

    point_on_surface.positionX.connect(mtx.in30)
    point_on_surface.positionY.connect(mtx.in31)
    point_on_surface.positionZ.connect(mtx.in32)
    mtx.in33.set(1)

    return pm.PyNode(pin_name)
