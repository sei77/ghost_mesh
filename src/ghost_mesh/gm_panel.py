import bpy
import bmesh
from bpy.types import Panel, UIList, Operator, PropertyGroup, Object
from bpy.props import IntProperty, FloatProperty, FloatVectorProperty, BoolProperty, CollectionProperty, StringProperty, PointerProperty
from . import gm_draw

# VIEW3D の全エリアを再描画して UI を最新状態に更新するヘルパー関数
def tag_redraw_all_view3d():
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()

# 指定されたオブジェクト名の描画キャッシュを無効化し、次回描画時に再生成させる
def set_cache_dirty(obj_name):
    if obj_name in gm_draw._draw_objects:
        gm_draw._draw_objects[obj_name].is_cache = False

# 共通: オブジェクト一覧と表示設定セクションを描画するヘルパー
# - Object モードと Edit パネルで共通して使用される UI ブロックをまとめる
def _draw_shared_object_section(layout, scn, rows=5):
    """Draw the shared object list and object-level ghost settings."""
    row = layout.row()
    row.template_list("GM_UL_ObjectItems", "object_list", scn, "mesh_objects", scn, "mesh_objects_index", rows=rows)

    layout.prop(scn, "object_ghost_display_edge"  , text="Object Ghosting Display(Edge)")
    layout.prop(scn, "object_ghost_display_face"  , text="Object Ghosting Display(Face)")
    layout.prop(scn, "object_ghost_edge_color", text="Object Edge color")
    layout.prop(scn, "object_ghost_face_color", text="Object Face color")

# オブジェクト一覧 UIList
# - 各オブジェクトの名前と表示/ゴースト切替ボタンを描画する
class GM_UL_ObjectItems(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        obj = item.object_ref
        if obj:
            row = layout.row(align=True)
            row.label(text=obj.name)
            
            icon_dp = "HIDE_ON" if obj.hide_get() else "HIDE_OFF"
            op_dp = row.operator(GM_OT_GhostObjectDisplayToggle.bl_idname, text="", icon=icon_dp)
            op_dp.target_name = obj.name
            
            icon_tr = "GHOST_ENABLED" if not obj.ghost_hide else "GHOST_DISABLED"
            op_tr = row.operator(GM_OT_GhostObjectTranslucentToggle.bl_idname, text="", icon=icon_tr)
            op_tr.target_name = obj.name
        else:
            layout.label(text="Missing Object")

# オブジェクトの表示/非表示を切り替えるオペレータ
# - 指定オブジェクトの hide_set をトグルし、キャッシュとビューを更新する
class GM_OT_GhostObjectDisplayToggle(bpy.types.Operator):
    bl_idname = "object.ghost_object_display_toggle"
    bl_label = bpy.app.translations.pgettext("Mesh display/hide")
    bl_description = bpy.app.translations.pgettext("Hide all meshes except those to which materials are assigned")
    bl_options = {'REGISTER', 'UNDO'}
    target_name: StringProperty()
    
    def execute(self, context):
        obj = context.scene.objects.get(self.target_name)
        if obj:
            obj.hide_set(not obj.hide_get())
            set_cache_dirty(obj.name)
            tag_redraw_all_view3d()
        return {'FINISHED'}

# オブジェクトのゴースト（半透明）表示フラグを切り替えるオペレータ
class GM_OT_GhostObjectTranslucentToggle(bpy.types.Operator):
    bl_idname = "object.ghost_object_translucent_toggle"
    bl_label = bpy.app.translations.pgettext("Mesh display/hide")
    bl_description = bpy.app.translations.pgettext("Hide all meshes except those to which materials are assigned")
    bl_options = {'REGISTER', 'UNDO'}
    target_name: StringProperty()
     
    def execute(self, context):
        obj = context.scene.objects.get(self.target_name)
        if obj:
            obj.ghost_hide = not obj.ghost_hide
            set_cache_dirty(obj.name)
            tag_redraw_all_view3d()
        return {'FINISHED'}

# オブジェクトモード用 UI パネル
# - オブジェクト一覧とオブジェクト単位のゴースト表示設定を提供する
class GM_PT_ObjectModePanel(bpy.types.Panel):
    bl_label = bpy.app.translations.pgettext("Drawing Settings")
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = bpy.app.translations.pgettext("Ghost")
    bl_context = "objectmode"
    
    def draw(self, context):
        layout = self.layout
        scn = context.scene

        _draw_shared_object_section(layout, scn, rows=5)

# マテリアル一覧 UIList
# - マテリアルごとの表示/ゴースト切替を行う UI を提供する
class GM_UL_MaterialItems(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        mat = item.material
        if mat:
            row = layout.row(align=True)
            row.label(text=mat.name)
            
            icon_dp = "HIDE_OFF" if getattr(mat, "ghost_visible", True) else "HIDE_ON"
            op_dp = row.operator(GM_OT_GhostMeshDisplayToggle.bl_idname, text="", icon=icon_dp)
            op_dp.selected = index
            
            icon_tr = "GHOST_ENABLED" if not getattr(mat, "ghost_hide", True) else "GHOST_DISABLED"
            op_tr = row.operator(GM_OT_GhostMeshTranslucentToggle.bl_idname, text="", icon=icon_tr)
            op_tr.selected = index
        else:
            layout.label(text="Missing Material")

# 編集モード内でマテリアル別に表示/非表示を切り替えるオペレータ
# - 編集モードの場合は BMesh を、オブジェクトモードの場合は一時 BMesh を用いてメッシュを更新する
class GM_OT_GhostMeshDisplayToggle(bpy.types.Operator):
    bl_idname = "object.ghost_mesh_display_toggle"
    bl_label = bpy.app.translations.pgettext("Mesh display/hide")
    bl_description = bpy.app.translations.pgettext("Hide all meshes except those to which materials are assigned")
    bl_options = {'REGISTER', 'UNDO'}
    
    selected : IntProperty()
    
    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH': return {'CANCELLED'}
        
        is_edit = (obj.mode == 'EDIT')
        bm = bmesh.from_edit_mesh(obj.data) if is_edit else bmesh.new()
        if not is_edit: bm.from_mesh(obj.data)

        if self.selected == -1: # Show All
            for f in bm.faces: f.hide = False
            for v in bm.verts: v.hide = False
            for e in bm.edges: e.hide = False
            for mat_slot in obj.material_slots:
                setattr(mat_slot.material, "ghost_visible", True)
        else:
            mat = obj.material_slots[self.selected].material
            material_index = self.selected
            if mat:
                mat.ghost_visible = not getattr(mat, "ghost_visible", True)
                
                bm.verts.ensure_lookup_table()
                bm.edges.ensure_lookup_table()
                bm.faces.ensure_lookup_table()
                for v in bm.verts:
                    v.hide = True
                for e in bm.edges:
                    e.hide = False
                if getattr(mat, "ghost_visible", False):
                    for f in bm.faces:
                        if f.material_index == material_index or f.hide == False:
                            f.hide = False
                            for v in f.verts: v.hide = False
                else:
                    for f in bm.faces:
                        if f.material_index == material_index:
                            f.hide = True
                        elif not f.hide:
                            for v in f.verts: v.hide = False
                for e in bm.edges:
                    if e.verts[0].hide or e.verts[1].hide:
                        e.hide = True
        if is_edit:
            bmesh.update_edit_mesh(obj.data)
        else:
            bm.to_mesh(obj.data)
            bm.free()

        set_cache_dirty(obj.name)
        tag_redraw_all_view3d()
        return {'FINISHED'}

# マテリアル単位でゴースト（半透明）表示を切り替えるオペレータ
# - アクティブオブジェクトのマテリアルスロットを参照し、`ghost_hide` を切り替える
class GM_OT_GhostMeshTranslucentToggle(bpy.types.Operator):
    bl_idname = "object.ghost_mesh_translucent_toggle"
    bl_label = bpy.app.translations.pgettext("Display switching")
    bl_description = bpy.app.translations.pgettext("Show/hide material")
    bl_options = {'REGISTER', 'UNDO'}
    
    selected : IntProperty()
    
    def execute(self, context):
        if context.area.type == 'VIEW_3D':
            obj = context.active_object
            if obj is None or obj.type != 'MESH' or obj.hide_get():
                return {'CANCELLED'}
            mat = obj.material_slots[self.selected].material
            mat.ghost_hide = True if not mat.ghost_hide else False
            set_cache_dirty(obj.name)
            tag_redraw_all_view3d()
            return {'FINISHED'}
        else:
            return {'CANCELLED'}

# 編集モード用 UI パネル
# - 編集時のマテリアル選択、及びエッジ/面のゴースト表示設定を表示する
class GM_PT_EditModePanel(bpy.types.Panel):
    bl_label = bpy.app.translations.pgettext("Drawing Settings")
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = bpy.app.translations.pgettext("Ghost")
    bl_context = "mesh_edit"
    
    def draw(self, context):
        
        layout = self.layout
        scn = context.scene
        obj = context.active_object
        if not obj is None and obj.type == 'MESH' and not obj.hide_get():
            row = layout.operator(GM_OT_GhostMeshDisplayToggle.bl_idname, text='Show All')
            row.selected = -1
            
            row = layout.row()
            row.template_list("GM_UL_MaterialItems", "material_list", obj, "material_slots", obj, "active_material_index", rows=6)
            
            layout.prop(scn, "edit_ghost_display_edge"  , text="Edit Ghosting Display(Edge)")
            layout.prop(scn, "edit_ghost_display_face"  , text="Edit Ghosting Display(Face)")
            layout.prop(scn, "edit_ghost_edge_color", text="Edit Edge color")
            layout.prop(scn, "edit_ghost_face_color", text="Edit Face color")
            
            layout.separator()
        
        _draw_shared_object_section(layout, scn, rows=6)

# 登録対象クラス
CLASSES = (
    GM_PT_ObjectModePanel,
    GM_PT_EditModePanel,
    GM_OT_GhostMeshDisplayToggle,
    GM_OT_GhostMeshTranslucentToggle,
    GM_OT_GhostObjectDisplayToggle,
    GM_OT_GhostObjectTranslucentToggle,
    GM_UL_MaterialItems,
    GM_UL_ObjectItems,
)

# 登録処理
def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)

# 解除処理
def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
