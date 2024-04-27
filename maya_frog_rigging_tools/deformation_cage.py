from maya import cmds
from maya import OpenMaya as om
import logging
import pymel.core as pm


logger = logging.getLogger("Deformation Cage")


def create_deform_cage(mesh_name, t_pose_objs, ctl_size=1, smooth_iterations=2):
    cage_ctl_group = pm.group(empty=True, name="cage_ctl")
    input_mesh = pm.PyNode(mesh_name)
    ctl_list = []
    jnt_list = []

    for vert_num in range(input_mesh.numVertices()):
        vert_name = f"{mesh_name}_{vert_num}"

        orig_group = pm.group(empty=True, name=f"{vert_name}_orig")
        orig_group.setParent(cage_ctl_group)

        srt_group = pm.group(empty=True, name=f"{vert_name}_srt")
        srt_group.setParent(orig_group)

        curve_sphere = create_sphere_ctl(f"{vert_name}", ctl_size)
        curve_sphere.setParent(srt_group)
    
        ctl_list.append(curve_sphere)

        bind_joint = pm.joint(name=f"{vert_name}_bnd")
        bind_joint.setParent(curve_sphere)
        bind_joint.visibility.set(False)

        bpm_joint = pm.joint(name=f"{vert_name}_bpm")
        bpm_joint.setParent(srt_group)
        bpm_joint.visibility.set(False)

        jnt_list.append((bind_joint, bpm_joint))

        bnd_jnts = get_bound_joints(mesh_name, vert_num)

        if len(bnd_jnts) == 2:
            jnt1, jnt1_weight = bnd_jnts[0]
            jnt2, jnt2_weight = bnd_jnts[1]
            
            blend = pm.createNode('blendMatrix', name=f"{orig_group}_blendMatrix")
            mult_jnt_1 = pm.createNode('multMatrix', name=f"{jnt1}_{blend}_mm")
            mult_jnt_2 = pm.createNode('multMatrix', name=f"{jnt2}_{blend}_mm")

            jnt1.worldMatrix[0].connect(mult_jnt_1.matrixIn[0])
            cage_ctl_group.worldInverseMatrix[0].connect(mult_jnt_1.matrixIn[1])

            jnt2.worldMatrix[0].connect(mult_jnt_2.matrixIn[0])
            cage_ctl_group.worldInverseMatrix[0].connect(mult_jnt_2.matrixIn[1])

            mult_jnt_1.matrixSum.connect(blend.inputMatrix)
            mult_jnt_2.matrixSum.connect(blend.target[0].targetMatrix)

            blend.envelope.set(jnt2_weight)
            blend.outputMatrix.connect(orig_group.offsetParentMatrix)
        elif len(bnd_jnts) > 2:
            wt_add_matrix = pm.createNode('wtAddMatrix', name=f"{orig_group}_wtAddMatrix")

            for bnd_idx in range(len(bnd_jnts)):
                jnt, jnt_weight = bnd_jnts[bnd_idx]

                mult_matrix = pm.createNode('multMatrix', name=f"{jnt}_{wt_add_matrix}_mm")

                jnt.worldMatrix[0].connect(mult_matrix.matrixIn[0])
                cage_ctl_group.worldInverseMatrix[0].connect(mult_matrix.matrixIn[1])

                mult_matrix.matrixSum.connect(wt_add_matrix.wtMatrix[bnd_idx].matrixIn)
                wt_add_matrix.wtMatrix[bnd_idx].weightIn.set(jnt_weight)

            wt_add_matrix.matrixSum.connect(orig_group.offsetParentMatrix)
        else:
            jnt, jnt_weight = bnd_jnts[0]
            jnt.worldMatrix[0].connect(orig_group.offsetParentMatrix)

        vert_position = input_mesh.getPoint(vert_num, space="world")
        orig_group.setTranslation(vert_position, space="world")
        orig_group.setRotation(vert_position, space="world")

        normal = input_mesh.getVertexNormal(vert_num, space='world', angleWeighted=True)
        orient_along_normal(srt_group, normal)

        for attr in ["scaleX", "scaleY", "scaleZ", "rotateX", "rotateY", "rotateZ"]:
            cmds.setAttr(f"{str(curve_sphere)}.{attr}", keyable = False, cb = False, lock = True)

    logger.info("Created Control Groups")

    create_ctl_nurbs(input_mesh, ctl_list, cage_ctl_group)

    logger.info("Created Wireframe Display")

    smoothed = duplicate_smoothed(input_mesh, iterations=smooth_iterations)
    pm.skinCluster(
        [tup[0] for tup in jnt_list], smoothed, toSelectedBones=True, name="tmp_cluster"
    )

    for t_pose in t_pose_objs:
        logger.info(f"Skinning {t_pose}")
        t_pose_mesh = pm.PyNode(t_pose)
        nice_name = t_pose.replace('|', '_').replace(":", "_")
        cage_cluster = pm.skinCluster(
            [tup[0] for tup in jnt_list], t_pose_mesh, toSelectedBones=True, name=f"{nice_name}_cage_cluster"
        )
        copy_skin_weights(smoothed, t_pose_mesh)
        logger.info("Copied Skin Weights")
        try:
            smoothSkinCluster(t_pose_mesh, intensity=0.7, itterations=smooth_iterations*10)
        except:
            logger.warning("Failed to smooth Skin Weights")
        for index in range(len(jnt_list)):
            bpm_jnt = jnt_list[index][1]
            cmds.connectAttr(
                bpm_jnt + ".worldInverseMatrix[0]", cage_cluster + f".bindPreMatrix[{index}]", f=True
            )

    pm.delete(smoothed)


def copy_skin_weights(source_obj, target_obj):
    source_skin_cluster = pm.listConnections(
        pm.PyNode(source_obj).listRelatives(s=True), type='skinCluster'
    )[0]
    target_skin_cluster = pm.listConnections(
        pm.PyNode(target_obj).listRelatives(s=True), type='skinCluster'
    )[0]
    pm.copySkinWeights(
        sourceSkin=source_skin_cluster,
        destinationSkin=target_skin_cluster,
        noMirror=True,
        surfaceAssociation='closestPoint',
        influenceAssociation=['label', 'oneToOne'],
        normalize=False
    )


def duplicate_smoothed(source_object, iterations=1, delete_history=True):
    smoothed = pm.duplicate(source_object)[0]
    pm.rename(smoothed, f"{source_object}_smoothed")
    pm.polySmooth(smoothed, method=0, divisions=iterations)
    if delete_history:
        pm.delete(smoothed, constructionHistory=True)
    return smoothed


def create_sphere_ctl(name, ctl_size=1):
    control_data = [
        (name, (0, 0, 90)),
        ("ctl_2", (90, 0, 0)),
        ("ctl_3", (90, 60, 0)),
        ("ctl_4", (90, 120, 0))
    ]
    controls = []

    for name, rotation in control_data:
        control = pm.circle(name=name, ch=False, normal=(1, 0, 0), radius=1, center=(0, 0, 0))[0]
        pm.rotate(control, rotation, relative=True)
        controls.append(control)

    for control in controls:
        pm.makeIdentity(control, apply=True, t=1, r=1, s=1)
        pm.makeIdentity(control, apply=True, t=1, r=1, s=1, n=0)
        pm.xform(control, zeroTransformPivots=True)

    main_ctl = controls.pop(0)

    for control in controls:
        shapes = pm.listRelatives(control, shapes=True, fullPath=True)
        pm.parent(shapes, main_ctl, add=True, shape=True)
        pm.delete(control)

    pm.scale(main_ctl, ctl_size, ctl_size, ctl_size)
    pm.makeIdentity(main_ctl, apply=True, t=1, r=1, s=1, n=0)
    pm.xform(main_ctl, zeroTransformPivots=True)
    colorize(main_ctl, color=[0.5, 0.5, 0.5])
    return main_ctl


def colorize(transform, color=None):
    if color is None:
        color = [1, 1, 1]
    is_rgb = isinstance(color, (tuple, list))
    color_attribute = "overrideColorRGB" if is_rgb else "overrideColor"
    for shape in transform.getShapes():
        shape.setAttr("overrideEnabled", 1)
        shape.setAttr("overrideRGBColors", is_rgb)
        shape.setAttr(color_attribute, color)


def orient_along_normal(srt_group, normal):
    x_axis = normal.cross(pm.datatypes.Vector(0, 1, 0)).normal()
    y_axis = normal
    z_axis = x_axis.cross(y_axis)
    rotation_matrix = [
        x_axis.x, x_axis.y, x_axis.z, 0,
        y_axis.x, y_axis.y, y_axis.z, 0,
        z_axis.x, z_axis.y, z_axis.z, 0,
        0, 0, 0, 1
    ]

    pm.xform(srt_group, matrix=rotation_matrix)


def get_bound_joints(mesh, vert_num):
    bind_joints = []

    connected_skin_clusters = pm.listConnections(
        pm.PyNode(mesh).listRelatives(s=True), type='skinCluster'
    )

    if len(set(connected_skin_clusters)) != 1:
        raise ValueError("More than one or no skin Cluster Connected")

    skin_cluster = connected_skin_clusters[0]

    for joint in pm.skinCluster(skin_cluster, query=True, inf=True):
        weight = pm.skinPercent(
            skin_cluster, f"{mesh}.vtx[{vert_num}]", transform=joint, query=True, value=True
        )
        if weight:
            influence = (joint, weight)
            bind_joints.append(influence)
    return bind_joints


def create_ctl_nurbs(cage_mesh, input_ctl_list, parent):
    connectivity_map = list()

    for i in range(len(cmds.ls(cage_mesh + '.vtx[*]', flatten=True))):
        connected_verts = get_connected_vertices(cage_mesh, i)
        for vert in connected_verts:
            connected_point = [i, vert]
            inverse_point = connected_point[::-1]
            if connectivity_map.count(inverse_point) == 0:
                connectivity_map.append(connected_point)

    cage_transform = cmds.createNode(
        "transform",
        name="{}_cageDisplay".format(cage_mesh),
        parent=str(parent),
    )
    cmds.setAttr("{}.overrideEnabled".format(cage_transform), True)
    cmds.setAttr("{}.overrideDisplayType".format(cage_transform), 1)
    for point in connectivity_map:
        control1 = input_ctl_list[point[0]]
        control2 = input_ctl_list[point[1]]

        line_name = "cageLine_{}_{}".format(point[0], point[1])
        display_line = create_display_line(
            point1=control1, point2=control2, parent=None, name=line_name
        )
        shape = cmds.listRelatives(display_line, s=True)[0]
        cmds.parent(shape, cage_transform, r=True, s=True)
        cmds.delete(display_line)


def get_connected_vertices(mesh, vertex_id):
    m_sel = om.MSelectionList()

    om.MGlobal.getSelectionListByName("{}.vtx[{}]".format(mesh, vertex_id), m_sel)
    dag_path = om.MDagPath()
    component = om.MObject()
    m_sel.getDagPath(0, dag_path, component)

    iter_mesh = om.MItMeshVertex(dag_path, component)
    connected_vertices = om.MIntArray()
    iter_mesh.getConnectedVertices(connected_vertices)

    return connected_vertices


def create_display_line(point1, point2, name, parent=None, display_type="temp"):
    if display_type not in ["norm", "temp", "ref"]:
        logger.error(
            "{} is not a valid display type. Valid values are: ['norm', 'temp', 'ref']".format(
                display_type
            )
        )
        display_type = "temp"

    display_line = create_curve_from_transform([point1, point2], name=name, degree=1)

    display_type_dict = {"norm": 0, "temp": 1, "ref": 2}

    cmds.setAttr(display_line + ".overrideEnabled", 1)
    cmds.setAttr(display_line + ".overrideDisplayType", display_type_dict[display_type])
    if parent:
        cmds.parent(display_line, parent)

    mm1 = cmds.createNode("multMatrix", n=display_line + "_1_mm")
    mm2 = cmds.createNode("multMatrix", n=display_line + "_2_mm")
    dcmp1 = cmds.createNode("decomposeMatrix", n=display_line + "_1_dcmp")
    dcmp2 = cmds.createNode("decomposeMatrix", n=display_line + "_2_dcmp")

    cmds.connectAttr(point1 + ".worldMatrix", mm1 + ".matrixIn[0]", f=True)
    cmds.connectAttr(display_line + ".worldInverseMatrix", mm1 + ".matrixIn[1]", f=True)
    cmds.connectAttr(point2 + ".worldMatrix", mm2 + ".matrixIn[0]", f=True)
    cmds.connectAttr(display_line + ".worldInverseMatrix", mm2 + ".matrixIn[1]", f=True)
    cmds.connectAttr(mm1 + ".matrixSum", dcmp1 + ".inputMatrix")
    cmds.connectAttr(mm2 + ".matrixSum", dcmp2 + ".inputMatrix")

    display_line_shape = cmds.listRelatives(display_line, s=True) or []
    cmds.connectAttr(
        dcmp1 + ".outputTranslate", display_line_shape[0] + ".controlPoints[0]", f=True
    )
    cmds.connectAttr(
        dcmp2 + ".outputTranslate", display_line_shape[0] + ".controlPoints[1]", f=True
    )
    return display_line


def create_curve_from_transform(
    transforms,
    degree=3,
    name="curve",
    transform_type="transform",
    form="Open",
    parent=None,
    edit_points=False,
):
    points = []
    for transform in transforms:
        transform = transform.name()
        points.append(
            cmds.xform(transform, q=True, ws=True, t=True)
        )

    if form == "Closed":
        pass

    if edit_points:
        return create_curve_from_ep(
            points,
            degree=degree,
            name=name,
            transform_type=transform_type,
            form=form,
            parent=parent,
        )

    return create_curve(
        points,
        degree=degree,
        name=name,
        transform_type=transform_type,
        form=form,
        parent=parent,
    )


def create_curve_from_ep(
    ep_list, degree=3, name="curve", transform_type="transform", form="Open", parent=None
):
    curve = create_curve(
        ep_list,
        degree=1,
        name=name,
        transform_type=transform_type,
        form=form,
        parent=parent,
    )

    fit_curve = cmds.fitBspline(curve, ch=0, tol=0.01)

    cmds.delete(curve)
    curve = cmds.rename(fit_curve[0], curve)
    cmds.parent(curve, parent)
    return curve


def create_curve(
    points, degree=3, name="curve", transform_type="transform", form="Open", parent=None
):
    knot_list = [0]
    if degree == 1:
        knot_list.extend(range(len(points))[1:])
    elif degree == 2:
        knot_list.extend(range(len(points) - 1))
        knot_list.append(knot_list[-1])
    elif degree == 3:
        knot_list.append(0)
        knot_list.extend(range(len(points) - 2))
        knot_list.extend([knot_list[-1], knot_list[-1]])

    if form not in ["Closed", "Periodic"]:
        curve = cmds.curve(name=name, p=points, k=knot_list, degree=degree)
    else:
        curve = cmds.circle(
            name=name,
            c=(0, 0, 0),
            nr=(0, 1, 0),
            sw=360,
            r=1,
            d=degree,
            ut=0,
            tol=0.01,
            s=len(points),
            ch=False,
        )[0]
        for i, position in enumerate(points):
            cmds.setAttr("{}.controlPoints[{}]".format(curve, i), *position)

    for shape in cmds.listRelatives(curve, c=True, type="shape"):
        if transform_type == "joint":
            trs_type_name = cmds.createNode("joint", name="{}_jnt".format(name))
            cmds.parent(shape, trs_type_name, r=True, shape=True)
            cmds.delete(curve)
            cmds.rename(trs_type_name, curve)
            cmds.setAttr("{}.drawStyle".format(curve), 2)
        cmds.rename(shape, "{}Shape".format(curve))
    if parent:
        cmds.parent(curve, parent)

    return curve


def smoothSkinCluster(polyMesh, intensity=0.5, itterations=30):
    """
    Try to import Ngskintools and smooth the skin cluster

    :param polyMesh: name of the poly mesh to smooth
    :param intensity: set the intensity of the smooth value
    :param itterations: number of times to run the smooth
    :return:
    """
    try:
        pluginLoaded = cmds.pluginInfo("ngSkinTools2", q=True, loaded=True)
        if not pluginLoaded:
            cmds.loadPlugin("ngSkinTools2")
        from ngSkinTools2 import api as ngst
    except:
        raise Warning(
            "Unable to load ngSkinTools2 python module. Cannot smooth mesh {}".format(
                polyMesh
            )
        )
    # we need a layer reference for this, so we'll take first layer from our sample mesh
    try:
        ngst.init_layers(polyMesh)
        layers = ngst.Layers(polyMesh)
    except:
        try:
            layers = ngst.Layers(polyMesh)
        except:
            om.MGlobal.displayWarning("Failed to initialize skinning layers")
    if not layers.list():
        layer = layers.add("base_weights")
    else:
        layer = layers.list()[0]

    # build settings for the flood
    
    settings = ngst.PaintModeSettings()

    # smoothing does not require current influence
    
    settings.mode = ngst.PaintMode.smooth
    settings.intensity = intensity
    settings.iterations = itterations
    
    
    ngst.flood_weights(target=layer, settings=settings)

    try:
        skinClusterNode = pm.ls( pm.listHistory( polyMesh ), type='skinCluster')[0]
        ngSkinNodes = cmds.listConnections(str(skinClusterNode), type="ngst2SkinLayerData")
        cmds.delete(ngSkinNodes)
    except:
        om.MGlobal.displayWarning("Failed to delete ngst2SkinLayerData")


def create(cage, bind_skin, ctl_size=1, smooth_iterations=2):
    create_deform_cage(
        cage, bind_skin, ctl_size=ctl_size, smooth_iterations=smooth_iterations
    )
