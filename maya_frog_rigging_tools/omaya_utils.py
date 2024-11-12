import maya.OpenMaya as om
from maya.api import OpenMaya as om2
from maya.api import OpenMayaAnim as oma2
import pymel.core as pm


def get_mobject(name):
	sel = om2.MGlobal.getSelectionListByName(name)
	return sel.getDependNode(0)


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


def get_verts(mesh_name):
	vertices = []
	mesh_path = om.MDagPath()
	mesh_selection = om.MSelectionList()
	mesh_selection.add(mesh_name)
	mesh_selection.getDagPath(0, mesh_path)

	vertex_i = om.MItMeshVertex(mesh_path)
	while not vertex_i.isDone():
		vertices.append(mesh_name + '.vtx[' + str(vertex_i.index()) + ']')
		next(vertex_i)
	return vertices

def get_u_param(pnt = [], crv = None):
	point = om.MPoint(pnt[0],pnt[1],pnt[2])
	curve_fn = om.MFnNurbsCurve(get_dag_path(crv))
	param_util=om.MScriptUtil()
	param_ptr=param_util.asDoublePtr()
	is_on_curve = curve_fn.isPointOnCurve(point)
	if is_on_curve:
		curve_fn.getParamAtPoint(point , param_ptr,0.001,om.MSpace.kObject )
	else:
		point = curve_fn.closestPoint(point,param_ptr,0.001,om.MSpace.kObject)
		curve_fn.getParamAtPoint(point , param_ptr,0.001,om.MSpace.kObject )
	param = param_util.getDouble(param_ptr)
	return param

def get_dag_path(object_name):
	if isinstance(object_name, list):
		o_node_list=[]

		for o in object_name:
			selection_list = om.MSelectionList()
			selection_list.add(o)
			o_node = om.MDagPath()
			selection_list.getDagPath(0, o_node)
			o_node_list.append(o_node)
		return o_node_list

	else:
		selection_list = om.MSelectionList()
		selection_list.add(object_name)
		o_node = om.MDagPath()
		selection_list.getDagPath(0, o_node)

		return o_node
