import bpy
import bmesh
from bpy.types import Panel, UIList, Operator, PropertyGroup, Object
from bpy.props import IntProperty, FloatProperty, FloatVectorProperty, BoolProperty, CollectionProperty, StringProperty, PointerProperty
from . import gm_draw


# 編集モード用のパネル登録
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
            row = layout.operator(GM_OT_GhostMesh.bl_idname, text='Show All', icon='SHADING_RENDERED')
            row.selected = -1
            
            row = layout.row()
            row.template_list("GM_UL_MaterialItems", "material_list", obj, "material_slots", obj, "active_material_index", rows=6)
            
            layout.prop(scn, "edit_ghost_display1"  , text="Edit Ghosting Display(Edge)")
            layout.prop(scn, "edit_ghost_display2"  , text="Edit Ghosting Display(Face)")
            layout.prop(scn, "edit_ghost_edge_color", text="Edit Edge color")
            layout.prop(scn, "edit_ghost_face_color", text="Edit Face color")
            
            layout.separator()
        
        row = layout.row()
        row.template_list("GM_UL_ObjectItems", "object_list", scn, "mesh_objects", scn, "mesh_objects_index", rows=6)
        
        layout.prop(scn, "object_ghost_display1"  , text="Object Ghosting Display(Edge)")
        layout.prop(scn, "object_ghost_display2"  , text="Object Ghosting Display(Face)")
        layout.prop(scn, "object_ghost_edge_color", text="Object Edge color")
        layout.prop(scn, "object_ghost_face_color", text="Object Face color")


# オブジェクトモード用のパネル登録
class GM_PT_ObjectModePanel(bpy.types.Panel):
    bl_label = bpy.app.translations.pgettext("Drawing Settings")
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = bpy.app.translations.pgettext("Ghost")
    bl_context = "objectmode"
    
    def draw(self, context):
        
        layout = self.layout
        scn = context.scene
        obj = context.active_object
        row = layout.row()
        row.template_list("GM_UL_ObjectItems", "object_list", scn, "mesh_objects", scn, "mesh_objects_index", rows=6)
        
        layout.prop(scn, "object_ghost_display1"  , text="Object Ghosting Display(Edge)")
        layout.prop(scn, "object_ghost_display2"  , text="Object Ghosting Display(Face)")
        layout.prop(scn, "object_ghost_edge_color", text="Object Edge color")
        layout.prop(scn, "object_ghost_face_color", text="Object Face color")


# マテリアルのリスト項目
class GM_UL_MaterialItems(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        
        row = layout.row(align=False)
        row.label(text=" " + item.material.name)
        row = layout.row(align=True)
        
        op = row.operator(GM_OT_GhostMesh.bl_idname, text="", 
            icon="HIDE_ON" if item.material.ghost_hide else "HIDE_OFF")
        op.selected = index
        op = row.operator(GM_OT_GhostMeshDisplay.bl_idname, text="", 
            icon="GHOST_ENABLED" if item.material.ghost else "GHOST_DISABLED")
        op.selected = index
    
    def invoke(self, context, event):
        pass


# オブジェクトのリスト項目
class GM_UL_ObjectItems(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        
        if item.object_ref.type != 'MESH':
            return
        
        row = layout.row(align=False)
        row.label(text=" " + item.name)
        row = layout.row(align=True)
        
        op = row.operator(GM_OT_GhostObject.bl_idname, text="", 
            icon="HIDE_ON" if item.object_ref.hide_get() else "HIDE_OFF")
        op.selected = item.object_ref.name
        op = row.operator(GM_OT_GhostObjectDisplay.bl_idname, text="", 
            icon="GHOST_ENABLED" if not item.object_ref.ghost_hide else "GHOST_DISABLED")
        op.selected = item.object_ref.name
    
    def invoke(self, context, event):
        pass


# メッシュの半透明表示オペレータ
class GM_OT_GhostMesh(bpy.types.Operator):
    bl_idname = "object.ghost_mesh"
    bl_label = bpy.app.translations.pgettext("Mesh display/hide")
    bl_description = bpy.app.translations.pgettext("Hide all meshes except those to which materials are assigned")
    bl_options = {'REGISTER', 'UNDO'}
    
    selected : IntProperty()
    
    def invoke(self, context, event):
        if context.area.type == 'VIEW_3D':
            obj = context.active_object
            if obj is None or obj.type != 'MESH' or obj.hide_get():
                return {'CANCELLED'}
            
            # すべて表示
            if self.selected == -1:
                old_mode = obj.mode
                bpy.ops.object.mode_set(mode='OBJECT')
                mesh = obj.data
                for vert in mesh.vertices:
                    vert.hide = False
                for edge in mesh.edges:
                    edge.hide = False
                for face in mesh.polygons:
                    face.hide = False
                mesh.update()
                bpy.ops.object.mode_set(mode=old_mode)
                
            # 個別マテリアルの表示
            else:
                mat = obj.material_slots[self.selected].material
                
                old_mode = obj.mode
                bpy.ops.object.mode_set(mode='OBJECT')
                mesh = obj.data
                
                # 頂点はすべて非表示、辺はすべて表示
                for vert in mesh.vertices:
                    vert.hide = True
                for edge in mesh.edges:
                    edge.hide = False
                # 現状を維持して対象を表示する
                if mat.ghost_hide:
                    for face in mesh.polygons:
                        if face.material_index == self.selected or face.hide == False:
                            face.hide = False
                            for v in face.vertices:
                                mesh.vertices[v].hide = False
                # 現状を維持して対象を非表示にする
                else:
                    for face in mesh.polygons:
                        if face.material_index == self.selected:
                            face.hide = True
                        elif face.hide == False:
                            for v in face.vertices:
                                mesh.vertices[v].hide = False
                # いずれかの頂点が非表示だった場合は辺を隠す
                for edge in mesh.edges:
                    v1 = mesh.vertices[edge.vertices[0]]
                    v2 = mesh.vertices[edge.vertices[1]]
                    
                    if v1.hide or v2.hide:
                        edge.hide = True
                mesh.update()
                bpy.ops.object.mode_set(mode=old_mode)
            
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
    
    selected : IntProperty()
    
    def invoke(self, context, event):
        if context.area.type == 'VIEW_3D':
            obj = context.active_object
            if obj is None or obj.type != 'MESH' or obj.hide_get():
                return {'CANCELLED'}
            mat = obj.material_slots[self.selected].material
            mat.ghost = False if mat.ghost else True
            gm_draw.DrawObject[context.active_object.name].isCache = False
            context.area.tag_redraw()
            return {'FINISHED'}
        else:
            return {'CANCELLED'}


# オブジェクトの半透明表示オペレータ
class GM_OT_GhostObject(bpy.types.Operator):
    bl_idname = "object.ghost_object"
    bl_label = bpy.app.translations.pgettext("Mesh display/hide")
    bl_description = bpy.app.translations.pgettext("Hide all meshes except those to which materials are assigned")
    bl_options = {'REGISTER', 'UNDO'}
    
    selected: StringProperty()
    
    def invoke(self, context, event):
        if context.area.type == 'VIEW_3D':
            obj = context.scene.objects[self.selected]
            obj.hide_set(not obj.hide_get())
            context.area.tag_redraw()
            return {'FINISHED'}
        else:
            return {'CANCELLED'}


# オブジェクト非表示オペレータ
class GM_OT_GhostObjectDisplay(bpy.types.Operator):
    bl_idname = "object.ghost_object_display"
    bl_label = bpy.app.translations.pgettext("Mesh display/hide")
    bl_description = bpy.app.translations.pgettext("Hide all meshes except those to which materials are assigned")
    bl_options = {'REGISTER', 'UNDO'}
    
    selected: StringProperty()
     
    def invoke(self, context, event):
        if context.area.type == 'VIEW_3D':
            obj = context.scene.objects[self.selected]
            obj.ghost_hide = False if obj.ghost_hide else True
            gm_draw.DrawObject[obj.name].isCache = False
            context.area.tag_redraw()
            return {'FINISHED'}
        else:
            return {'CANCELLED'}


# 登録処理
def register():
    bpy.utils.register_class(GM_PT_ObjectModePanel)
    bpy.utils.register_class(GM_PT_EditModePanel)
    bpy.utils.register_class(GM_OT_GhostMesh)
    bpy.utils.register_class(GM_OT_GhostMeshDisplay)
    bpy.utils.register_class(GM_OT_GhostObject)
    bpy.utils.register_class(GM_OT_GhostObjectDisplay)
    bpy.utils.register_class(GM_UL_MaterialItems)
    bpy.utils.register_class(GM_UL_ObjectItems)


# 解除処理
def unregister():
    bpy.utils.unregister_class(GM_UL_ObjectItems)
    bpy.utils.unregister_class(GM_UL_MaterialItems)
    bpy.utils.unregister_class(GM_OT_GhostObjectDisplay)
    bpy.utils.unregister_class(GM_OT_GhostObject)
    bpy.utils.unregister_class(GM_OT_GhostMeshDisplay)
    bpy.utils.unregister_class(GM_OT_GhostMesh)
    bpy.utils.unregister_class(GM_PT_EditModePanel)
    bpy.utils.unregister_class(GM_PT_ObjectModePanel)
