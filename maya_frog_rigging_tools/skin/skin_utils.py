def get_deform_shape(ob):
	ob = pm.PyNode(ob)
	if ob.type() in ['nurbsSurface', 'mesh', 'nurbsCurve']:
		ob = ob.getParent()
	shapes = pm.PyNode(ob).getShapes()
	if len(shapes) == 1:
		return(shapes[0])
	else:
		real_shapes = [ x for x in shapes if not x.intermediateObject.get() ]
		return(real_shapes[0] if len(real_shapes) else None)


def get_skin_cluster(ob):
	shape = get_deform_shape(ob)
	if shape is None:
		return(None)
	skins = pm.ls(pm.listHistory(shape), type='skinCluster')
	return(skins[0])
