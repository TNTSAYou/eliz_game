import * as THREE from "three";
import { createWorld } from "./world.js";
import { Character } from "./character.js";
import { FollowCamera } from "./cameraRig.js";
import { Input } from "./input.js";

const params = new URLSearchParams(location.search);
const assetBase = new URL("./assets/", document.baseURI).href;

if (params.get("hud") === "0") document.body.classList.add("no-hud");

const app = document.getElementById("app");
const loading = document.getElementById("loading");
const bar = document.getElementById("bar");
const pct = document.getElementById("pct");
const errBox = document.getElementById("error");
const errMsg = document.getElementById("err-msg");

window.addEventListener("error", (e) => fail(e.error ?? e.message));
window.addEventListener("unhandledrejection", (e) => fail(e.reason));

const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.02;
renderer.outputColorSpace = THREE.SRGBColorSpace;
app.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(44, window.innerWidth / window.innerHeight, 0.1, 220);

const world = createWorld(scene);
const input = new Input();
const follow = new FollowCamera(camera, renderer.domElement);
const character = new Character(scene);

const setProgress = (v) => {
  const p = Math.round(THREE.MathUtils.clamp(v, 0, 1) * 100);
  bar.style.width = `${p}%`;
  pct.textContent = `${p}%`;
};

function fail(err) {
  console.error(err);
  loading.classList.add("done");
  errMsg.textContent = String(err?.stack || err?.message || err);
  errBox.hidden = false;
}

function applyDebugParams() {
  const clip = params.get("clip");
  if (clip && character.actions[clip]) {
    character.freeze(clip, Number(params.get("t") ?? 0.2));
  }
  if (params.has("yaw")) follow.yaw = Number(params.get("yaw"));
  if (params.has("pitch")) follow.pitch = Number(params.get("pitch"));
  if (params.has("dist")) follow.distance = Number(params.get("dist"));
  if (params.has("yaw") || params.has("pitch") || params.has("dist")) {
    follow.snap(character.position);
  }
}

const clock = { last: performance.now() };
let fpsTime = 0;
let fpsFrames = 0;

function updateStats(dt) {
  fpsTime += dt;
  fpsFrames += 1;
  if (fpsTime < 0.35) return;
  const fps = Math.round(fpsFrames / fpsTime);
  const state = character.frozen ? "frozen" : character.moving ? "run" : "idle";
  const el = document.getElementById("state");
  el.textContent = state;
  el.dataset.state = state;
  // fps 只在 ?debug=1 时显示，正式页面不挂一个开发指标
  if (params.get("debug") === "1") {
    document.getElementById("fps").textContent = `${fps} fps`;
    const p = character.position;
    document.title = `pos ${p.x.toFixed(2)},${p.z.toFixed(2)} | ${state} | ${fps} fps`;
  }
  fpsTime = 0;
  fpsFrames = 0;
}

function holdKey(code) {
  window.dispatchEvent(new KeyboardEvent("keydown", { code, bubbles: true }));
}

async function boot() {
  try {
    await character.load(`${assetBase}eliz.glb`, setProgress);
  } catch (err) {
    fail(err);
    return;
  }

  setProgress(1);
  loading.classList.add("done");
  // CSS 过渡在无头/后台标签页里可能不推进，350ms 后直接摘掉，避免残留半透明遮罩
  setTimeout(() => {
    loading.style.display = "none";
  }, 450);
  applyDebugParams();
  follow.snap(character.position);

  // 端到端自测：?replay=1 按住 W（2 = W+Shift 冲刺，3 = A 左移）
  const replay = params.get("replay");
  if (replay) {
    const codes = replay === "2" ? ["KeyW", "ShiftLeft"] : replay === "3" ? ["KeyA"] : ["KeyW"];
    for (const code of codes) holdKey(code);
  }

  // 确定性自测：同步推进 N 个 1/60 s 步，不受无头 rAF 节流影响
  if (params.has("selftest")) {
    const steps = Number(params.get("selftest")) || 240;
    const hold = params.get("hold") || "KeyW";
    holdKey(hold);
    if (params.get("sprint") === "1") holdKey("ShiftLeft");
    for (let i = 0; i < steps; i++) {
      character.update(1 / 60, input, follow.yaw, true);
      follow.update(1 / 60, character.position, character.yaw, character.alignCamera);
    }
    world.update(character.position);
    renderer.render(scene, camera);
    const p = character.position;
    document.title =
      `selftest steps=${steps} pos=${p.x.toFixed(2)},${p.z.toFixed(2)} ` +
      `yaw=${character.yaw.toFixed(2)} speed=${character.speed.toFixed(2)} ` +
      `moving=${character.moving} clip=${character.current?.getClip().name}`;
    return;
  }

  renderer.setAnimationLoop(() => {
    const now = performance.now();
    const dt = Math.min((now - clock.last) / 1000, 0.05);
    clock.last = now;

    if (!character.frozen && input.take("KeyR")) {
      character.reset();
      follow.snap(character.position);
    }
    if (!character.frozen && input.take("KeyT")) character.toggleSign();

    character.update(dt, input, follow.yaw, !character.frozen);
    follow.update(dt, character.position, character.yaw, character.alignCamera);
    world.update(character.position);
    renderer.render(scene, camera);
    updateStats(dt);
    input.endFrame();
  });
}

window.addEventListener("resize", () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

window.__eliz = { character, follow, camera, renderer, scene, world };

boot();
