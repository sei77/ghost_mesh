
bl_info = {
    "name"    : "Ghost Mesh",
    "author"  : "sei77",
    "version" : (1, 0, 3),
    "blender" : (4, 0, 0),
    "category": "3D View"
}

if "bpy" in locals():
    import importlib
    importlib.reload(gm_panel)
    importlib.reload(gm_draw)
    importlib.reload(gm_dict)
else:
    import bpy
    from . import gm_panel
    from . import gm_draw
    from . import gm_dict

# 登録処理
def register():
    gm_panel.register()
    gm_draw.register()
    bpy.app.translations.register(__name__, gm_dict.translation_dict)

# 登録解除処理
def unregister():
    bpy.app.translations.unregister(__name__, gm_dict.translation_dict)
    gm_draw.unregister()
    gm_panel.unregister()
    
if __name__ == "__main__":
    register()

