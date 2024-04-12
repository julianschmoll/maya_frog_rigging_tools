from pymel import core as pm
import maya.cmds as cmds
from functools import partial
from maya.api import OpenMaya as om2

from maya_frog_rigging_tools import deformation_cage

class CreateUI():
    def __init__(self):
        windowID = "myWindowID"

        if cmds.window(windowID, exists=True):
            cmds.deleteUI(windowID)

        masterWindow = cmds.window(windowID, title="Deform Cage", w=390, h=225, sizeable=False, resizeToFitChildren=False)
        cmds.rowColumnLayout(parent=masterWindow, numberOfColumns=1)       
      
        def apply_close(*args):
            try:
                apply()
            except:
                om2.MGlobal.displayError("Failed to create Deform Cage")
            close()

        def apply(*args):
            cage_obj = cmds.textField("cage_obj", query=True, text=True)
            bind_nodes = cmds.textField("bind_nodes", query=True, text=True).split(',')
            ctl_size = cmds.intSliderGrp("ctl_size", query=True, v=True)
            smooth_iter = cmds.intSliderGrp("smooth_iter", query=True, v=True)
            deformation_cage.create(
                cage_obj, bind_nodes, ctl_size=ctl_size, smooth_iterations=smooth_iter
            )

        def close(*args):
            cmds.deleteUI(windowID)
  
        cmds.separator(h=20, style="none")           
        cmds.columnLayout()
        cmds.rowLayout(numberOfColumns=2, width=500)
        cmds.text(label="Cage Object: ",  align='right', width=100)
        try:
            cage = pm.ls(sl=True)[0]
            nodes = [node.name() for node in pm.ls(sl=True)[1:]]
        except IndexError:
            cage = ""
            nodes = ""

        self.cage_obj = cmds.textField("cage_obj", width=240, text=f"{cage}")
        cmds.setParent("..")
        cmds.separator(h=20, style="none")
        
        self.ctl_size = cmds.intSliderGrp("ctl_size",label="Control Size: ", field=True, min=1, max=100, value=2, width=350)  
        self.smooth_iter = cmds.intSliderGrp("smooth_iter",label="Smoothing Iterations ", field=True, min=1, max=10, value=2, width=350)
        cmds.separator(h=20, style="none")
         
        cmds.columnLayout()
        cmds.rowLayout(numberOfColumns=2, width=500)
        cmds.text(label="Bind Objects: ",  align='right', width=100)
        nodes_str = str(nodes).replace("[", "").replace("]", "").replace("'", "")
        self.bind_nodes = cmds.textField("bind_nodes", width=240, text=f"{nodes_str}")
        cmds.setParent("..")

        cmds.separator(h=20, style="none")            
        cmds.columnLayout()
        cmds.rowLayout(numberOfColumns=3, width=500)
        cmds.button(label="Apply and Close", command=apply_close, width=125, height=28)
        cmds.button(label="Apply", command=apply, width=125, height=28)
        cmds.button(label="Close", command=close, width=125, height=28)
        cmds.setParent("..")

        cmds.showWindow(windowID)

def show():
    ui=CreateUI()   
    