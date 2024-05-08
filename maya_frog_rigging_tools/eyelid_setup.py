from maya import cmds
from maya_frog_rigging_tools import omaya_utils

# followed tutorial by Marco Giordano

# create joints
for v in vtx:
    cmds.select(cl=1)
    jnt = cmds.joint(name=f"eye_l_upper_{v}bnd")
    pos = cmds.xform(v, q=1, ws=1, t=1)
    cmds.xform(jnt, ws=1, t=pos)
    center_position = cmds.xform(center, q=1, ws=1, t=1)
    cmds.select(cl=1)
    center_joint = cmds.joint(name=f"eye_l_upper_{v}center")
    cmds.xform(center_joint, ws=1, t=center_position)
    cmds.parent(jnt, center_joint)
    cmds.joint(center_joint, e=1, oj="xyz", secondaryAxisOrient="yup", ch=1, zso=1)

# select joint tips(bnd)and create aim constraints
sel = cmds.ls(sl=1)

for s in sel:
    loc = cmds.spaceLocator(name=f"{s}_loc")[0]
    pos = cmds.xform(s, q=1, ws=1, t=1)
    cmds.xform(loc, ws=1, t=pos)
    par = cmds.listRelatives(s, p=1)[0]
    cmds.aimConstraint(
        loc, par, mo=1, weight=1, aimVector=(1, 0, 0), upVector=(0, 1, 0), worldUpType="object",worldUpObject="eye_l_up"
    )

# create a cv curve connecting all top and bottom locs

sel = cmds.ls(sl=1)
crv = "eye_l_lower_curveShape"

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
