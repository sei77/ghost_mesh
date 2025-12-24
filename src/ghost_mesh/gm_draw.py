import bpy
import gpu
import bmesh
from bpy.app.handlers import persistent
from gpu_extras.batch import batch_for_shader
from mathutils import Matrix, Vector
from bpy.props import FloatVectorProperty
from . import gm_prop


# オブジェクトの描画状態を保持するクラス
# - 各オブジェクトごとに描画キャッシュ、バッチ、ワールド行列などを保持する
class _draw_objectsData:
    def __init__(self):
        self.is_cache     = False
        self.is_display   = False
        self.batch_edge   = None
        self.batch_face   = None
        self.matrix_world = Matrix.Identity(4)

_draw_objects = {}
_shader_cache = None

# 組み込みシェーダーを取得・キャッシュする関数
# - 初回呼び出しで組み込みシェーダーを取得し、以後はキャッシュを返す
# - シェーダー初期化に失敗した場合は None を返す可能性がある
def get_shader():
    global _shader_cache
    if _shader_cache is None:
        try:
            _shader_cache = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
        except Exception:
            try:
                _shader_cache = gpu.shader.from_builtin('UNIFORM_COLOR')
            except Exception as e:
                print(f"Shader initialization failed: {e}")
    return _shader_cache

# 編集モード向けメッシュ解析とバッチ生成
# - 編集モード中の非表示（hidden）フェースを BMesh で解析し、
#   面バッチと辺バッチを作成して cache に格納する
# - 評価メッシュと BMesh は finally で確実に解放される
def update_mesh_cache(obj, scn, cache):
    
    cache.batch_face = cache.batch_edge = None
    
    # モディファイア適用後のメッシュを取得
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    eval_mesh = None
    bm = None
    try:
        eval_mesh = evaluated.to_mesh()
        
        # BMeshによるメッシュ解析開始
        bm = bmesh.new()
        bm.from_mesh(eval_mesh)
        
        # 非表示マテリアルの面情報を取得する
        faces = [face for face in bm.faces if face.hide]
        shader = get_shader()
        
        # 描画バッチの作成
        verts, indices = [], []
        edge_verts, edge_exists = [], set()
        for face in faces:
            # 特定のマテリアルの半透明描画を除外する判定
            if len(obj.material_slots) > 0:
                mat = obj.material_slots[face.material_index].material
                if mat and getattr(mat, "ghost_hide", True): continue
                
            if getattr(scn, "edit_ghost_display_face", True):
                start_idx = len(verts)
                for loop in face.loops:
                    verts.append(loop.vert.co.to_tuple())
                for i in range(1, len(face.verts) - 1):
                    indices.append((start_idx, start_idx + i, start_idx + i + 1))
                if verts:
                    cache.batch_face = batch_for_shader(shader, 'TRIS', {"pos": verts}, indices=indices)
        
            if getattr(scn, "edit_ghost_display_edge", True):
                for edge in face.edges:
                    if edge.index not in edge_exists:
                        edge_exists.add(edge.index)
                        edge_verts.append(edge.verts[0].co.to_tuple())
                        edge_verts.append(edge.verts[1].co.to_tuple())
                if edge_verts:
                    cache.batch_edge = batch_for_shader(shader, 'LINES', {"pos": edge_verts})
        
        cache.is_cache = True
    finally:
        if bm is not None:
            bm.free()
        if eval_mesh is not None:
            evaluated.to_mesh_clear()


# オブジェクトモード向けバッチ生成
# - 非表示オブジェクトの評価メッシュを取得し、面/辺のバッチを作成する
# - 評価メッシュは finally で解放される
def update_object_cache(obj, scn, cache):
    
    cache.batch_face = None
    cache.batch_edge = None
    
    # 非表示オブジェクトを描画しない場合は処理行わない
    if getattr(obj, "ghost_hide", False):
        return
    
    # モディファイア適用後のメッシュを取得
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = None
    try:
        mesh = evaluated.to_mesh()
        mesh.calc_loop_triangles() # 三角形化データを内部計算
        
        # 頂点とインデックスを Vector/Tuple のリストとして一括取得
        verts = [v.co for v in mesh.vertices]
        faces = [t.vertices for t in mesh.loop_triangles]
        
        shader = get_shader()
        if getattr(scn, "object_ghost_display_face", True):
            cache.batch_face = batch_for_shader(shader, 'TRIS', {"pos": verts}, indices=faces)
        
        if getattr(scn, "object_ghost_display_edge", True):
            edges = [e.vertices for e in mesh.edges]
            cache.batch_edge = batch_for_shader(shader, 'LINES', {"pos": verts}, indices=edges)
        
        cache.is_cache = True
    finally:
        if mesh is not None:
            evaluated.to_mesh_clear()

# GPU バッチを使用して半透明面およびエッジを描画する
# - シェーダーと MVP 行列を設定し、必要に応じて面/辺を描画する
# - GPU ステート（深度テスト・ブレンド・カリング）を設定し、描画後に復元する
def draw_ghost_geometry(cache, color_face, color_edge, line_width):
    
    if not cache.batch_face and not cache.batch_edge:
        return

    # MVP行列の合成
    view_matrix = gpu.matrix.get_model_view_matrix()
    proj_matrix = gpu.matrix.get_projection_matrix()
    mvp_matrix = proj_matrix @ view_matrix @ cache.matrix_world
    
    shader = get_shader()
    shader.bind()
    shader.uniform_float("ModelViewProjectionMatrix", mvp_matrix)
    
    gpu.state.depth_test_set('LESS')
    gpu.state.blend_set('ALPHA')
    gpu.state.face_culling_set('BACK')
    
    if cache.batch_face:
        shader.uniform_float("color", color_face)
        cache.batch_face.draw(shader)
    
    if cache.batch_edge:
        gpu.state.line_width_set(line_width)
        shader.uniform_float("color", color_edge)
        cache.batch_edge.draw(shader)
    
    gpu.state.face_culling_set('NONE')
    gpu.state.blend_set('NONE')
    gpu.state.depth_test_set('NONE')


# ビュー上でゴーストメッシュの描画を行うオペレータ
# - SpaceView3D に draw handler を登録して、各フレームで該当オブジェクトの
#   隠された面/辺の描画を実行する
class GM_OT_CustomDraw(bpy.types.Operator):
    bl_idname = "gm.custom_draw"
    bl_label  = "Draw ghost mesh"
    
    _handle = None
    
    def invoke(self, context, event):
        if GM_OT_CustomDraw._handle is None:
            GM_OT_CustomDraw._handle = bpy.types.SpaceView3D.draw_handler_add(
                GM_OT_CustomDraw.draw_callback, (), 'WINDOW', 'POST_VIEW')
            return {'RUNNING_MODAL'}
        return {'CANCELLED'}

    def draw_callback():
        scn = bpy.context.scene

        # ビュー行列・射影行列を先に取得し、複数オブジェクトで共有する
        view_matrix = gpu.matrix.get_model_view_matrix()
        proj_matrix = gpu.matrix.get_projection_matrix()
        view_proj = proj_matrix @ view_matrix

        def _is_obj_in_view(obj, cache, view_proj_matrix):
            try:
                for corner in obj.bound_box:
                    world_co = cache.matrix_world @ Vector(corner)
                    clip = view_proj_matrix @ world_co.to_4d()
                    w = clip.w
                    if w == 0.0:
                        continue
                    x = clip.x / w
                    y = clip.y / w
                    z = clip.z / w
                    if -1.0 <= x <= 1.0 and -1.0 <= y <= 1.0 and -1.0 <= z <= 1.0:
                        return True
                return False
            except Exception:
                return True

        for obj in [obj for obj in scn.objects if obj.type == 'MESH']:
            # 初回登場オブジェクトのデータ初期化
            if obj.name not in _draw_objects:
                _draw_objects[obj.name] = _draw_objectsData()
            cache = _draw_objects[obj.name]
            cache.matrix_world = obj.matrix_world.copy()

            # 画面外で選択・アクティブでないオブジェクトは処理をスキップ
            if (not _is_obj_in_view(obj, cache, view_proj)) and (not obj.select_get()) and (obj != bpy.context.active_object):
                continue

            if obj.mode == 'EDIT' and not obj.hide_get():
                if not cache.is_cache:
                    update_mesh_cache(obj, scn, cache)
                draw_ghost_geometry(
                    cache, scn.edit_ghost_face_color, 
                    scn.edit_ghost_edge_color, scn.ghost_line_size
                )
            elif obj.hide_get():
                if not cache.is_cache:
                    update_object_cache(obj, scn, cache)
                draw_ghost_geometry(
                    cache, scn.object_ghost_face_color, 
                    scn.object_ghost_edge_color, scn.ghost_line_size
                )

# .blend ファイル読み込み後にドローハンドラを起動するハンドラ
@persistent
def load_handler(dummy):
    bpy.ops.gm.custom_draw('INVOKE_DEFAULT')

# depsgraph の更新を監視して描画キャッシュや UI を更新するハンドラ
# - メッシュ/オブジェクトの変更を検出し、必要に応じてキャッシュを無効化する
@persistent
def depsgraph_update_handler(scn, depsgraph):
    
    all_names = {obj.name for obj in scn.objects}
    for name in list(_draw_objects.keys()):
        if name not in all_names:
            del _draw_objects[name]
    
    needs_ui_refresh = False
    for update in depsgraph.updates:
        if isinstance(update.id, bpy.types.Mesh):
            mesh_name = update.id.name
            for obj in scn.objects:
                if obj.type == 'MESH' and obj.data.name == mesh_name:
                    if obj.name in _draw_objects:
                        _draw_objects[obj.name].is_cache = False
        elif isinstance(update.id, bpy.types.Object):
            obj_name = update.id.name
            if obj_name in _draw_objects:
                state = _draw_objects[obj_name]
                obj = update.id
                if update.is_updated_geometry or obj.hide_get() != state.is_display:
                    state.is_cache = False
                    state.is_display = obj.hide_get()
        if isinstance(update.id, (bpy.types.Scene, bpy.types.Object)):
            needs_ui_refresh = True
            break
            
    if needs_ui_refresh:
        gm_prop.update_mesh_object_list(scn)


# 全オブジェクトの描画キャッシュを無効化し、View3D を再描画するユーティリティ
# - プロパティの変更（チェックボックス等）や外部イベントから呼び出して使用する
def invalidate_all_caches():
    for state in _draw_objects.values():
        state.is_cache = False
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()


# アドオン登録処理: オペレータの登録とハンドラの追加を行う
# 注意: draw handler の追加は operator.invoke 内で行われる
def register():
    bpy.utils.register_class(GM_OT_CustomDraw)
    bpy.app.handlers.load_post.append(load_handler)
    bpy.app.handlers.depsgraph_update_post.append(depsgraph_update_handler)


# アドオン解除処理: ハンドラの削除とオペレータの登録解除を行う
def unregister():
    bpy.app.handlers.depsgraph_update_post.remove(depsgraph_update_handler)
    bpy.app.handlers.load_post.remove(load_handler)
    bpy.utils.unregister_class(GM_OT_CustomDraw)

