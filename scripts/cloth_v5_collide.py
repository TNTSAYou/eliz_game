"""v5 cloth layer: single-surface proxy -> headless Cloth bake -> fold fields
-> relative shape keys on the suit shell.

The proxy spans chest (z=1.25) to below the floor, with a body collider that
holds the suit silhouette.  The run's bounce is simulated in the suit's frame
by moving the floor collider; the body collider sways sideways with the run.

v5.2 (KI-01): the legs and shoes are colliders too, the run action is looped
during the bake, and every sampled frame is additionally projected out of the
shoes/legs.  The collision solve gives a natural drape; the projection
guarantees the fabric is never left inside a limb.
"""
import math

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

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
KEY_FRAMES = tuple(range(1, CYCLE + 1, 2))  # 12 keys, one every other frame
SIM_KEY_FRAMES = tuple(SETTLE + CYCLE * (CYCLES - 1) + f for f in KEY_FRAMES)
IDLE_FRAME = 31                            # settled, floor at rest, symmetric stance

# collision push-out: the field must keep a 20 cm shoebox bulge, so the clamp is
# far above a fold.  Small displacements still get the old 1.8x fold gain.
RAD_CLAMP = 0.30
RAD_IN_CLAMP = -0.05
Z_CLAMP = 0.12
FOLD_GAIN = 0.8
GAIN_SCALE = 0.05
PROJECT_MARGIN = 0.032

# objects the coat has to stay outside of
LIMB_COLLIDERS = ("INNER_Leg_L", "INNER_Leg_R", "DUCKSHOE_L", "DUCKSHOE_R")


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


def enable_limb_colliders():
    """Let the solver actually see the legs and shoes (KI-01)."""
    for name in LIMB_COLLIDERS:
        obj = bpy.data.objects.get(name)
        if obj is None:
            continue
        if obj.modifiers.get("Collision") is None:
            obj.modifiers.new("Collision", "COLLISION")
        obj.collision.thickness_outer = 0.012
        obj.collision.cloth_friction = 6.0


def start_run_loop(rig):
    """Loop the run action across the whole bake (fcurves stop at frame 25)."""
    act = bpy.data.actions["run"]
    ad = rig.animation_data or rig.animation_data_create()
    ad.action = act
    slots = list(getattr(act, "slots", []))
    if slots and hasattr(ad, "action_slot"):
        ad.action_slot = slots[0]
    for fc in act.fcurves:
        if not any(m.type == "CYCLES" for m in fc.modifiers):
            fc.modifiers.new("CYCLES")


def stop_run_loop(rig):
    act = bpy.data.actions.get("run")
    if act:
        for fc in act.fcurves:
            for m in list(fc.modifiers):
                if m.type == "CYCLES":
                    fc.modifiers.remove(m)
    ad = rig.animation_data
    if ad:
        ad.action = None
    B.reset_pose(rig)


def _collider_bvhs(dg):
    """BVH per limb + its outward sign (some lathed meshes wind inward)."""
    bvhs = []
    points = []
    for name in LIMB_COLLIDERS:
        obj = bpy.data.objects.get(name)
        if obj is None:
            continue
        ev = obj.evaluated_get(dg)
        me = ev.to_mesh()
        mw = ev.matrix_world
        verts = [mw @ v.co for v in me.vertices]
        polys = [tuple(p.vertices) for p in me.polygons]
        if not verts or not polys:
            ev.to_mesh_clear()
            continue
        points.extend(verts)
        center = sum(verts, Vector()) / len(verts)
        rot = mw.to_3x3()
        vote = 0
        for poly in me.polygons:
            n = (rot @ poly.normal).normalized()
            vote += 1 if ((mw @ poly.center) - center).dot(n) > 0 else -1
        sign = 1.0 if vote >= 0 else -1.0
        bvhs.append((BVHTree.FromPolygons(verts, polys, all_triangles=False), sign))
        ev.to_mesh_clear()
    return bvhs, points


def _bone_matrices(rig):
    """pose-bone skinning matrix in armature space, per bone."""
    return {pb.name: pb.matrix @ pb.bone.matrix_local.inverted()
            for pb in rig.pose.bones}


def _rest_weights(obj):
    names = [g.name for g in obj.vertex_groups]
    out = []
    for v in obj.data.vertices:
        out.append([(names[g.group], g.weight) for g in v.groups if g.weight > 1e-4])
    return out


def project_shell(shell, rig, key, frame, weights, margin=0.018,
                  iterations=3, zmax=0.35):
    """Push the actual shell vertices out of the limbs, in rest space.

    The proxy -> (z, theta) field loses a local shoe bulge; this pass works on
    the evaluated shell instead.  A world-space push is converted back with the
    vertex's blended skinning matrix, so the shape key stays a valid rest-space
    displacement.  Two corrections are combined: "inside the shoe" and "inside
    the shoe's back-half swept radius" (the shoe can already be outside the
    cloth, in which case the first test never fires).
    """
    scene = bpy.context.scene
    rest = [v.co.copy() for v in shell.data.vertices]
    edges = [(e.vertices[0], e.vertices[1]) for e in shell.data.edges]
    count = len(rest)
    total = 0
    for _ in range(iterations):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        ev = shell.evaluated_get(dg)
        me = ev.to_mesh()
        world = [ev.matrix_world @ v.co for v in me.vertices]
        ev.to_mesh_clear()
        bvhs, limb_pts = _collider_bvhs(dg)
        mats = _bone_matrices(rig)

        pushes = [None] * count
        for i, p in enumerate(world):
            # the free bottom edge has no neighbours to relax into; moving it
            # tears the hem, so leave the last couple of centimetres alone
            if p.z > zmax or p.z < 0.015:
                continue
            best = None
            for bvh, sign in bvhs:
                loc, nor, _idx, dist = bvh.find_nearest(p, 0.6)
                if loc is None:
                    continue
                if (p - loc).dot(nor) * sign < 0.0 and (best is None or dist > best[0]):
                    best = (dist, loc, nor, sign)
            if best is not None:
                _d, loc, nor, sign = best
                pushes[i] = (loc + nor * (margin * sign)) - p

        cleared, _moved = radial_clearance(world, limb_pts, margin=margin,
                                           zmax=zmax)
        for i, p in enumerate(world):
            d = cleared[i] - p
            if d.length > 1e-6:
                pushes[i] = d if pushes[i] is None else pushes[i] + d

        # A push that lifts the hem tears its free edge: bias it horizontal and
        # cap it, then relax it over the neighbourhood.
        for i in range(count):
            if pushes[i] is None:
                continue
            push = pushes[i]
            push.z = min(max(push.z, -0.01), 0.03)
            if push.length > 0.10:
                push = push.normalized() * 0.10
            pushes[i] = push

        for _ in range(3):
            acc = [Vector((0.0, 0.0, 0.0)) for _ in range(count)]
            cnt = [0] * count
            for a, b in edges:
                if pushes[a] is not None:
                    acc[b] += pushes[a]
                    cnt[b] += 1
                if pushes[b] is not None:
                    acc[a] += pushes[b]
                    cnt[a] += 1
            for i in range(count):
                if cnt[i]:
                    avg = acc[i] / cnt[i]
                    pushes[i] = avg if pushes[i] is None else pushes[i] * 0.5 + avg * 0.5

        pushed = 0
        for i, push in enumerate(pushes):
            if push is None or push.length < 1e-5 or not weights[i]:
                continue
            M = Matrix.Identity(4) * 0.0
            for b, w in weights[i]:
                M += mats[b] * w
            try:
                local = M.to_3x3().inverted() @ push
            except ValueError:
                continue
            key.data[i].co = rest[i] + (key.data[i].co - rest[i]) + local
            pushed += 1
        total += pushed
        if pushed == 0:
            break
    return total


def radial_clearance(points, limb_points, margin=PROJECT_MARGIN, zmax=0.5,
                     ymin=0.0, dz=0.02, nslices=72, spread=2):
    """Keep the back of the coat outside the shoe's swept silhouette.

    Once the shoe has passed through the wall, the "inside the shoe" test no
    longer fires (the shoe is outside the cloth), so the cloth is pushed to at
    least the limb's radius in that (z, angle) bin plus the margin.
    """
    grid = {}
    for p in limb_points:
        if p.z > zmax or p.y < ymin:
            continue
        r = math.hypot(p.x, p.y)
        iz = int(max(0.0, p.z) / dz)
        ia = int((math.atan2(p.y, p.x) + math.pi) / (2.0 * math.pi) * nslices) % nslices
        key = (iz, ia)
        if r > grid.get(key, 0.0):
            grid[key] = r

    need = {}
    for (iz, ia), r in grid.items():
        for di in (-1, 0, 1):
            for da in range(-spread, spread + 1):
                k = (max(0, iz + di), (ia + da) % nslices)
                if r > need.get(k, 0.0):
                    need[k] = r

    out = []
    moved = 0
    for p in points:
        if p.z > zmax or p.y < ymin:
            out.append(p)
            continue
        r = math.hypot(p.x, p.y)
        if r < 1e-4:
            out.append(p)
            continue
        iz = int(max(0.0, p.z) / dz)
        ia = int((math.atan2(p.y, p.x) + math.pi) / (2.0 * math.pi) * nslices) % nslices
        req = need.get((iz, ia), 0.0)
        if req and r < req + margin:
            s = (req + margin) / r
            out.append(Vector((p.x * s, p.y * s, p.z)))
            moved += 1
        else:
            out.append(p)
    return out, moved


def project_out(rest, edges, bvhs, margin=PROJECT_MARGIN, iterations=3,
                smooth_passes=2):
    """Push proxy vertices out of the limbs, then relax the push ring-wise.

    Returns (corrected points, number of vertices that had to move).
    """
    count = len(rest)
    disp = [Vector((0.0, 0.0, 0.0)) for _ in range(count)]
    total = 0
    for _ in range(iterations):
        hits = 0
        for i in range(count):
            p = rest[i] + disp[i]
            best = None
            for bvh, sign in bvhs:
                loc, nor, _idx, dist = bvh.find_nearest(p, 0.6)
                if loc is None:
                    continue
                inside = (p - loc).dot(nor) * sign < 0.0
                if inside and (best is None or dist > best[0]):
                    best = (dist, loc, nor, sign)
            if best is None:
                continue
            _dist, loc, nor, sign = best
            d = (loc + nor * (margin * sign)) - p
            if d.length > 1e-6:
                disp[i] += d
                hits += 1
        total += hits
        if hits == 0:
            break
        for _ in range(smooth_passes):
            acc = [Vector((0.0, 0.0, 0.0)) for _ in range(count)]
            cnt = [0] * count
            for a, b in edges:
                acc[a] += disp[b]
                cnt[a] += 1
                acc[b] += disp[a]
                cnt[b] += 1
            for i in range(count):
                if cnt[i]:
                    disp[i] = disp[i] * 0.5 + (acc[i] / cnt[i]) * 0.5
    return [rest[i] + disp[i] for i in range(count)], total


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
    cs.distance_min = 0.010
    cs.collision_quality = 3
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
        self.edges = [tuple(e.vertices) for e in proxy.data.edges]
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

        # KI-01: physics alone leaves the shoebox ~6 cm outside the cloth, so
        # every sampled frame is projected out of the limbs as a hard guarantee.
        bvhs, limb_pts = _collider_bvhs(dg)
        if bvhs:
            sim, pushed = project_out(sim, self.edges, bvhs)
            sim, cleared = radial_clearance(sim, limb_pts)
            if pushed or cleared:
                print(f"  fold f{frame}: inside={pushed} cleared={cleared}")

        for ring in range(RINGS):
            for j in range(SEG):
                i = ring * SEG + j
                p = self.rest[i]
                rad = Vector((p.x, p.y / B.DEPTH_RATIO, 0.0)).normalized()
                d = sim[i] - p
                self.dr[ring][j] = d.dot(rad)
                self.dz[ring][j] = d.z
        # v5.2: no ring-mean removal and no angular blur.  A shoe push is a
        # local bulge; averaging it around the ring is what flattened it before.
        for _ in range(0):
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


def bake_shape_keys(shell, field, frames, rig):
    me = shell.data
    if me.shape_keys is None:
        shell.shape_key_add(name="Basis", from_mix=False)
    weights = _rest_weights(shell)
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
            fade_sleeve = 1.0 - B._smoothstep((side - B.body_r(co.z) * 0.99) / 0.10)
            top = 1.0 - B._smoothstep((co.z - 1.12) / 0.13)
            hem = 1.0
            mask = fade_sleeve * top * hem
            if mask <= 1e-4:
                continue
            a, c = field.sample(co.z, math.atan2(co.y / B.DEPTH_RATIO, co.x))
            # keep the old fold gain for small displacements, but let a real
            # collision push (shoe) through without amplifying it
            gain = 1.0 + FOLD_GAIN / (1.0 + (a / GAIN_SCALE) ** 2)
            a = max(RAD_IN_CLAMP, min(RAD_CLAMP, a * gain * mask))
            c = max(-Z_CLAMP, min(Z_CLAMP, c * gain * mask))
            rad = Vector((co.x, co.y / B.DEPTH_RATIO, 0.0))
            if rad.length < 1e-6:
                continue
            rad.normalize()
            key.data[v.index].co = co + rad * a + Vector((0.0, 0.0, c))
            moved += 1
        # last mile: the transferred bulge is lossy, so the real shell is
        # pushed out of the shoes/legs in rest space as well (guaranteed)
        for k in keys:
            k.value = 0.0
        key.value = 1.0
        fixed = project_shell(shell, rig, key, frame, weights)
        key.value = 0.0
        print(f"fold key {frame}: {moved} verts, collision-fixed {fixed}")
        keys.append(key)
    return keys


def make_morph_action(shell, name, keys, weights_by_frame):
    ks = shell.data.shape_keys
    ad = ks.animation_data_create()
    ad.action = bpy.data.actions.new(name)
    for f, weights in weights_by_frame:
        for key, w in zip(keys, weights):
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


def setup_morph_actions(shell, run_keys, idle_key):
    all_keys = [k for k in shell.data.shape_keys.key_blocks
                if k.name.startswith("fold_")]
    for k in all_keys:
        k.value = 0.0

    def full(values):
        return [values.get(k.name, 0.0) for k in all_keys]

    run_frames = [(f, full({k.name: w for k, w in zip(run_keys, run_weights(f))}))
                  for f in range(1, 26)]
    # idle uses its own settled key: key 0 of the run is the contact pose, whose
    # shoe bulge would otherwise sit on the coat at rest
    idle_w = full({idle_key.name: 1.0})
    idle_frames = [(1, idle_w), (30, idle_w), (60, idle_w)]
    run_act = make_morph_action(shell, "run_morph", all_keys, run_frames)
    idle_act = make_morph_action(shell, "idle_morph", all_keys, idle_frames)
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


def build(coll, shell, rig):
    proxy = build_proxy(coll)
    body = build_body_collider(coll)
    floor = build_floor(coll)
    enable_limb_colliders()
    mod = setup_cloth(proxy)
    animate_run(floor, body)
    start_run_loop(rig)
    print("cloth: baking", SIM_END, "frames with leg/shoe colliders ...")
    bake(proxy, mod)
    field = FoldField(proxy)
    # frame 31: settled, floor at rest, both feet under the body -> idle drape
    idle_key = bake_shape_keys(shell, field, (IDLE_FRAME,), rig)[0]
    run_keys = bake_shape_keys(shell, field, SIM_KEY_FRAMES, rig)
    stop_run_loop(rig)
    idle_act, run_act = setup_morph_actions(shell, run_keys, idle_key)
    stash_morph_nla(shell, idle_act, run_act)
    return {"proxy": proxy, "body": body, "floor": floor,
            "keys": [idle_key] + list(run_keys),
            "idle_act": idle_act, "run_act": run_act}
