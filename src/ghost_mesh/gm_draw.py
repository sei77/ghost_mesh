import bpy
import gpu
import bmesh
from bpy.app.handlers import persistent
from gpu_extras.batch import batch_for_shader
from mathutils import Matrix
from bpy.props import FloatVectorProperty


# 非表示設定された辺と面を描画する
class CustomDrawOperator(bpy.types.Operator):
    bl_idname = "view3d.draw_ghost_mesh"
    bl_label  = "Draw Ghost Mesh"
    
    _handle  = None
    
    def invoke(self, context, event):
        CustomDrawOperator.init_draw()
        return {'RUNNING_MODAL'}
    
    def init_draw():
        if CustomDrawOperator._handle is None:
            CustomDrawOperator._handle = bpy.types.SpaceView3D.draw_handler_add(
                CustomDrawOperator.draw_callback, (), 'WINDOW', 'POST_VIEW')
        return
    
    def draw_callback():
        if not hasattr(bpy.context.scene,'ghost_display') or bpy.context.scene.ghost_display == False:
            return
        
        obj = bpy.context.active_object
        if obj and obj.mode == 'EDIT':
            
            # ミラーモディファイアーが適用されているか判定
            has_mirror_modifier = any(mod.type == 'MIRROR' for mod in obj.modifiers)
            if has_mirror_modifier == True:
                # モディファイア適用後のメッシュを取得
                depsgraph = bpy.context.evaluated_depsgraph_get()
                eval_obj = obj.evaluated_get(depsgraph)
                eval_mesh = eval_obj.to_mesh()
                
                # 評価されたメッシュから bmesh を作成
                bm = bmesh.new()
                bm.from_mesh(eval_mesh)
            else:
                bm = bmesh.from_edit_mesh(obj.data)
            
            # 隠れた面/辺を描画する
            faces = [face for face in bm.faces if face.hide]
            
            if faces:
                edge_vert = []
                face_vert = []
                indices   = []
                
                model_matrix = obj.matrix_world
                
                for face in faces:
                    if not obj.material_slots[face.material_index].material.ghost:
                        continue
                    start_index = len(face_vert)
                    for loop in face.loops:
                        face_vert.append(model_matrix @ loop.vert.co)
                    for i in range(1, len(face.verts) - 1):
                        indices.append((start_index, start_index + i, start_index + i + 1))
                    for edge in face.edges:
                        edge_vert.append(model_matrix @ edge.verts[0].co)
                        edge_vert.append(model_matrix @ edge.verts[1].co)
                
                gpu.state.depth_test_set('LESS')
                gpu.state.blend_set('ALPHA')
                gpu.state.face_culling_set('BACK')
                
                shader = gpu.shader.from_builtin('UNIFORM_COLOR')
                shader.bind()
                
                batch = batch_for_shader(shader, 'TRIS', {"pos": face_vert}, indices=indices)
                shader.uniform_float("color", bpy.context.scene.ghost_face_color)
                batch.draw(shader)
                gpu.state.face_culling_set('NONE')
                
                gpu.state.line_width_set(2.0)
                batch = batch_for_shader(shader, 'LINES', {"pos": edge_vert})
                shader.uniform_float("color", bpy.context.scene.ghost_edge_color)
                batch.draw(shader)
                
                gpu.state.blend_set('NONE')
                gpu.state.depth_test_set('NONE')
            
            bm.free()

def register():
    bpy.utils.register_class(CustomDrawOperator)
    bpy.app.handlers.load_post.append(load_handler)

def unregister():
    bpy.app.handlers.load_post.remove(load_handler)
    bpy.utils.unregister_class(CustomDrawOperator)

@persistent
def load_handler(dummy):
    bpy.ops.view3d.draw_ghost_mesh('INVOKE_DEFAULT')

