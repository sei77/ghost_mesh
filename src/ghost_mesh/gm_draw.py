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
            
            ghost_verts = []
            
            # 隠れた面を描画する
            faces = [face for face in bm.faces if face.hide]
            
            if faces:
                shader = gpu.shader.from_builtin('UNIFORM_COLOR')
                vertices = []
                indices  = []
                
                model_matrix = obj.matrix_world
                
                for face in faces:
                    if not obj.material_slots[face.material_index].material.ghost:
                        ghost_verts.extend(face.verts)
                        continue
                    start_index = len(vertices)
                    for loop in face.loops:
                        vertices.append(model_matrix @ loop.vert.co)
                    for i in range(1, len(face.verts) - 1):
                        indices.append((start_index, start_index + i, start_index + i + 1))
                
                batch = batch_for_shader(shader, 'TRIS', {"pos": vertices}, indices=indices)
                
                gpu.state.depth_test_set('LESS')
                gpu.state.blend_set('ALPHA')
                gpu.state.face_culling_set('BACK')
                
                shader.bind()
                shader.uniform_float("color", bpy.context.scene.ghost_face_color)
                batch.draw(shader)
                
                gpu.state.blend_set('NONE')
                gpu.state.depth_test_set('NONE')
                gpu.state.face_culling_set('NONE')
            
            # 隠れた辺を描画する
            edges = [edge for edge in bm.edges if edge.hide]
            
            if edges:
                shader = gpu.shader.from_builtin('UNIFORM_COLOR')
                vertices = []
                indices  = []
                
                model_matrix = obj.matrix_world
                
                for edge in edges:
                    v1, v2 = edge.verts
                    if v1 in ghost_verts and v2 in ghost_verts:
                        continue
                    vertices.extend([v1.co, v2.co])
                    vertices.extend([model_matrix @ v1.co, model_matrix @ v2.co])
                    indices.append((len(vertices) - 2, len(vertices) - 1))
                
                batch = batch_for_shader(shader, 'LINES', {"pos": vertices}, indices=indices)
                
                gpu.state.depth_test_set('LESS')
                gpu.state.blend_set('ALPHA')
                gpu.state.line_width_set(2.0)
                
                shader.bind()
                if bpy.context.scene.ghost_edge_color:
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

