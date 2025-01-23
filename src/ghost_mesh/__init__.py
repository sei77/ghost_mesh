
bl_info = {
    "name"    : "Ghost Mesh",
    "author"  : "sei77",
    "version" : (1, 1, 0),
    "blender" : (4, 0, 0),
    "category": "3D View"
}

import bpy
from bpy.app.handlers import persistent
from . import gm_prop
from . import gm_panel
from . import gm_draw
from . import gm_dict

# 登録処理
def register():
    gm_prop.register()
    gm_panel.register()
    gm_draw.register()
    bpy.app.translations.register(__name__, gm_dict.translation_dict)

# 解除処理
def unregister():
    bpy.app.translations.unregister(__name__)
    gm_draw.unregister()
    gm_panel.unregister()
    gm_prop.unregister()

if __name__ == "__main__":
    register()

