
bl_info = {
    "name"    : "Ghost Mesh",
    "author"  : "shikage34",
    "version" : (0, 2, 0),
    "blender" : (4, 0, 0),
    "category": "3D View"
}


if "bpy" in locals():
    import importlib
    importlib.reload(gm_panel)
    importlib.reload(gm_draw)
else:
    import bpy
    from . import gm_panel
    from . import gm_draw


def register():
    gm_panel.register()
    gm_draw.register()


def unregister():
    gm_panel.unregister()
    gm_draw.unregister()

if __name__ == "__main__":
    register()

