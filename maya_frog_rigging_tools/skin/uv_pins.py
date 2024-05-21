from maya import cmds
from pymel import core as pm


def create_pin_on_vert(name=None, vert=None):
    if not vert:
        vert = pm.ls(sl=True, fl=True)[0]

    mesh = pm.polyListComponentConversion(vert, fv=True)[0]
    transform = pm.listRelatives(mesh, parent=True, fullPath=True)[0]

    if not name:
        name = f"{transform.split(':')[-1]}_{vert.index()}_pin"

    uv_values = get_uv_values(vert)
    pm.createNode("locator", name=f"{name}_locShape")
    pin_loc = pm.PyNode(f"{name}_loc")
    pin_dcmp = pm.createNode("decomposeMatrix", name=f"{name}_dcmp")
    uv_pin_node = add_uv_pin(transform, uv_values, name=name)

    pm.connectAttr(f"{uv_pin_node}.outputMatrix[0]", f"{pin_dcmp}.inputMatrix")
    pm.connectAttr(f"{pin_dcmp}.outputTranslate", f"{pin_loc}.translate")

    pm.select(pin_loc)

    return pin_loc


def get_uv_values(vert):
    pm.select(vert)
    cmds.ConvertSelectionToUVs()
    return cmds.polyEditUV(query=True)


def pin_on_nurbs_surface(nurbs_surface, u_pos=0.5, v_pos=0.5, name_suf="#"):
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

def add_uv_pin(mesh_transform, coordinates, name="uv_pin"):
    all_shapes = pm.listRelatives(
        mesh_transform, shapes=True, children=True, parent=False
    )
    intermediates = [
        x for x in all_shapes if pm.getAttr("{}.intermediateObject".format(x)) == 1
    ]
    non_intermediates = [x for x in all_shapes if x not in intermediates]
    deformed_mesh = non_intermediates[0]
    if not intermediates:
        duplicated_mesh = pm.duplicate(mesh_transform, name="f{mesh_transform}_orig")[0]
        original_mesh = pm.listRelatives(duplicated_mesh, children=True)[0]
        pm.parent(original_mesh, mesh_transform, shape=True, r=True)
        pm.delete(duplicated_mesh)
        _raw_list = cmds.listConnections(
            str(deformed_mesh), source=True, destination=False, connections=True, plugs=True
        )
        if _raw_list:
            connection_pairs = list(zip(_raw_list[1::2], _raw_list[::2]))
            for pair in connection_pairs:
                pm.connectAttr(
                    pair[0], pair[1].replace(str(deformed_mesh), str(original_mesh)), force=True
                )

        pm.setAttr(f"{original_mesh}.hiddenInOutliner", 1)
        pm.setAttr(f"{original_mesh}.intermediateObject", 1)
    else:
        original_mesh = intermediates[0]

    uv_pin_node = pm.createNode("uvPin", name=name)

    pm.connectAttr(
        f"{deformed_mesh}.worldMesh", f"{uv_pin_node}.deformedGeometry"
    )
    pm.connectAttr(
        f"{original_mesh}.outMesh", f"{uv_pin_node}.originalGeometry"
    )
    pm.setAttr(f"{uv_pin_node}.coordinate[0]", coordinates[0], coordinates[1])

    return uv_pin_node
