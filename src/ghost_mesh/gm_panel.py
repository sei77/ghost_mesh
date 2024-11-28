import bpy
import bmesh
from bpy.types import Panel, UIList, Operator
from bpy.props import IntProperty, FloatProperty, FloatVectorProperty, BoolProperty
from . import gm_draw

# すべての頂点、辺、面を表示
def show_all(act_obj):
    
    if act_obj is None or act_obj.type != 'MESH':
        return
    
    old_mode = act_obj.mode
    bpy.ops.object.mode_set(mode="OBJECT")
    
    mesh = act_obj.data
    
    for vert in mesh.vertices:
        vert.hide = False
    for edge in mesh.edges:
        edge.hide = False
    for face in mesh.polygons:
        face.hide = False
    
    mesh.update()
    
    bpy.ops.object.mode_set(mode=old_mode)


# 表示マテリアル以外のメッシュ非表示
def ghost_mesh(event, act_obj, mat_index, mat_hide):
    
    if act_obj is None or act_obj.type != 'MESH':
        return
    
    old_mode = act_obj.mode
    bpy.ops.object.mode_set(mode="OBJECT")
    
    mesh = act_obj.data
    
    # 頂点はすべて非表示、辺はすべて表示
    for vert in mesh.vertices:
        vert.hide = True
    for edge in mesh.edges:
        edge.hide = False
    
    # 現状を維持して対象を表示する
    if mat_hide == 0:
        for face in mesh.polygons:
            if face.material_index == mat_index or face.hide == False:
                face.hide = False
                for v in face.vertices:
                    mesh.vertices[v].hide = False
        act_obj.material_slots[mat_index].material.ghost_hide = False
    # 現状を維持して対象を非表示にする
    else:
        for face in mesh.polygons:
            if face.material_index == mat_index:
                face.hide = True
            elif face.hide == False:
                for v in face.vertices:
                    mesh.vertices[v].hide = False
        act_obj.material_slots[mat_index].material.ghost_hide = True
    
    # いずれかの頂点が非表示だった場合は辺を隠す
    for edge in mesh.edges:
        v1 = mesh.vertices[edge.vertices[0]]
        v2 = mesh.vertices[edge.vertices[1]]
        
        if v1.hide or v2.hide:
            edge.hide = True
    
    mesh.update()
    
    bpy.ops.object.mode_set(mode=old_mode)


# メッシュ表示オペレータ
class GM_OT_GhostMesh(bpy.types.Operator):
    
    bl_idname = "object.ghost_mesh"
    bl_label = bpy.app.translations.pgettext("Mesh display/hide")
    bl_description = bpy.app.translations.pgettext("Hide all meshes except those to which materials are assigned")
    bl_options = {'REGISTER', 'UNDO'}
    
    mat_index : IntProperty()
    mat_hide  : IntProperty()
    
    def invoke(self, context, event):
        if context.area.type == 'VIEW_3D':
            if self.mat_index == -1:
                show_all(bpy.context.object)
            else:
                ghost_mesh(event, bpy.context.object, self.mat_index, self.mat_hide)
            context.area.tag_redraw()
            
            return {'FINISHED'}
        else:
            return {'CANCELLED'}


# メッシュ非表示オペレータ
class GM_OT_GhostMeshDisplay(bpy.types.Operator):
    
    bl_idname = "object.ghost_mesh_display"
    bl_label = bpy.app.translations.pgettext("Display switching")
    bl_description = bpy.app.translations.pgettext("Show/hide material")
    bl_options = {'REGISTER', 'UNDO'}
    
    mat_index : IntProperty()
    
    def invoke(self, context, event):
        if context.area.type == 'VIEW_3D':
            if context.active_object and context.active_object.type == 'MESH':
                mat = context.active_object.material_slots[self.mat_index].material
                mat.ghost = False if mat.ghost else True
                
                context.area.tag_redraw()
            
            return {'FINISHED'}
        else:
            return {'CANCELLED'}


# パネル登録
class GM_PT_SelectMaterial(bpy.types.Panel):

    bl_label = bpy.app.translations.pgettext("Display Material Selection")
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = bpy.app.translations.pgettext("Ghost")
    bl_context = "mesh_edit"
    
    def draw(self, context):
        
        layout = self.layout
        scn = bpy.context.scene
        
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            return
        
        row = layout.operator(GM_OT_GhostMesh.bl_idname,text='Show All', icon='SHADING_RENDERED')
        row.mat_index = -1
        
        row = layout.row()
        row.template_list("GM_UL_Items", "", obj, "material_slots", obj, "active_material_index", rows=8)
        
        layout.prop(scn, "ghost_display1"  , text=bpy.app.translations.pgettext("Ghosting Display1"))
        layout.prop(scn, "ghost_display2"  , text=bpy.app.translations.pgettext("Ghosting Display2"))
        layout.prop(scn, "ghost_edge_color", text=bpy.app.translations.pgettext("Edge color"))
        layout.prop(scn, "ghost_face_color", text=bpy.app.translations.pgettext("Face color"))
        
        gm_draw.GM_OT_CustomDraw.init_draw()

# 表示マテリアルのリスト項目
class GM_UL_Items(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        
        if not hasattr(item.material, 'ghost_hide'):
            return
        
        row = layout.row(align=False)
        row.label(text=item.material.name)
        row = layout.row(align=True)
        
        if item.material.ghost_hide:
            op2 = row.operator(GM_OT_GhostMesh.bl_idname, text='', icon='HIDE_ON')
            op2.mat_hide  = 0
            op2.mat_index = index
        else:
            op2 = row.operator(GM_OT_GhostMesh.bl_idname, text='', icon='HIDE_OFF')
            op2.mat_hide  = 1
            op2.mat_index = index
        op2 = row.operator(GM_OT_GhostMeshDisplay.bl_idname, text='', icon='GHOST_ENABLED' if item.material.ghost else 'GHOST_DISABLED')
        op2.mat_index = index
    
    def invoke(self, context, event):
        pass   

# プロパティの初期化
def init_props():
    bpy.types.Scene.ghost_display1 = BoolProperty(
        name=bpy.app.translations.pgettext("Ghosting Display1"),
        description=bpy.app.translations.pgettext("Display hidden edges as translucent"),
        default=True)
    bpy.types.Scene.ghost_display2 = BoolProperty(
        name=bpy.app.translations.pgettext("Ghosting Display2"),
        description=bpy.app.translations.pgettext("Display hidden faces as translucent"),
        default=True)
    bpy.types.Scene.ghost_edge_color = FloatVectorProperty(
        name=bpy.app.translations.pgettext("Edge color"),
        description=bpy.app.translations.pgettext("Hidden edge color"),
        subtype='COLOR', default=[0.0, 1.0, 0.0, 0.1], size=4, min=0.0, max=1.0)
    bpy.types.Scene.ghost_face_color = FloatVectorProperty(
        name=bpy.app.translations.pgettext("Face color"),
        description=bpy.app.translations.pgettext("Hidden surface color"),
        subtype='COLOR', default=[0.0, 0.8, 0.0, 0.1], size=4, min=0.0, max=1.0)
    bpy.types.Scene.ghost_line_size = FloatProperty(
        name=bpy.app.translations.pgettext("Line size"),
        description=bpy.app.translations.pgettext("Line size"),
        default=2.0, min=1.0, max=5.0)
    bpy.types.Material.ghost = bpy.props.BoolProperty(default=True)
    bpy.types.Material.ghost_hide = bpy.props.BoolProperty(default=False)

# プロパティのクリア
def clear_props():
    del bpy.types.Material.ghost
    del bpy.types.Material.ghost_hide
    del bpy.types.Scene.ghost_edge_color
    del bpy.types.Scene.ghost_face_color
    del bpy.types.Scene.ghost_display

# 登録処理
def register():
    bpy.utils.register_class(GM_PT_SelectMaterial)
    bpy.utils.register_class(GM_OT_GhostMesh)
    bpy.utils.register_class(GM_OT_GhostMeshDisplay)
    bpy.utils.register_class(GM_UL_Items)
    init_props()

# 登録解除処理
def unregister():
    clear_props()
    bpy.utils.unregister_class(GM_UL_Items)
    bpy.utils.unregister_class(GM_OT_GhostMeshDisplay)
    bpy.utils.unregister_class(GM_OT_GhostMesh)
    bpy.utils.unregister_class(GM_PT_SelectMaterial)
