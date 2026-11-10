"""v5 cloth layer: single-surface proxy -> headless Cloth bake -> fold fields
-> relative shape keys on the suit shell.

The proxy spans chest (z=1.25) to below the floor, with a body collider that
holds the suit silhouette.  The run's bounce is simulated in the suit's frame
by moving the floor collider; the body collider sways sideways with the run.

NOTE (KI-01): the legs/shoes are NOT colliders and are not simulated.  A
zero-poke-through variant lives in ``cloth_v5_collide.py`` (adds animated limb
colliders + a per-vertex push-out); it reaches 0 penetration but visibly tears
the double-walled hem, so it is not wired into the build.  See
docs/KNOWN_ISSUES.md.
"""
import math

import bpy
from mathutils import Vector

import build_eliz_v2 as B

SEG = 128
RINGS = 40
Z_TOP = 1.25
Z_BOT = -0.06
PIN_ROWS = 1
SETTLE = 48
CYCLE = 24
CYCLES = 3
SIM_END = SETTLE + CYCLE * CYCLES          # 120
KEY_FRAMES = (1, 4, 7, 10, 13, 16, 19, 22)
SIM_KEY_FRAMES = tuple(SETTLE + CYCLE * (CYCLES - 1) + f for f in KEY_FRAMES)

RAD_CLAMP = 0.060
Z_CLAMP = 0.030
SCALE = 1.8


def _slack(z):
    """Chest is nearly fitted; the skirt keeps 22% extra circumference."""
    return 1.055 + 0.165 * B._smoothstep((0.95 - z) / 0.55)


def build_proxy(coll):
    zs = [Z_TOP - (Z_TOP - Z_BOT) * (i / (RINGS - 1)) ** 1.12 for i in range(RINGS)]
    verts, faces = [], []
    for z in zs:
        r0 = B.body_r(z) * _slack(z)
        for j in range(SEG):
            a = 2.0 * math.pi * j / SEG
            # flutes break the axisymmetry and seed drape folds
            amp = 0.028 + 0.012 * B._smoothstep((0.95 - z) / 0.4)
            r = r0 * (1.0 + amp * math.sin(a * 10.0 + 0.7)
                      + 0.45 * amp * math.sin(a * 17.0 + 2.1))
            verts.append((r * math.cos(a), r * B.DEPTH_RATIO * math.sin(a), z))
    for i in range(RINGS - 1):
        for j in range(SEG):
            a0 = i * SEG + j
            a1 = i * SEG + (j + 1) % SEG
            b0 = (i + 1) * SEG + j
            b1 = (i + 1) * SEG + (j + 1) % SEG
            faces.append((a0, a1, b1, b0))
    me = bpy.data.meshes.new("CLOTH_Proxy")
    me.from_pydata(verts, [], faces)
    me.update()
    obj = bpy.data.objects.new("CLOTH_Proxy", me)
    coll.objects.link(obj)
    vg = obj.vertex_groups.new(name="PIN")
    vg.add(list(range(SEG * PIN_ROWS)), 1.0, "REPLACE")
    for p in me.polygons:
        p.use_smooth = True
    obj.hide_render = True
    return obj


def build_body_collider(coll):
    zs = [0.0, 0.12, 0.25, 0.40, 0.55, 0.70, 0.85, 1.00, 1.10, 1.18, 1.24, 1.28]
    profile = [(0.0, 0.0)] + [(B.body_r(z) * 0.955, z) for z in zs] + [(0.0, 1.28)]
    verts, faces = B._revolve(profile, 96)
    me = bpy.data.meshes.new("CLOTH_Body")
    me.from_pydata(verts, [], faces)
    me.update()
    obj = bpy.data.objects.new("CLOTH_Body", me)
    coll.objects.link(obj)
    B.recalc_normals(obj)
    col = obj.modifiers.new("Collision", "COLLISION")
    obj.collision.thickness_outer = 0.012
    obj.collision.cloth_friction = 6.0
    obj.hide_render = True
    return obj


def build_floor(coll):
    bpy.ops.mesh.primitive_plane_add(size=6.0, location=(0.0, 0.0, 0.0))
    obj = bpy.context.active_object
    obj.name = "CLOTH_Floor"
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    coll.objects.link(obj)
    obj.modifiers.new("Collision", "COLLISION")
    obj.collision.thickness_outer = 0.01
    obj.collision.cloth_friction = 8.0
    obj.hide_render = True
    return obj


def setup_cloth(proxy):
    mod = proxy.modifiers.new("Cloth", "CLOTH")
    cl = mod.settings
    cl.quality = 10
    cl.mass = 0.08
    cl.air_damping = 1.2
    cl.tension_stiffness = 4.0
    cl.compression_stiffness = 4.0
    cl.shear_stiffness = 1.5
    cl.bending_stiffness = 0.08
    cl.tension_damping = 5.0
    cl.compression_damping = 5.0
    cl.shear_damping = 5.0
    cl.bending_damping = 0.4
    cl.vertex_group_mass = "PIN"       # RNA name: Pin Vertex Group
    cl.pin_stiffness = 1.0
    cs = mod.collision_settings
    cs.use_collision = True
    cs.distance_min = 0.012
    cs.collision_quality = 2
    cs.use_self_collision = False
    return mod


def animate_run(floor, body):
    """Floor = run bounce in the suit frame; body = lateral weight shift."""
    for f in range(1, SIM_END + 1):
        if f <= SETTLE:
            fz, bx = 0.0, 0.0
        else:
            k = f - SETTLE
            ff = ((k - 1 + 9) % CYCLE) + 1       # start at the airborne frame
            ramp = B._smoothstep((k - 1) / 12.0)
            fz = 1.5 * (0.090 - B.run_lift(ff)) * ramp
            bx = 0.020 * math.sin(2.0 * math.pi * (ff - 1) / CYCLE) * ramp
        floor.location.z = fz
        floor.keyframe_insert("location", frame=f)
        body.location.x = bx
        body.keyframe_insert("location", frame=f)


def bake(proxy, mod):
    mod.point_cache.frame_start = 1
    mod.point_cache.frame_end = SIM_END
    with bpy.context.temp_override(scene=bpy.context.scene, active_object=proxy,
                                   object=proxy, point_cache=mod.point_cache):
        bpy.ops.ptcache.bake(bake=True)
    if not mod.point_cache.is_baked:
        raise RuntimeError("cloth bake failed")


class FoldField:
    """Radial/vertical fold field sampled on (z, theta), ring mean removed."""

    def __init__(self, proxy):
        self.proxy = proxy
        self.rest = [v.co.copy() for v in proxy.data.vertices]
        self.dr = [[0.0] * SEG for _ in range(RINGS)]
        self.dz = [[0.0] * SEG for _ in range(RINGS)]
        self.ring_z = [sum(self.rest[r * SEG + j].z for j in range(SEG)) / SEG
                       for r in range(RINGS)]

    def at(self, frame):
        scene = bpy.context.scene
        scene.frame_set(frame)
        dg = bpy.context.evaluated_depsgraph_get()
        ev = self.proxy.evaluated_get(dg)
        me = ev.to_mesh()
        if len(me.vertices) != len(self.rest):
            ev.to_mesh_clear()
            raise RuntimeError("proxy vertex count changed")
        sim = [v.co.copy() for v in me.vertices]
        ev.to_mesh_clear()

        for ring in range(RINGS):
            for j in range(SEG):
                i = ring * SEG + j
                p = self.rest[i]
                rad = Vector((p.x, p.y / B.DEPTH_RATIO, 0.0)).normalized()
                d = sim[i] - p
                self.dr[ring][j] = d.dot(rad)
                self.dz[ring][j] = d.z
        for ring in range(RINGS):
            mr = sum(self.dr[ring]) / SEG
            mz = sum(self.dz[ring]) / SEG
            self.dr[ring] = [v - mr for v in self.dr[ring]]
            self.dz[ring] = [v - mz for v in self.dz[ring]]
        for _ in range(1):
            for ring in range(RINGS):
                a = self.dr[ring][:]
                b = self.dz[ring][:]
                for j in range(SEG):
                    self.dr[ring][j] = 0.25 * a[j - 1] + 0.5 * a[j] + 0.25 * a[(j + 1) % SEG]
                    self.dz[ring][j] = 0.25 * b[j - 1] + 0.5 * b[j] + 0.25 * b[(j + 1) % SEG]

    def sample(self, z, theta):
        if z >= self.ring_z[0]:
            r0 = r1 = 0
            t = 0.0
        elif z <= self.ring_z[-1]:
            r0 = r1 = RINGS - 1
            t = 0.0
        else:
            r0 = 0
            for r in range(RINGS - 1):
                if self.ring_z[r] >= z >= self.ring_z[r + 1]:
                    r0, r1 = r, r + 1
                    break
            span = self.ring_z[r0] - self.ring_z[r1]
            t = (self.ring_z[r0] - z) / span if span > 1e-6 else 0.0
        u = (theta / (2.0 * math.pi)) % 1.0 * SEG
        j0 = int(math.floor(u)) % SEG
        j1 = (j0 + 1) % SEG
        f = u - math.floor(u)
        a0 = self.dr[r0][j0] * (1 - f) + self.dr[r0][j1] * f
        a1 = self.dr[r1][j0] * (1 - f) + self.dr[r1][j1] * f
        c0 = self.dz[r0][j0] * (1 - f) + self.dz[r0][j1] * f
        c1 = self.dz[r1][j0] * (1 - f) + self.dz[r1][j1] * f
        return a0 * (1 - t) + a1 * t, c0 * (1 - t) + c1 * t


def bake_shape_keys(shell, field, frames):
    me = shell.data
    if me.shape_keys is None:
        shell.shape_key_add(name="Basis", from_mix=False)
    keys = []
    for frame in frames:
        field.at(frame)
        key = shell.shape_key_add(name=f"fold_{frame:03d}", from_mix=False)
        key.value = 0.0
        moved = 0
        for v in me.vertices:
            co = v.co
            key.data[v.index].co = co
            if co.z > Z_TOP or co.z < 0.0:
                continue
            # fade under the sleeves / armholes so the shell stays attached
            side = abs(co.x)
            if side > B.body_r(co.z) * 1.10:
                continue
            fade_sleeve = 1.0 - B._smoothstep((side - B.body_r(co.z) * 0.94) / 0.09)
            top = 1.0 - B._smoothstep((co.z - 1.12) / 0.13)
            hem = B._smoothstep((co.z - 0.025) / 0.05)
            mask = fade_sleeve * top * hem
            if mask <= 1e-4:
                continue
            a, c = field.sample(co.z, math.atan2(co.y / B.DEPTH_RATIO, co.x))
            # inward folds are capped: a deep valley can reach the hairy leg or
            # the crotch hair, outward ridges keep the full amplitude
            a = max(-0.015, min(RAD_CLAMP, a * SCALE * mask))
            c = max(-Z_CLAMP, min(Z_CLAMP, c * SCALE * mask))
            rad = Vector((co.x, co.y / B.DEPTH_RATIO, 0.0))
            if rad.length < 1e-6:
                continue
            rad.normalize()
            key.data[v.index].co = co + rad * a + Vector((0.0, 0.0, c))
            moved += 1
        print(f"fold key {frame}: {moved} verts")
        keys.append(key)
    return keys


def make_morph_action(shell, name, weights_by_frame):
    ks = shell.data.shape_keys
    ad = ks.animation_data_create()
    ad.action = bpy.data.actions.new(name)
    for f, weights in weights_by_frame:
        for key, w in zip([k for k in ks.key_blocks if k.name.startswith("fold_")], weights):
            key.value = w
            key.keyframe_insert("value", frame=f)
    act = ad.action
    act.use_fake_user = True
    ad.action = None
    return act


def run_weights(f):
    phase = (f - 1) / 24.0 * len(KEY_FRAMES)
    i0 = int(math.floor(phase)) % len(KEY_FRAMES)
    i1 = (i0 + 1) % len(KEY_FRAMES)
    frac = phase - math.floor(phase)
    w = [0.0] * len(KEY_FRAMES)
    w[i0] = 1.0 - frac
    w[i1] = frac
    return w


def setup_morph_actions(shell):
    run_frames = [(f, run_weights(f)) for f in range(1, 26)]
    # idle keeps the settled drape (key 0) instead of the bare base mesh, so the
    # coat is not a smooth balloon at rest; run frame 1 is the same key
    idle_w = [1.0] + [0.0] * (len(KEY_FRAMES) - 1)
    idle_frames = [(1, idle_w), (30, idle_w), (60, idle_w)]
    run_act = make_morph_action(shell, "run_morph", run_frames)
    idle_act = make_morph_action(shell, "idle_morph", idle_frames)
    return idle_act, run_act


def stash_morph_nla(shell, idle_act, run_act):
    ad = shell.data.shape_keys.animation_data_create()
    ad.action = None
    for t in list(ad.nla_tracks):
        ad.nla_tracks.remove(t)
    for act, name in ((idle_act, "idle"), (run_act, "run")):
        tr = ad.nla_tracks.new()
        tr.name = name
        tr.strips.new(name, 1, act)
    return ad


def build(coll, shell):
    proxy = build_proxy(coll)
    body = build_body_collider(coll)
    floor = build_floor(coll)
    mod = setup_cloth(proxy)
    animate_run(floor, body)
    print("cloth: baking", SIM_END, "frames ...")
    bake(proxy, mod)
    field = FoldField(proxy)
    keys = bake_shape_keys(shell, field, SIM_KEY_FRAMES)
    idle_act, run_act = setup_morph_actions(shell)
    stash_morph_nla(shell, idle_act, run_act)
    return {"proxy": proxy, "body": body, "floor": floor, "keys": keys,
            "idle_act": idle_act, "run_act": run_act}
