from maya import cmds
import json
from maya import OpenMaya as om


def create_ctl_from_json(file_path):
    with open(file_path, "r") as f:
        shape_data = json.load(f)

    for shape in shape_data:
        new_curve = cmds.curve(degree=3, point=shape["points"])
        cmds.closeCurve(new_curve, ch=False, ps=False, rpo=True)
        cmds.rename(new_curve, shape["name"])


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

    # Save as a json file (or switch this up to use another format)
    with open(out_path, mode="w") as output_file:
        json.dump(output, output_file)
