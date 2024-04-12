from pathlib import Path

from PySide2.QtWidgets import *
import shiboken2
import maya.OpenMayaUI as omui
import pymel.core as pc


def get_maya_win():
    ptr = omui.MQtUtil().mainWindow()
    return shiboken2.wrapInstance(int(ptr), QWidget)   


class ShaderSetup:
    def __init__(self, name, folder, selected):
        self.folder = Path(folder)
        self.name = name
        self.selected = selected

        self.material = pc.shadingNode('aiStandardSurface', asShader=1, name=self.name + '_ai')
        self.SG = pc.sets(renderable=1, noSurfaceShader=1, empty=1, name=self.name + '_sg')
        self.placeTwoD = pc.shadingNode('place2dTexture', asShader=1, name=self.name + '_p2d')

        self.material.outColor >> self.SG.surfaceShader


        self.file_map = {
            "BaseColor": {"out_channel": "outColor", "to_channel": "baseColor", "factory": self.file_factory},
            "Metallic": {"out_channel": "outColor.outColorR", "to_channel": "metalness", "factory": self.file_factory},
            "Roughness": {"out_channel": "outColor.outColorR", "to_channel": "specularRoughness", "factory": self.file_factory},
            "Emissive": {"out_channel": "outAlpha", "to_channel": "emission", "factory": self.file_factory},
            "Normal": {"out_channel": "outValue", "to_channel": "normalCamera", "factory": self.normal_factory}
        }

        for file in self.folder.glob("*.tif"):
            self.connect_nodes(str(file.stem))
            
        pc.select(self.selected)
        pc.hyperShade(assign = self.SG)

            
    def connect_nodes(self, filename):
        self.filename = filename
        parts = str(filename).split("_")
        self.key = parts[-2]
        self.color_space = parts[-1]
        channel_info = self.file_map.get(self.key)
        
        if channel_info:
            self.connect_node_to_material(**channel_info)
            
    def connect_node_to_material(self, out_channel, to_channel, factory):
        node = factory()
        node.attr(out_channel) >> self.material.attr(to_channel)
            
    def file_factory(self):
        file_node = pc.shadingNode('file', asShader=1, name=f"{self.name}_{self.key}_file")
        filePath = f"{self.folder}\{self.filename}.tif"
        file_node.fileTextureName.set(filePath)
        file_node.colorSpace.set(self.color_space)
        self.placeTwoD.outUV >> file_node.uvCoord
        return file_node
    
    def normal_factory(self):
        aiNormalMap = pc.shadingNode('aiNormalMap', asShader=1, name = f"{self.name}_aiNormalMap")
        file_node = self.file_factory()
        file_node.outColor >> aiNormalMap.input
        return aiNormalMap
    
    
            
class ShaderWin(QMainWindow):
    def __init__(self):
        super().__init__(parent=get_maya_win())
        self.folder = None
        self._create_widgets()
        self._connect_widgets()
        self._create_layout()
        self.show()

    def _create_widgets(self):
        self.dir_lineedit = QLineEdit()
        self.dir_lineedit.setEnabled(False)
        self.dir_lineedit.setText("Choose Texturing Folder")
        self.choose_btn = QPushButton("")
        pixmap = QStyle.SP_DirIcon
        icon = self.style().standardIcon(pixmap)
        self.choose_btn.setIcon(icon)
        self.ok_btn = QPushButton("Assign Shader")

    def _connect_widgets(self):
        self.ok_btn.clicked.connect(self.__assign_shader)
        self.choose_btn.clicked.connect(self._get_dir)

    def _create_layout(self):
        vbox = QVBoxLayout()
        dir_hbox = QHBoxLayout()
        dir_hbox.addWidget(self.dir_lineedit, stretch=1)
        dir_hbox.addWidget(self.choose_btn)
        vbox.addLayout(dir_hbox)

        res_hbox = QHBoxLayout()
        vbox.addLayout(res_hbox)

        vbox.addWidget(self.ok_btn)

        central_widget = QWidget()
        central_widget.setLayout(vbox)
        self.setCentralWidget(central_widget)

    def __assign_shader(self):
        folder = self.dir_lineedit.text()
        if self.folder and Path(self.folder).exists():
            print(self.folder)
            asset_name = str(pc.sceneName().name).split("_")[0]
            sel = pc.selected()
            if not sel:
                return
            sel_name = sel[0]
            shader_name = f"{asset_name}_{sel_name}"
            print(shader_name)
            ShaderSetup(shader_name, self.folder, sel_name)
            self.close()
        else:
            pc.warning("Please select an existing folder.")

    def _get_dir(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Choose Directory",
            str(pc.Workspace().path),
            QFileDialog.ShowDirsOnly
        )
        self.dir_lineedit.setText(folder)
        self.folder = folder