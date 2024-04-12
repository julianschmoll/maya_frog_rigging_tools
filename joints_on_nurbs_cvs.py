import pymel.core as pm
"""help the joints are parented and they shouldnt be, and the name is very weird"""


def corner_joints(nurbs_surface):
    cv_array = nurbs_surface.cv
    for index, cv in enumerate(cv_array):
        pm.joint(n = f"{nurbs_surface.name}_jnt_{index}", a = True, p = pm.pointPosition(cv))
        print(cv)

corner_joints(pm.selected()[0])
    
