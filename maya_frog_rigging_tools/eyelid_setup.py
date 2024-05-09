from maya import cmds
from pymel import core as pm
from maya_frog_rigging_tools import omaya_utils

# followed tutorial by Marco Giordano
vtx = cmds.ls(sl=10, fl=1)
prefix = "eye_l_lower"
center = pm.PyNode("head_bnd|eye_l_bnd").fullPath()


# create joints
for i, v in enumerate(vtx):
    cmds.select(cl=1)
    jnt = cmds.joint(name=f"{prefix}_{i}_bnd")
    pos = cmds.xform(v, q=1, ws=1, t=1)
    cmds.xform(jnt, ws=1, t=pos)
    center_position = cmds.xform(center, q=1, ws=1, t=1)
    cmds.select(cl=1)
    center_joint = cmds.joint(name=f"{prefix}_{i}_center")
    cmds.xform(center_joint, ws=1, t=center_position)
    cmds.parent(jnt, center_joint)
    cmds.joint(center_joint, e=1, oj="xyz", secondaryAxisOrient="yup", ch=1, zso=1)

# select joint tips(bnd)and create aim constraints
# create up vectors as well (locators above eyes)
sel = cmds.ls(sl=1)
up = "eye_r_up"

for s in sel:
    loc = cmds.spaceLocator(name=f"{s}_loc")[0]
    pos = cmds.xform(s, q=1, ws=1, t=1)
    cmds.xform(loc, ws=1, t=pos)
    par = cmds.listRelatives(s, p=1)[0]
    cmds.aimConstraint(
        loc, par, mo=1, weight=1, aimVector=(1, 0, 0), upVector=(0, 1, 0), worldUpType="object",worldUpObject=up
    )

# create a cv curve (linear) connecting all top or bottom locs
# with the following function, locators will follow curve
# selection has to be locators
sel = cmds.ls(sl=1)
crv = "eye_r_lower_aim_curveShape"

for s in sel:
    pos = cmds.xform(s, q=1, ws=1, t=1)
    u_parm = omaya_utils.get_u_param(pos, crv)
    name = s.replace("_loc", "_pci")
    pci = cmds.createNode("pointOnCurveInfo", name=name)
    cmds.connectAttr(f"{crv}.worldSpace", f"{pci}.inputCurve")
    cmds.setAttr(f"{pci}.parameter", u_parm)
    cmds.connectAttr(f"{pci}.position", f"{s}.t")

# create cubic curve with less cv points (5 for example, 1 in corners, 1 at top, 1 in middle)
# modify that one to make it fit to higher resolution curve
# name low
# add wire deformer
# create controls, bigger ones in mid and corner, smol ones in middle
# controls should be around cv of control curve, rename appropriately
# change colors accordingly
# we need attribute somewhere to to show or hide secondary ctl
# connect visibility with attrq
# add joints for cvs (ctls) since they will be driving the curve
# skin lowres curve with joints, default skinning should work
# constrain bone to control (point constraint)
# keep secondary average by selecting middle, corner and group of secondary, parent with 0.5 weights so they follow

### usage
# name_prefix = "eye_l"
# center = pm.PyNode("head_bnd|eye_l_bnd").fullPath()
# vtx = cmds.ls(sl=1, fl=1)
