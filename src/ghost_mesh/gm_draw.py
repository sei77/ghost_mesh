import bpy
import gpu
import bmesh
from bpy.app.handlers import persistent
from gpu_extras.batch import batch_for_shader
from mathutils import Matrix
from bpy.props import FloatVectorProperty


# オブジェクトの描画状態を保持するクラス
class DrawObjectData:
    isCache   = False
    isDisplay = False
    vertEdge  = []
    vertFace  = []
    indices   = []


# 非表示設定されたオブジェクト、マテリアルの辺と面を描画する
class GM_OT_CustomDraw(bpy.types.Operator):
    bl_idname = "gm.custom_draw"
    bl_label  = "Draw ghost mesh"
    
    DrawHandle = None
    
    def invoke(self, context, event):
        if GM_OT_CustomDraw.DrawHandle is None:
            GM_OT_CustomDraw.DrawHandle = bpy.types.SpaceView3D.draw_handler_add(
                GM_OT_CustomDraw.draw_callback, (), 'WINDOW', 'POST_VIEW')
        return {'RUNNING_MODAL'}
    
    def draw_callback():
        scn = bpy.context.scene
        
        objects = [obj for obj in scn.objects if obj.type == 'MESH']
        for obj in objects:
            # オブジェクトの描画状態を取得する
            if not obj.name in DrawObject:
                DrawObject[obj.name] = DrawObjectData()
                DrawObject[obj.name].isCache = False
                DrawObject[obj.name].isDisplay = obj.hide_get()
            state = DrawObject[obj.name]
            
            if obj.mode == 'EDIT' and not obj.hide_get():
                draw_material(obj, scn, state)
            elif obj.hide_get():
                draw_object(obj, scn, state)


# マテリアルの半透明描画
def draw_material(obj, scn, state):
    
    # 非表示マテリアルの描画状態を更新する
    if state.isCache == False:
        state.isCache = True
        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_obj = obj.evaluated_get(depsgraph)
        eval_mesh = eval_obj.to_mesh()
        bm = bmesh.new()
        bm.from_mesh(eval_mesh)
        
        state.vertEdge = []
        state.vertFace = []
        state.indices  = []
        
        # マテリアルの非表示フラグをクリア
        for mat_slot in obj.material_slots:
            mat_slot.material.ghost_hide = False
        
        # 非表示マテリアルの面/辺の情報を取得する
        faces = [face for face in bm.faces if face.hide]
        
        if faces:
            model_matrix = obj.matrix_world
            
            edge_exists = set()
            for face in faces:
                if len(obj.material_slots) > 0:
                    # 非表示フラグを設定
                    obj.material_slots[face.material_index].material.ghost_hide = True
                    # 半透明描画しないマテリアルの場合は継続
                    if obj.material_slots[face.material_index].material.ghost == False:
                        continue
                
                # 非表示マテリアルの面を設定
                if scn.edit_ghost_display2 == True:
                    start_index = len(state.vertFace)
                    for loop in face.loops:
                        state.vertFace.append(model_matrix @ loop.vert.co)
                    for i in range(1, len(face.verts) - 1):
                        state.indices.append((start_index, start_index + i, start_index + i + 1))
                # 非表示マテリアルの辺を設定
                if scn.edit_ghost_display1 == True:
                    for edge in face.edges:
                        if edge.index not in edge_exists:
                            edge_exists.add(edge.index)
                            state.vertEdge.append(model_matrix @ edge.verts[0].co)
                            state.vertEdge.append(model_matrix @ edge.verts[1].co)
    
    gpu.state.clip_distances_set(1)
    gpu.state.depth_test_set('LESS')
    gpu.state.blend_set('ALPHA')
    gpu.state.face_culling_set('BACK')
    
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    shader.bind()
    
    # 非表示マテリアルの面を描画する
    if scn.edit_ghost_display2 == True:
        batch = batch_for_shader(shader, 'TRIS', {"pos": state.vertFace}, indices=state.indices)
        shader.uniform_float("color", scn.edit_ghost_face_color)
        batch.draw(shader)
    
    # 非表示マテリアルの辺を描画する
    if scn.edit_ghost_display1 == True:
        gpu.state.line_width_set(scn.ghost_line_size)
        batch = batch_for_shader(shader, 'LINES', {"pos": state.vertEdge})
        shader.uniform_float("color", scn.edit_ghost_edge_color)
        batch.draw(shader)
    
    gpu.state.face_culling_set('NONE')
    gpu.state.blend_set('NONE')
    gpu.state.depth_test_set('NONE')
    gpu.state.clip_distances_set(0)


# オブジェクトの半透明描画
def draw_object(obj, scn, state):
    
    # 非表示オブジェクトを描画しない場合は処理行わない
    if obj.ghost_hide == True:
        return
    
    # 非表示オブジェクトの描画状態を更新する
    if state.isCache == False:
        state.isCache = True
        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_obj = obj.evaluated_get(depsgraph)
        eval_mesh = eval_obj.to_mesh()
        bm = bmesh.new()
        bm.from_mesh(eval_mesh)
        
        state.vertEdge = []
        state.vertFace = []
        state.indices  = []
        
        # 非表示オブジェクトの面/辺の情報を取得する
        faces = [face for face in bm.faces]
        
        if faces:
            model_matrix = obj.matrix_world
            
            edge_exists = set()
            for face in faces:
                # 非表示オブジェクトの面を設定
                if scn.object_ghost_display2 == True:
                    start_index = len(state.vertFace)
                    for loop in face.loops:
                        state.vertFace.append(model_matrix @ loop.vert.co)
                    for i in range(1, len(face.verts) - 1):
                        state.indices.append((start_index, start_index + i, start_index + i + 1))
                # 非表示オブジェクトの辺を設定
                if scn.object_ghost_display1 == True:
                    for edge in face.edges:
                        if edge.index not in edge_exists:
                            edge_exists.add(edge.index)
                            state.vertEdge.append(model_matrix @ edge.verts[0].co)
                            state.vertEdge.append(model_matrix @ edge.verts[1].co)
    
    gpu.state.clip_distances_set(1)
    gpu.state.depth_test_set('LESS')
    gpu.state.blend_set('ALPHA')
    gpu.state.face_culling_set('BACK')
    
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    shader.bind()
    
    # 非表示オブジェクトの面を描画する
    if scn.object_ghost_display2 == True:
        batch = batch_for_shader(shader, 'TRIS', {"pos": state.vertFace}, indices=state.indices)
        shader.uniform_float("color", scn.object_ghost_face_color)
        batch.draw(shader)
    
    # 非表示オブジェクトの辺を描画する
    if scn.object_ghost_display1 == True:
        gpu.state.line_width_set(scn.ghost_line_size)
        batch = batch_for_shader(shader, 'LINES', {"pos": state.vertEdge})
        shader.uniform_float("color", scn.object_ghost_edge_color)
        batch.draw(shader)
    
    gpu.state.face_culling_set('NONE')
    gpu.state.blend_set('NONE')
    gpu.state.depth_test_set('NONE')
    gpu.state.clip_distances_set(0)


DrawObject = {}


@persistent
def load_handler(dummy):
    bpy.ops.gm.custom_draw('INVOKE_DEFAULT')


@persistent
def depsgraph_update_handler(scn, depsgraph):
    # メッシュオブジェクトの状態変化を描画に反映させる
    active_object = bpy.context.view_layer.objects.active
    scn.mesh_objects.clear()
    for obj in scn.objects:
        if obj.type != 'MESH':
            continue
            
        if not obj.name in DrawObject:
            DrawObject[obj.name] = DrawObjectData()
            DrawObject[obj.name].isCache = False
        elif obj.hide_get() != DrawObject[obj.name].isDisplay:
            DrawObject[obj.name].isCache = False
            DrawObject[obj.name].isDisplay = obj.hide_get()
        elif active_object == obj:
            DrawObject[obj.name].isCache = False
            DrawObject[obj.name].isDisplay = obj.hide_get()
        
        item = scn.mesh_objects.add()
        item.name = obj.name
        item.object_ref = obj

# 登録処理
def register():
    bpy.utils.register_class(GM_OT_CustomDraw)
    bpy.app.handlers.load_post.append(load_handler)
    bpy.app.handlers.depsgraph_update_post.append(depsgraph_update_handler)


# 登録解除処理
def unregister():
    bpy.app.handlers.depsgraph_update_post.remove(depsgraph_update_handler)
    bpy.app.handlers.load_post.remove(load_handler)
    bpy.utils.unregister_class(GM_OT_CustomDraw)

