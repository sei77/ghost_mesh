import bpy
import gpu
import bmesh
from bpy.app.handlers import persistent
from gpu_extras.batch import batch_for_shader
from mathutils import Matrix
from bpy.props import FloatVectorProperty

# 非表示設定された辺と面を描画する
class GM_OT_CustomDraw(bpy.types.Operator):
    bl_idname = "gm.custom_draw"
    bl_label  = "Draw Ghost Mesh"
    
    _handle  = None
    
    def invoke(self, context, event):
        GM_OT_CustomDraw.init_draw()
        return {'RUNNING_MODAL'}
    
    def init_draw():
        if GM_OT_CustomDraw._handle is None:
            GM_OT_CustomDraw._handle = bpy.types.SpaceView3D.draw_handler_add(
                GM_OT_CustomDraw.draw_callback, (), 'WINDOW', 'POST_VIEW')
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
            
            # 非表示フラグをクリア
            for i, mat_slot in enumerate(obj.material_slots):
                if hasattr(mat_slot.material, 'ghost_hide'):
                    mat_slot.material.ghost_hide = False
            
            # 隠れた面/辺を描画する
            faces = [face for face in bm.faces if face.hide]
            
            if faces:
                edge_vert = []
                face_vert = []
                face_indices = []
                
                model_matrix = obj.matrix_world
                
                edge_exists = {}
                for face in faces:
                    if len(obj.material_slots) > 0:
                        # 非表示フラグを設定
                        if hasattr(obj.material_slots[face.material_index].material, 'ghost_hide'):
                            if obj.material_slots[face.material_index].material.ghost_hide == False:
                                obj.material_slots[face.material_index].material.ghost_hide = True
                        # ゴーストを表示しない場合は継続
                        if hasattr(obj.material_slots[face.material_index].material, 'ghost'):
                            if obj.material_slots[face.material_index].material.ghost == False:
                                continue
                    
                    # 描画対象の面、辺を設定
                    start_index = len(face_vert)
                    for loop in face.loops:
                        face_vert.append(model_matrix @ loop.vert.co)
                    for i in range(1, len(face.verts) - 1):
                        face_indices.append((start_index, start_index + i, start_index + i + 1))
                    for edge in face.edges:
                        if edge.index not in edge_exists:
                            edge_exists[edge.index] = edge.index
                            edge_vert.append(model_matrix @ edge.verts[0].co)
                            edge_vert.append(model_matrix @ edge.verts[1].co)
                
                gpu.state.clip_distances_set(1)
                gpu.state.depth_test_set('LESS')
                gpu.state.blend_set('ALPHA')
                gpu.state.face_culling_set('BACK')
                
                shader = gpu.shader.from_builtin('UNIFORM_COLOR')
                shader.bind()
                
                batch = batch_for_shader(shader, 'TRIS', {"pos": face_vert}, indices=face_indices)
                shader.uniform_float("color", bpy.context.scene.ghost_face_color)
                batch.draw(shader)
                gpu.state.face_culling_set('NONE')
                
                gpu.state.line_width_set(bpy.context.scene.ghost_line_size)
                batch = batch_for_shader(shader, 'LINES', {"pos": edge_vert})
                shader.uniform_float("color", bpy.context.scene.ghost_edge_color)
                batch.draw(shader)
                
                gpu.state.blend_set('NONE')
                gpu.state.depth_test_set('NONE')
                gpu.state.clip_distances_set(0)

# 登録処理
def register():
    bpy.utils.register_class(GM_OT_CustomDraw)
    bpy.app.handlers.load_post.append(load_handler)

# 登録解除処理
def unregister():
    bpy.app.handlers.load_post.remove(load_handler)
    bpy.utils.unregister_class(GM_OT_CustomDraw)

# 永続ハンドラー
@persistent
def load_handler(dummy):
    bpy.ops.gm.custom_draw('INVOKE_DEFAULT')

