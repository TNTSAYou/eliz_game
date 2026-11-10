import * as THREE from "three";

/** 可复现的伪随机，保证每次刷新场景布局一致。 */
function mulberry32(seed) {
  return function () {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function createWorld(scene) {
  scene.background = new THREE.Color("#e8ecef");
  scene.fog = new THREE.Fog("#e8ecef", 30, 110);

  // ---- 天空：竖直渐变的天穹，比纯色背景更有空间感 ----
  const skyGeo = new THREE.SphereGeometry(120, 64, 40);
  const skyPos = skyGeo.attributes.position;
  const skyColors = new Float32Array(skyPos.count * 3);
  const cTop = new THREE.Color("#c2d2e6");
  const cBottom = new THREE.Color("#e8ecef");
  const cTmp = new THREE.Color();
  for (let i = 0; i < skyPos.count; i++) {
    // 地平线处正好等于雾色，往上立刻开始渐变，避免出现一条平的亮带
    const t = THREE.MathUtils.smoothstep(skyPos.getY(i) / 120, 0.0, 0.95);
    cTmp.copy(cBottom).lerp(cTop, t);
    skyColors[i * 3] = cTmp.r;
    skyColors[i * 3 + 1] = cTmp.g;
    skyColors[i * 3 + 2] = cTmp.b;
  }
  skyGeo.setAttribute("color", new THREE.BufferAttribute(skyColors, 3));
  const sky = new THREE.Mesh(
    skyGeo,
    new THREE.MeshBasicMaterial({
      vertexColors: true,
      side: THREE.BackSide,
      fog: false,
      depthWrite: false,
      // 雾色是直接混到输出空间的；天穹若走 ACES 就会和地平线差出一截灰阶
      toneMapped: false,
    }),
  );
  sky.frustumCulled = false;
  scene.add(sky);

  // ---- 灯光：暖主光 + 冷补光 + 冷边缘光，白衣服才不会糊成一片 ----
  const hemi = new THREE.HemisphereLight("#eef5ff", "#b8ab98", 0.85);
  scene.add(hemi);

  const sun = new THREE.DirectionalLight("#fff2dd", 2.5);
  sun.position.set(5, 9, 6);
  sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  sun.shadow.camera.left = -9;
  sun.shadow.camera.right = 9;
  sun.shadow.camera.top = 9;
  sun.shadow.camera.bottom = -9;
  sun.shadow.camera.near = 0.5;
  sun.shadow.camera.far = 40;
  sun.shadow.bias = -0.0008;
  sun.shadow.normalBias = 0.06;
  scene.add(sun, sun.target);

  const rim = new THREE.DirectionalLight("#c9dcff", 1.1);
  rim.position.set(-7, 5, -6);
  scene.add(rim);

  const fill = new THREE.DirectionalLight("#ffffff", 0.35);
  fill.position.set(-2, 3, 8);
  scene.add(fill);

  // ---- 地面 ----
  const ground = new THREE.Mesh(
    new THREE.PlaneGeometry(400, 400),
    // Lambert 没有镜面项：掠射角不会在地平线附近堆出一条亮带
    new THREE.MeshLambertMaterial({ color: "#e7e2d6" }),
  );
  ground.rotation.x = -Math.PI / 2;
  ground.receiveShadow = true;
  scene.add(ground);

  const grid = new THREE.GridHelper(120, 120, "#c5bead", "#d9d3c4");
  grid.position.y = 0.004;
  grid.material.transparent = true;
  grid.material.opacity = 0.55;
  scene.add(grid);

  // ---- 参照物：石头与树，给移动提供视差 ----
  const rand = mulberry32(20261110);
  const stoneColors = ["#cdd6d0", "#d8d0c2", "#c6d0da", "#d9cfd2"];
  const stoneGeo = new THREE.DodecahedronGeometry(1, 0);
  const stones = new THREE.Group();
  const tmp = new THREE.Object3D();

  for (let i = 0; i < 16; i++) {
    const angle = rand() * Math.PI * 2;
    const radius = 5.5 + rand() * 14;
    const scale = 0.22 + rand() * 0.42;
    tmp.position.set(Math.cos(angle) * radius, scale * 0.55, Math.sin(angle) * radius);
    tmp.rotation.set(rand() * 0.6, rand() * Math.PI, rand() * 0.5);
    tmp.scale.set(scale * (0.8 + rand() * 0.5), scale * (0.5 + rand() * 0.4), scale);
    tmp.updateMatrix();
    const mesh = new THREE.Mesh(
      stoneGeo,
      new THREE.MeshStandardMaterial({
        color: stoneColors[i % stoneColors.length],
        roughness: 0.92,
        metalness: 0,
      }),
    );
    mesh.matrix.copy(tmp.matrix);
    mesh.matrixAutoUpdate = false;
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    stones.add(mesh);
  }
  scene.add(stones);

  const trees = new THREE.Group();
  const trunkGeo = new THREE.CylinderGeometry(0.09, 0.13, 1.5, 7);
  const crownGeo = new THREE.IcosahedronGeometry(0.85, 0);
  const trunkMat = new THREE.MeshStandardMaterial({ color: "#a99a86", roughness: 0.95 });
  const crownMat = new THREE.MeshStandardMaterial({ color: "#a8b8a2", roughness: 0.95 });

  for (let i = 0; i < 5; i++) {
    const angle = (i / 5) * Math.PI * 2 + 0.7;
    const radius = 11 + rand() * 6;
    const tree = new THREE.Group();
    const trunk = new THREE.Mesh(trunkGeo, trunkMat);
    trunk.position.y = 0.75;
    const crown = new THREE.Mesh(crownGeo, crownMat);
    crown.position.y = 1.95;
    crown.scale.set(1, 1.05, 1);
    for (const m of [trunk, crown]) {
      m.castShadow = true;
      m.receiveShadow = true;
      tree.add(m);
    }
    tree.position.set(Math.cos(angle) * radius, 0, Math.sin(angle) * radius);
    tree.rotation.y = rand() * Math.PI;
    trees.add(tree);
  }
  scene.add(trees);

  const sunOffset = new THREE.Vector3(5, 9, 6);

  return {
    sun,
    /** 主光跟着角色走，阴影贴图始终覆盖角色附近。 */
    update(pos) {
      sun.position.set(pos.x + sunOffset.x, sunOffset.y, pos.z + sunOffset.z);
      sun.target.position.set(pos.x, 0, pos.z);
      sun.target.updateMatrixWorld();
    },
  };
}
