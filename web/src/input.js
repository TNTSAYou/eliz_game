/** 键盘输入：按住状态 + 本帧刚按下（用于一次性切换）。 */
export class Input {
  constructor() {
    this.keys = new Set();
    this.pressed = new Set();

    this.onKeyDown = (e) => {
      if (e.repeat) {
        if (this.isBrowserKey(e.code)) e.preventDefault();
        return;
      }
      this.keys.add(e.code);
      this.pressed.add(e.code);
      if (this.isBrowserKey(e.code)) e.preventDefault();
    };
    this.onKeyUp = (e) => {
      this.keys.delete(e.code);
    };
    this.onBlur = () => {
      this.keys.clear();
      this.pressed.clear();
    };

    window.addEventListener("keydown", this.onKeyDown, { passive: false });
    window.addEventListener("keyup", this.onKeyUp);
    window.addEventListener("blur", this.onBlur);
  }

  isBrowserKey(code) {
    return code === "Space" || code === "Tab" || code.startsWith("Arrow");
  }

  down(code) {
    return this.keys.has(code);
  }

  take(code) {
    const hit = this.pressed.has(code);
    this.pressed.delete(code);
    return hit;
  }

  /** x: 右为正；z: 前为正。 */
  axis() {
    const right = this.down("KeyD") || this.down("ArrowRight") ? 1 : 0;
    const left = this.down("KeyA") || this.down("ArrowLeft") ? 1 : 0;
    const fwd = this.down("KeyW") || this.down("ArrowUp") ? 1 : 0;
    const back = this.down("KeyS") || this.down("ArrowDown") ? 1 : 0;
    return { x: right - left, z: fwd - back };
  }

  get sprint() {
    return this.down("ShiftLeft") || this.down("ShiftRight");
  }

  endFrame() {
    this.pressed.clear();
  }
}
