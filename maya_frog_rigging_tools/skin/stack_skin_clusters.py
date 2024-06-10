
from maya.api import OpenMaya as om2
from pymel import core as pm

from maya_frog_rigging_tools.omaya_utils import get_dag_path, get_mfn_skin, get_mfn_mesh, get_complete_components
from maya_frog_rigging_tools.skin.skin_utils import get_deform_shape, get_skin_cluster


def log(msg, warn=False, error=False):
	if error:
		log_func = om2.MGlobal.displayError
	elif warn:
		log_func = om2.MGlobal.displayWarning
	else:
		log_func = om2.MGlobal.displayInfo
	log_func(msg)


def move_skin(source, target):
	source_shape = get_deform_shape(source)
	source_dp = get_dag_path(source_shape.longName())
	source_skin = get_skin_cluster(source)
	source_mfn = get_mfn_skin(source_skin)
	source_mesh = get_mfn_mesh(get_deform_shape(source))
	components = get_complete_components(source_mesh)

	weights, influence_count = source_mfn.getWeights(source_dp, components)

	pm.select(cl=True)
	target_skin = pm.deformer(target, type='skinCluster', n='stacked_' + source_skin.name())[0]

	bind_inputs = [(x.inputs(plugs=True)[0] if x.isConnected() else None) for x in source_skin.bindPreMatrix]
	bind_values = [x.get() for x in source_skin.bindPreMatrix]
	mat_inputs = [(x.inputs(plugs=True)[0] if x.isConnected() else None) for x in source_skin.matrix]
	mat_values = [x.get() for x in source_skin.matrix]

	for index, bind_value, mat_value in zip(range(influence_count), bind_values, mat_values):
		target_skin.bindPreMatrix[index].set(bind_value)
		target_skin.matrix[index].set(mat_value)

	for index, bind_input, mat_input in zip(range(influence_count), bind_inputs, mat_inputs):
		if bind_input:
			bind_input >> target_skin.bindPreMatrix[index]
		if mat_input:
			mat_input >> target_skin.matrix[index]

	target_mfn = get_mfn_skin(target_skin)
	target_mesh = get_mfn_mesh(get_deform_shape(target))
	target_dp = get_dag_path(get_deform_shape(target).longName())
	components = get_complete_components(target_mesh)
	all_indices = om2.MIntArray(range(influence_count))
	
	target_mfn.setWeights(target_dp, components, all_indices, weights)


def stack_skin_clusters():
	items = pm.selected()
	if len(items) == 2:
		move_skin(items[0], items[1])
		log(f"Merged skin from {items[0]} onto {items[1]}.")
	else:
		log("Please select a skinned mesh and a target mesh.", error=True)
