import pymel.core as pm

sel = pm.selected()

for index, jnt in enumerate(sel):
    pm.joint(sel[index] , rad = 3)
    