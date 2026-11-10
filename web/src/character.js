import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

const TAU = Math.PI * 2;
const wrapAngle = (a) => (((a + Math.PI) % TAU) + TAU) % TAU - Math.PI;

/** 移动速度（m/s）。run 循环 0.833 s 两步，配合这个速度脚不容易滑。 */
export const BASE_SPEED = 2.45;
export const SPRINT_FACTOR = 1.32;
const ARENA_RADIUS = 26;

export class Character {
  constructor(scene) {
    this.root = new THREE.Group();
    this.root.name = "Player";
    scene.add(this.root);

    this.yaw = 0;
    this.speed = 0;
    this.moving = false;
    this.ready = false;
    this.frozen = false;
    this.current = null;
    this.actions = {};
    this.moveBasisYaw = 0;
    this.wasMoving = false;
  }

  get position() {
    return this.root.position;
  }

  async load(url, onProgress) {
    const loader = new GLTFLoader();
    const gltf = await loader.loadAsync(url, (e) => {
      if (onProgress && e.total) onProgress(Math.min(1, e.loaded / e.total));
    });

    this.model = gltf.scene;
    this.model.traverse((o) => {
      if (!o.isMesh) return;
      o.castShadow = true;
      o.receiveShadow = true;
      // 蒙皮网格的包围盒不随动画更新，关掉剔除防止转身时消失
      o.frustumCulled = false;
    });
    this.root.add(this.model);

    // 牌子目前是挂在 sign_socket 上的独立板子，跑动时悬在身侧很出戏，默认收起
    this.sign = this.model.getObjectByName("PROP_Sign") ?? null;
    if (this.sign) this.sign.visible = false;

    this.mixer = new THREE.AnimationMixer(this.model);
    const byName = Object.fromEntries(gltf.animations.map((c) => [c.name, c]));
    this.clips = byName;

    for (const name of ["idle", "run"]) {
      const clip = byName[name];
      if (!clip) throw new Error(`GLB 缺少动画 "${name}"`);
      const action = this.mixer.clipAction(clip);
      action.setLoop(THREE.LoopRepeat, Infinity);
      action.enabled = true;
      this.actions[name] = action;
    }

    this.actions.idle.play();
    this.current = this.actions.idle;
    this.ready = true;
    return gltf;
  }

  play(name, fade = 0.18) {
    const next = this.actions[name];
    if (!next || next === this.current) return;
    next.reset();
    next.setEffectiveTimeScale(next.timeScale || 1);
    next.setEffectiveWeight(1);
    next.fadeIn(fade).play();
    this.current.fadeOut(fade);
    this.current = next;
  }

  update(dt, input, camYaw, controlsEnabled = true) {
    if (!this.ready || this.frozen) return;

    const axis = controlsEnabled ? input.axis() : { x: 0, z: 0 };
    const moving = axis.x !== 0 || axis.z !== 0;
    // 只有纯前进时相机才自动回到背后；否则 A/D 横移会和相机自动跟随互相追成一个圈
    this.alignCamera = moving && axis.x === 0 && axis.z > 0;

    // 移动基准冻结在"开始移动"的那一帧：相机随后怎么转，都不改变这一步的方向，
    // 否则相机自动跟随会把 W 走成弧线
    if (moving && !this.wasMoving) this.moveBasisYaw = camYaw;
    if (!moving) this.moveBasisYaw = camYaw;
    this.wasMoving = moving;

    const targetSpeed = moving ? BASE_SPEED * (input.sprint ? SPRINT_FACTOR : 1) : 0;
    this.speed += (targetSpeed - this.speed) * (1 - Math.exp(-9 * dt));

    if (moving) {
      // 相机朝向为前，右方向由前向旋转 -90° 得到（用冻结的基准，不用实时相机）
      const fx = -Math.sin(this.moveBasisYaw);
      const fz = -Math.cos(this.moveBasisYaw);
      const rx = -fz;
      const rz = fx;
      let dx = fx * axis.z + rx * axis.x;
      let dz = fz * axis.z + rz * axis.x;
      const len = Math.hypot(dx, dz) || 1;
      dx /= len;
      dz /= len;

      // 模型面朝 +Z，所以目标偏航是 atan2(x, z)
      const targetYaw = Math.atan2(dx, dz);
      this.yaw += wrapAngle(targetYaw - this.yaw) * (1 - Math.exp(-14 * dt));

      this.root.position.x += dx * this.speed * dt;
      this.root.position.z += dz * this.speed * dt;

      const r = Math.hypot(this.root.position.x, this.root.position.z);
      if (r > ARENA_RADIUS) {
        this.root.position.x *= ARENA_RADIUS / r;
        this.root.position.z *= ARENA_RADIUS / r;
      }
    }

    this.root.rotation.y = this.yaw;
    this.moving = moving && this.speed > 0.05;

    if (this.moving) {
      this.play("run");
      this.actions.run.timeScale = THREE.MathUtils.clamp(this.speed / BASE_SPEED, 0.5, 1.7);
    } else if (this.speed < 0.15) {
      this.play("idle");
    }

    this.mixer.update(dt);
  }

  /** 调试/截图用：停在一个固定姿势。 */
  freeze(name, time) {
    const action = this.actions[name];
    if (!action) return;
    for (const a of Object.values(this.actions)) a.stop();
    action.reset().play();
    this.mixer.setTime(time);
    this.current = action;
    this.frozen = true;
  }

  reset() {
    this.root.position.set(0, 0, 0);
    this.yaw = 0;
    this.speed = 0;
    this.moving = false;
    this.wasMoving = false;
    this.root.rotation.y = 0;
  }

  toggleSign() {
    if (!this.sign) return false;
    this.sign.visible = !this.sign.visible;
    return this.sign.visible;
  }
}
