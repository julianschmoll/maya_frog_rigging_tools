from pymel import core as pm
import numpy as np


def create_eye(name, iris=False, subdiv_res=20):
    sphere = pm.polySphere(n=f"{name}_blend", ax=(1, 0, 0), subdivisionsX=subdiv_res*2, subdivisionsY=subdiv_res*2)[0]
    ctl = pm.circle(name=f"{name}_ctl", radius=2, normal=(1, 0, 0))[0]

    pm.addAttr(
        ctl,
        longName="Iris",
        attributeType='float',
        minValue=0,
        maxValue=1,
        defaultValue=0.5,
        keyable=True
    )

    pm.addAttr(
        ctl,
        longName="Pupil",
        attributeType='float',
        minValue=0,
        maxValue=1,
        defaultValue=0.5,
        keyable=True
    )

    jnt_list = []
    value_list = get_value_list(subdiv_res + 1)
    value_list.reverse()

    pupil_edge = 16

    for i, val in enumerate(value_list):
        pm.select(cl=1)
        joint = pm.joint(n=f"{name}_{i}_bnd")

        remap = pm.createNode("remapValue", n=f"{name}_{i}_remap")
        mult = pm.createNode("multiplyDivide", n=f"{name}_{i}_mult")
        quat = pm.createNode("eulerToQuat", n=f"{name}_{i}_quat")
        clamp = pm.createNode("clamp", n=f"{name}_{i}_clamp")

        if i < pupil_edge:
            pm.connectAttr(ctl + ".Iris", remap + ".inputValue")
        else:
            pm.connectAttr(ctl + ".Pupil", remap + ".inputValue")
        pm.connectAttr(remap + ".outValue", mult + ".input1X")
        pm.connectAttr(mult + ".outputX", quat + ".inputRotateX")
        pm.connectAttr(quat + ".outputQuatX", joint + ".translateX")

        pm.connectAttr(quat + ".outputQuatW", clamp + ".inputR")
        pm.connectAttr(clamp + ".output.outputR", joint + ".scaleY")
        pm.connectAttr(clamp + ".output.outputR", joint + ".scaleZ")

        pm.setAttr(remap + ".outputMin", float(i) / (len(value_list)-1))
        pm.setAttr(remap + ".outputMax", 0)
        pm.setAttr(mult + ".input2X", 180)
        pm.setAttr(clamp + ".maxR", 1000)

        pm.setAttr(f"{remap}.value[0].value_Position", 0)
        pm.setAttr(f"{remap}.value[0].value_FloatValue", val*-1)
        pm.setAttr(f"{remap}.value[0].value_Interp", 1)

        pm.setAttr(f"{remap}.value[1].value_Position", 1)
        pm.setAttr(f"{remap}.value[1].value_FloatValue", val)
        pm.setAttr(f"{remap}.value[1].value_Interp", 1)

        jnt_list.append(joint)

    jnt_grp = pm.group(jnt_list, name=f"{name}_bnd")
    pm.group(jnt_grp, sphere, ctl, name=name)
    # this is currently not what we want as every
    # joint should have 100% influence for according edge loop
    pm.skinCluster(sphere, jnt_list)


def get_value_list(length):
    x_values = np.linspace(0, 1, length)
    # playing with graphs here would make sense, linear seems to work well
    # y_values = 1 / (1 + np.exp(-11.7 * (x_values - 0.5)))
    y_values = x_values
    y_values[0] = 0
    y_values[-1] = 1
    return list(y_values)


# usage: create_eye("eye")
