import pymel.core as pm

from maya_frog_rigging_tools import control
from maya_frog_rigging_tools import utils

def add_pins_to_ribbon(ribbon, number_of_pins):
    param_length_u = ribbon.getShape().minMaxRangeU.get()

    pin_list = []

    for i in range(number_of_pins):
        u_pos = (i/float(number_of_pins-1)) * param_length_u[1]
        pin_list.append(pin_to_surface(ribbon, u_pos=u_pos, name_suf=str(i)))

    return pin_list


def create_bezier_ribbon(jnt_chain, prim_axis="x", name="bezier_rbbn"):
    pins = {
        "start_pin": {"parent": jnt_chain[0], "curve_points": [0, 1]},
        "end_pin": {"parent": jnt_chain[-1], "curve_points": [5, 6]},
        "mid_pin": {"curve_points": [3], "tangent": True},
        "start_mid": {"align": [jnt_chain[0], jnt_chain[1]], "curve_points": [2], "tangent": True},
        "end_mid": {"align": [jnt_chain[1], jnt_chain[2]], "curve_points": [4], "tangent": True},
    }

    bezier_points = [
        (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0)
    ]
    bezier_curve = pm.curve(p=bezier_points, bezier=True, name=f"{name}_bezier")
    tangent_grp = pm.group(name=f"{name}_tangent", empty=True)
    pin_grp = pm.group(tangent_grp, name=f"{name}_pins")
    pm.group(pin_grp, bezier_curve, name=f"{name}_null")

    for pin, pin_data in pins.items():
        pin_node = control.create("sphere", f"{name}_{pin}")
        srt_grp = pm.group(pin_node, name=f"{pin_node}_srt")
        null_grp = pm.group(srt_grp, name=f"{pin_node}_null")

        pm.setAttr(f"{pin_node}.visibility", 0)
        curve_points = pin_data.get("curve_points")

        if pin_data.get("parent"):
            pm.parentConstraint(pin_data.get("parent"), srt_grp, name=f"{pin_data.get('parent')}_{pin}_constraint")

        if pin_data.get("align"):
            if len(pin_data.get("align")) > 2:
                raise ValueError("Can't align between more than 2 objects")
            utils.align_center(*pin_data.get("align"), srt_grp)

        if pin_data.get("tangent"):
            pm.parent(null_grp, tangent_grp)
        else:
            pm.parent(null_grp, pin_grp)

        for curve_point in curve_points:
            decompose_matrix = pm.createNode("decomposeMatrix", name=f"{pin_node}_{curve_point}_dcmp")
            pm.connectAttr(
                f"{pin_node}.worldMatrix[0]", f"{decompose_matrix}.inputMatrix", f=True
            )
            pm.connectAttr(
                f"{decompose_matrix}.outputTranslate", f"{bezier_curve}.controlPoints[{curve_point}]", f=True
            )

    pm.pointConstraint(jnt_chain[1], tangent_grp)
    pm.tangentConstraint(f"{name}_start_pin", f"{name}_end_pin", tangent_grp)

    return ribbon


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
    out_matrix = pm.createNode("decomposeMatrix", name=f"{pin_name}_dcmtx")
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
