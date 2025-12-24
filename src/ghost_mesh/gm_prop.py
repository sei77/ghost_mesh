import bpy
import bmesh
from bpy.app.handlers import persistent
from bpy.types import Panel, UIList, Operator, PropertyGroup, Object
from bpy.props import IntProperty, FloatProperty, FloatVectorProperty, BoolProperty, CollectionProperty, StringProperty, PointerProperty


# メッシュオブジェクトアイテム
class MeshObjectItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="name")
    object_ref: bpy.props.PointerProperty(type=bpy.types.Object)

def update_mesh_object_list(scn):
    """シーン内の全メッシュオブジェクトをUIリストに同期する"""
    # 既存のリストをクリア
    scn.mesh_objects.clear()
    
    # メッシュオブジェクトのみを抽出して登録
    for obj in scn.objects:
        if obj.type == 'MESH':
            item = scn.mesh_objects.add()
            item.name = obj.name
            item.object_ref = obj

# ゴースト表示用の Bool プロパティが変更された際に呼ばれるコールバック
# - gm_draw.invalidate_all_caches を呼んで全キャッシュを無効化し、View3D を再描画する
def _on_ghost_prop_update(self, context):
    from . import gm_draw
    gm_draw.invalidate_all_caches()
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()

# プロパティの初期化
def init_props():
    
    # 編集モード用
    bpy.types.Scene.edit_ghost_display_edge = BoolProperty(
        name=bpy.app.translations.pgettext("Edit Ghosting Display(Edge)"),
        description=bpy.app.translations.pgettext("Display hidden edges as translucent"),
        default=True,
        update=_on_ghost_prop_update)
    bpy.types.Scene.edit_ghost_display_face = BoolProperty(
        name=bpy.app.translations.pgettext("Edit Ghosting Display(Face)"),
        description=bpy.app.translations.pgettext("Display hidden faces as translucent"),
        default=True,
        update=_on_ghost_prop_update)
    bpy.types.Scene.edit_ghost_edge_color = FloatVectorProperty(
        name=bpy.app.translations.pgettext("Edit Edge color"),
        description=bpy.app.translations.pgettext("Hidden edge color"),
        subtype='COLOR', default=[0.0, 1.0, 0.0, 0.1], size=4, min=0.0, max=1.0)
    bpy.types.Scene.edit_ghost_face_color = FloatVectorProperty(
        name=bpy.app.translations.pgettext("Edit Face color"),
        description=bpy.app.translations.pgettext("Hidden surface color"),
        subtype='COLOR', default=[0.0, 0.8, 0.0, 0.1], size=4, min=0.0, max=1.0)
    
    # オブジェクトモード用
    bpy.types.Scene.object_ghost_display_edge = BoolProperty(
        name=bpy.app.translations.pgettext("Object Ghosting Display(Edge)"),
        description=bpy.app.translations.pgettext("Display hidden edges as translucent"),
        default=False,
        update=_on_ghost_prop_update)
    bpy.types.Scene.object_ghost_display_face = BoolProperty(
        name=bpy.app.translations.pgettext("Object Ghosting Display(Face)"),
        description=bpy.app.translations.pgettext("Display hidden faces as translucent"),
        default=False,
        update=_on_ghost_prop_update)
    bpy.types.Scene.object_ghost_edge_color = FloatVectorProperty(
        name=bpy.app.translations.pgettext("Object Edge color"),
        description=bpy.app.translations.pgettext("Hidden edge color"),
        subtype='COLOR', default=[0.8, 0.8, 0.0, 0.1], size=4, min=0.0, max=1.0)
    bpy.types.Scene.object_ghost_face_color = FloatVectorProperty(
        name=bpy.app.translations.pgettext("Object Face color"),
        description=bpy.app.translations.pgettext("Hidden surface color"),
        subtype='COLOR', default=[0.5, 0.5, 0.0, 0.1], size=4, min=0.0, max=1.0)
    bpy.types.Scene.mesh_objects = bpy.props.CollectionProperty(type=MeshObjectItem)
    bpy.types.Scene.mesh_objects_index = bpy.props.IntProperty(name="Object index", default=0)
    # 描画用
    bpy.types.Scene.ghost_line_size = FloatProperty(
        name=bpy.app.translations.pgettext("Line size"),
        description=bpy.app.translations.pgettext("Line size"),
        default=2.0, min=1.0, max=5.0)
    
    # 半透明/非表示用
    bpy.types.Material.ghost_visible = bpy.props.BoolProperty(default=True)
    bpy.types.Material.ghost_hide = bpy.props.BoolProperty(default=False)
    bpy.types.Object.ghost_hide = bpy.props.BoolProperty(default=False)


# プロパティのクリア
def clear_props():
    del bpy.types.Object.ghost_hide
    del bpy.types.Material.ghost_visible
    del bpy.types.Material.ghost_hide
    del bpy.types.Scene.ghost_line_size
    del bpy.types.Scene.mesh_objects_index
    del bpy.types.Scene.mesh_objects
    del bpy.types.Scene.object_ghost_face_color
    del bpy.types.Scene.object_ghost_edge_color
    del bpy.types.Scene.object_ghost_display_face
    del bpy.types.Scene.object_ghost_display_edge
    del bpy.types.Scene.edit_ghost_face_color
    del bpy.types.Scene.edit_ghost_edge_color
    del bpy.types.Scene.edit_ghost_display_face
    del bpy.types.Scene.edit_ghost_display_edge


# 登録処理
def register():
    bpy.utils.register_class(MeshObjectItem)
    init_props()


# 解除処理
def unregister():
    bpy.utils.unregister_class(MeshObjectItem)
    clear_props()

