def get_mobject(name):
	sel = om2.MGlobal.getSelectionListByName(name)
	return sel.getDependNode(0)


def get_dag_path(name):
	sel = om2.MGlobal.getSelectionListByName(name)
	return sel.getDagPath(0)


def get_mfn_skin(skin_ob):
	if isinstance(skin_ob, pm.PyNode):
		skin_ob = get_mobject(skin_ob.longName())
	return oma2.MFnSkinCluster(skin_ob)


def get_mfn_mesh(mesh_ob):
	if isinstance(mesh_ob, pm.PyNode):
		mesh_ob = get_mobject(mesh_ob.longName())
	return om2.MFnMesh(mesh_ob)


def get_complete_components(mesh_ob):
	assert(isinstance(mesh_ob, om2.MFnMesh))
	comp = om2.MFnSingleIndexedComponent()
	ob = comp.create(om2.MFn.kMeshVertComponent)
	comp.setCompleteData(mesh_ob.numVertices)
	return(ob)
