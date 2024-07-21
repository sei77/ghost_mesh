import bpy
import bmesh
from bpy.props import IntProperty, StringProperty, FloatVectorProperty, FloatProperty, BoolProperty
from . import gm_draw

# すべての頂点、辺、面を表示
def show_all(act_obj):
    
    if act_obj is None or act_obj.type != 'MESH':
        return
    
    old_mode = act_obj.mode
    bpy.ops.object.mode_set(mode="OBJECT")
    
    mesh = act_obj.data
    mesh.update()
    
    for vert in mesh.vertices:
        vert.hide = False
    for edge in mesh.edges:
        edge.hide = False
    for face in mesh.polygons:
        face.hide = False
    
    bpy.ops.object.mode_set(mode=old_mode)


# 表示マテリアル以外のメッシュ非表示
def ghost_mesh(event, act_obj, mat_index):
    
    if act_obj is None or act_obj.type != 'MESH':
        return
    
    old_mode = act_obj.mode
    bpy.ops.object.mode_set(mode="OBJECT")
    
    mesh = act_obj.data
    mesh.update()
    
    # CTRLキーを押していた場合は状態を維持する
    if not event.ctrl:
        for vert in mesh.vertices:
            vert.hide = True
        for face in mesh.polygons:
            face.hide = True
    for edge in mesh.edges:
        edge.hide = False
    
    # 選択マテリアルを持つ面と構成する頂点を表示する
    for face in mesh.polygons:
        if face.material_index == mat_index:
            for v in face.vertices:
                mesh.vertices[v].hide = False
            face.hide = False
    
    # いずれかの頂点が非表示だった場合は辺を隠す
    for edge in mesh.edges:
        v1 = mesh.vertices[edge.vertices[0]]
        v2 = mesh.vertices[edge.vertices[1]]
        
        if v1.hide or v2.hide:
            edge.hide = True
    
    bpy.ops.object.mode_set(mode=old_mode)


# メッシュ表示オペレータ
class GM_OT_GhostMesh(bpy.types.Operator):
    
    bl_idname = "object.ghost_mesh"
    bl_label = "メッシュ表示オペレータ"
    bl_description = "指定マテリアル以外のメッシュを隠す"
    bl_options = {'REGISTER', 'UNDO'}
    
    mat_name  : StringProperty()
    mat_index : IntProperty()
    
    def execute(self, context):
        if context.area.type == 'VIEW_3D':
            ghost_mesh(self, event, bpy.context.object, self.mat_index)
            context.area.tag_redraw()
        return {'FINISHED'}
    
    def invoke(self, context, event):
        if context.area.type == 'VIEW_3D':
            if self.mat_name == '':
                show_all(bpy.context.object)
            else:
                ghost_mesh(event, bpy.context.object, self.mat_index)
            context.area.tag_redraw()
            
            return {'FINISHED'}
        else:
            return {'CANCELLED'}


# メッシュ非表示オペレータ
class GM_OT_GhostMeshDisplay(bpy.types.Operator):
    
    bl_idname = "object.ghost_mesh_display"
    bl_label = "表示・非表示切り替え"
    bl_description = "指定マテリアルの表示・非表示切り替え"
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

    bl_label = "表示マテリアルの選択"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ゴースト"
    bl_context = "mesh_edit"
    
    def draw(self, context):
        
        layout = self.layout
        
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            return
        
        op1 = layout.operator(GM_OT_GhostMesh.bl_idname,text='Show All', icon='SHADING_RENDERED')
        op1.mat_name  = ''
        op1.mat_index = 0
        
        if not obj.material_slots:
            return
        
        for i, mat_slot in enumerate(obj.material_slots):
            mat = mat_slot.material
            if mat:
                if not hasattr(mat, 'ghost'):
                    mat.ghost = False
                sp = layout.split(align=True,factor=0.8)
                op1 = sp.operator(GM_OT_GhostMesh.bl_idname, text=mat.name, icon='MATERIAL')
                op1.mat_name  = mat.name
                op1.mat_index = i
                op2 = sp.operator(GM_OT_GhostMeshDisplay.bl_idname, text='', icon='GHOST_ENABLED' if mat.ghost else 'X')
                op2.mat_index = i
            else:
                op1 = layout.operator(GM_OT_GhostMesh.bl_idname, text='No Material Assigned', icon='MATERIAL')
                op1.mat_name = 'No Material Assigned'
                op1.mat_index = -1


class GM_PT_SelectMaterialOption(bpy.types.Panel):

    bl_label = "オプション設定"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ゴースト"
    bl_context = "mesh_edit"
    
    def draw(self, context):
        
        layout = self.layout
        scene = context.scene
        
        layout.prop(scene, "ghost_display"   , text="ゴーストを表示")
        layout.prop(scene, "ghost_edge_color", text="辺の色")
        layout.prop(scene, "ghost_face_color", text="面の色")
        
        gm_draw.CustomDrawOperator.init_draw()


def init_props():
    bpy.types.Scene.ghost_display = BoolProperty(
        name="ゴーストを表示",
        description="隠れた辺や面を半透明で表示する",
        default=True)
    bpy.types.Scene.ghost_edge_color = FloatVectorProperty(
        name="辺の色",
        description="隠れた辺の色",
        subtype='COLOR', default=[0.0, 1.0, 0.0, 0.1], size=4, min=0.0, max=1.0)
    bpy.types.Scene.ghost_face_color = FloatVectorProperty(
        name="面の色",
        description="隠れた面の色",
        subtype='COLOR', default=[0.0, 0.8, 0.0, 0.1], size=4, min=0.0, max=1.0)
    bpy.types.Material.ghost = bpy.props.BoolProperty(
        name="ゴースト表示", default=True)


def clear_props():
    del bpy.types.Material.ghost
    del bpy.types.Scene.ghost_edge_color
    del bpy.types.Scene.ghost_face_color
    del bpy.types.Scene.ghost_display


def register():
    bpy.utils.register_class(GM_PT_SelectMaterial)
    bpy.utils.register_class(GM_PT_SelectMaterialOption)
    bpy.utils.register_class(GM_OT_GhostMesh)
    bpy.utils.register_class(GM_OT_GhostMeshDisplay)
    init_props()


def unregister():
    clear_props()
    bpy.utils.unregister_class(GM_OT_GhostMeshDisplay)
    bpy.utils.unregister_class(GM_OT_GhostMesh)
    bpy.utils.unregister_class(GM_PT_SelectMaterialOption)
    bpy.utils.unregister_class(GM_PT_SelectMaterial)
