import * as THREE from "three";

const TAU = Math.PI * 2;
const wrapAngle = (a) => (((a + Math.PI) % TAU) + TAU) % TAU - Math.PI;

/**
 * 第三人称跟随相机：阻尼跟随 + 拖拽环绕 + 滚轮缩放。
 * 角色朝 +Z，所以"背后"是 yaw + PI。
 */
export class FollowCamera {
  constructor(camera, dom) {
    this.camera = camera;
    this.dom = dom;

    // 初始给一个能看到脸的左前方 3/4，第一次按 W 后会自动回到背后
    this.yaw = 0.75;
    this.pitch = 0.3;
    this.distance = 5.4;

    this.focus = new THREE.Vector3(0, 1.02, 0);
    this.userTimer = 0;
    this.dragging = false;
    this.lastX = 0;
    this.lastY = 0;

    this.dom.addEventListener("pointerdown", (e) => {
      this.dragging = true;
      this.lastX = e.clientX;
      this.lastY = e.clientY;
      this.dom.setPointerCapture(e.pointerId);
      this.markUser();
    });
    this.dom.addEventListener("pointermove", (e) => {
      if (!this.dragging) return;
      const dx = e.clientX - this.lastX;
      const dy = e.clientY - this.lastY;
      this.lastX = e.clientX;
      this.lastY = e.clientY;
      this.yaw -= dx * 0.0055;
      this.pitch = THREE.MathUtils.clamp(this.pitch + dy * 0.0035, 0.06, 1.15);
      this.markUser();
    });
    const stop = (e) => {
      this.dragging = false;
      if (e.pointerId !== undefined && this.dom.hasPointerCapture?.(e.pointerId)) {
        this.dom.releasePointerCapture(e.pointerId);
      }
    };
    this.dom.addEventListener("pointerup", stop);
    this.dom.addEventListener("pointercancel", stop);
    this.dom.addEventListener("pointerleave", stop);
    this.dom.addEventListener(
      "wheel",
      (e) => {
        e.preventDefault();
        this.distance = THREE.MathUtils.clamp(
          this.distance * Math.exp(e.deltaY * 0.0011),
          2.2,
          11,
        );
        this.markUser();
      },
      { passive: false },
    );
  }

  markUser() {
    this.userTimer = 1.6;
  }

  snap(pos) {
    this.focus.set(pos.x, 1.02, pos.z);
    this.placeCamera(1);
  }

  placeCamera(alpha = 1) {
    const cp = Math.cos(this.pitch);
    const offset = new THREE.Vector3(
      Math.sin(this.yaw) * cp,
      Math.sin(this.pitch),
      Math.cos(this.yaw) * cp,
    ).multiplyScalar(this.distance);
    const desired = this.focus.clone().add(offset);
    this.camera.position.lerp(desired, alpha);
    this.camera.lookAt(this.focus.x, this.focus.y + 0.12, this.focus.z);
  }

  update(dt, pos, playerYaw, moving) {
    this.userTimer = Math.max(0, this.userTimer - dt);

    this.focus.lerp(
      new THREE.Vector3(pos.x, 1.02, pos.z),
      1 - Math.exp(-9 * dt),
    );

    // 移动时缓缓回到角色背后；刚拖过视角就先别抢
    if (moving && this.userTimer <= 0) {
      const target = playerYaw + Math.PI;
      this.yaw += wrapAngle(target - this.yaw) * (1 - Math.exp(-2.4 * dt));
    }

    this.placeCamera(1 - Math.exp(-8 * dt));
  }
}
