from pymel import core as pm
import json
from maya import OpenMaya as om


def create_ctl_from_json(file_path, name, ctl_size=1):
    with open(file_path, "r") as f:
        shape_data = json.load(f)

    shape_list = []

    for shape in shape_data:
        new_curve = pm.curve(degree=3, point=shape["points"])
        pm.closeCurve(new_curve, ch=False, ps=False, rpo=True)
        shape_list.append(pm.rename(new_curve, shape["name"]))

    ctl = shape_list.pop(0)

    for shape in shape_list:
        shapes = pm.listRelatives(shape, shapes=True, fullPath=True)
        pm.parent(shapes, ctl, add=True, shape=True)
        pm.delete(shape)

    pm.scale(ctl, ctl_size, ctl_size, ctl_size)
    pm.makeIdentity(ctl, apply=True, t=1, r=1, s=1, n=0)
    pm.xform(ctl, zeroTransformPivots=True)
    pm.rename(ctl, name, ignoreShape=True)

    return ctl


def write_json_from_dag(out_path):
    dag_iter = om.MItDag(om.MItDag.kDepthFirst, om.MFn.kCurve)
    output = []

    while not dag_iter.isDone():
        curve_iter = om.MItCurveCV(dag_iter.currentItem())
        curve = om.MFnDagNode(dag_iter.currentItem())
        dag_iter.next()
        node = {"name": curve.name(), "points": []}

        while not curve_iter.isDone():
            pos = curve_iter.position()
            curve_iter.next()
            node["points"].append([pos.x, pos.y, pos.z])

        output.append(node)

    with open(out_path, mode="w") as output_file:
        json.dump(output, output_file)
