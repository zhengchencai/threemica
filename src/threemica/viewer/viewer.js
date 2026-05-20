// Report viewer — fsLR mid/inflated/sphere surface coloured by a scalar map.
// Hover shows Yale-696 parcel name + map value + NeuroQuery/NeuroSynth terms.
// Controls: drag to rotate, scroll or ←→ inflate/deflate, ↑↓ zoom,
// L lock, R reset, O opacity, M wireframe, F toggle hover.

// ── Colormaps ──────────────────────────────────────────────────────────────
const CMAPS = {
  plasma:   [[13,8,135],[84,2,163],[139,10,165],[185,50,137],[219,92,104],[244,136,73],[254,188,43],[240,249,33]],
  viridis:  [[68,1,84],[72,40,120],[62,83,160],[49,104,142],[38,130,142],[31,158,137],[53,183,121],[110,206,88],[181,222,43],[253,231,37]],
  inferno:  [[0,0,4],[40,11,84],[101,21,110],[159,42,99],[212,72,66],[245,125,21],[252,193,7],[252,255,164]],
  hot:      [[10,0,0],[128,0,0],[255,64,0],[255,178,0],[255,255,200],[255,255,255]],
  magma:    [[0,0,4],[28,16,68],[79,18,123],[129,37,129],[181,54,122],[229,89,100],[251,135,97],[254,194,140],[252,253,191]],
  cividis:  [[0,32,77],[0,67,100],[60,92,107],[107,116,118],[152,141,118],[199,168,107],[241,198,68],[253,232,37]],
  RdBu_r:   [[33,102,172],[67,147,195],[146,197,222],[209,229,240],[247,247,247],[253,219,199],[239,138,98],[178,24,43]],
  coolwarm: [[59,76,192],[98,130,234],[141,176,254],[184,208,249],[221,220,220],[249,196,184],[244,154,123],[220,100,66],[180,4,38]],
  spectral: [[94,79,162],[50,136,189],[102,194,165],[171,221,164],[230,245,152],[255,255,191],[254,224,139],[253,174,97],[244,109,67],[213,62,79],[158,1,66]],
  gray_r:   [[255,255,255],[0,0,0]],
};
const CMAP_CYCLE_POS = ['magma', 'viridis', 'gray_r'];
const CMAP_CYCLE_DIV = ['coolwarm', 'RdBu_r'];

let currentCmapPos = 'magma';
let currentCmapDiv = 'coolwarm';
let currentCmap = 'magma';

function cmapRGB(t, name) {
  const lut = CMAPS[name] || CMAPS.plasma;
  t = Math.max(0, Math.min(1, t));
  const s = t * (lut.length - 1);
  const i = Math.min(Math.floor(s), lut.length - 2);
  const f = s - i;
  return lut[i].map((a, k) => Math.round(a + f * (lut[i+1][k] - a)));
}
function drawColorbar() {
  const mapData = PAYLOAD.maps[activeMapIdx];
  const canvas = document.getElementById('colorbar-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const w = canvas.width, h = canvas.height;
  for (let y = 0; y < h; y++) {
    const [r,g,b] = cmapRGB(1 - y/(h-1), currentCmap);
    ctx.fillStyle = `rgb(${r},${g},${b})`;
    ctx.fillRect(0, y, w, 1);
  }
  const fmt = v => (Math.abs(v) < 10 ? v.toFixed(2) : v.toFixed(1));
  document.getElementById('cb-min').textContent = fmt(mapData.vmin);
  document.getElementById('cb-max').textContent = fmt(mapData.vmax);
  document.getElementById('colorbar-title').textContent = mapData.cb_label;
}

// ── State ────────────────────────────────────────────────────────────────
let sceneL, cameraL, rendererL, controlsL, meshL = null, wireL = null;
let sceneR, cameraR, rendererR, controlsR, meshR = null, wireR = null;
let viewLocked = true;
let lastMovedSide = 'L';
let cortexOpacity = 1.0;
let wireframeVisible = true;
const REDUCED_OPACITY = 0.30;

let morphT = 0.0;
let tooltipPinned = false;
let hoveredRoi = -1;
let hoveredVertexIdx = -1;
let hoverEnabled = false;    // 'Q' toggles the hover/click query system

// Leader-line state — tracks the picked vertex while the tooltip is pinned, so
// the line can be re-projected each frame as the cortex morphs and rotates.
let pinnedHostMesh = null;
let pinnedVertexIdx = -1;
let pinnedSide = null;       // 'L' | 'R'

const H_W = window.innerWidth / 2;
const H_H = window.innerHeight;
const CAM_DIST = 500;     // far enough that the whole mid surface fits with margin
const NO_PARCEL_RGB = [148, 148, 148];   // medium grey for unassigned vertices

const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();

let _downT = 0, _leftDown = false;

// ── Decoders ─────────────────────────────────────────────────────────────
function b64ToBytes(b64) {
  const bin = atob(b64);
  const u8 = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
  return u8;
}
const b64ToFloat32 = b => new Float32Array(b64ToBytes(b).buffer);
const b64ToUint32  = b => new Uint32Array(b64ToBytes(b).buffer);
const b64ToInt16   = b => new Int16Array(b64ToBytes(b).buffer);

// ── Decode mesh: 3 surface states per hemi, shared topology ──────────────
const SURFACE_KINDS = PAYLOAD.mesh.lh.surfaces.sphere ? ['mid','inflated','sphere'] : ['mid','inflated'];
const meshData = {};
['lh', 'rh'].forEach(h => {
  const m = PAYLOAD.mesh[h];
  const surfaces = {};
  SURFACE_KINDS.forEach(kind => {
    surfaces[kind] = {
      positions: b64ToFloat32(m.surfaces[kind].positions),
      normals:   b64ToFloat32(m.surfaces[kind].normals),
    };
  });
  // Center each state to (0,0,0) so OrbitControls rotates around the
  // visual centre regardless of morphT (matches spaces_viewer behaviour).
  const nv = m.n_verts;
  SURFACE_KINDS.forEach(kind => {
    const p = surfaces[kind].positions;
    let cx = 0, cy = 0, cz = 0;
    for (let i = 0; i < nv; i++) { cx += p[i*3]; cy += p[i*3+1]; cz += p[i*3+2]; }
    cx /= nv; cy /= nv; cz /= nv;
    for (let i = 0; i < nv; i++) { p[i*3] -= cx; p[i*3+1] -= cy; p[i*3+2] -= cz; }
  });
  meshData[h] = {
    faces:    b64ToUint32(m.faces),
    n_verts:  nv,
    surfaces: surfaces,
    vertex_to_roi: b64ToInt16(PAYLOAD.atlas['vertex_to_roi_' + h]),
  };
});

// ── ROI + map lookup tables ───────────────────────────────────────────────
const roiNames     = PAYLOAD.atlas.roi_names;
const roiLongNames = PAYLOAD.atlas.roi_long_names;
const topQuery     = PAYLOAD.atlas.top_terms_query;
const topSynth     = PAYLOAD.atlas.top_terms_synth;

let activeMapIdx = 0;

function switchMap(idx) {
  if (idx < 0) idx = PAYLOAD.maps.length - 1;
  if (idx >= PAYLOAD.maps.length) idx = 0;
  activeMapIdx = idx;
  
  const mapData = PAYLOAD.maps[activeMapIdx];
  currentCmap = mapData.cmap_type === 'diverging' ? currentCmapDiv : currentCmapPos;
  
  document.getElementById('map-label-main').textContent = mapData.label || "";
  document.getElementById('map-label-sub').textContent = mapData.sub_label || "";
  
  // Update nav buttons
  const btns = document.querySelectorAll('.nav-btn');
  btns.forEach((b, i) => {
    if (i === activeMapIdx) b.classList.add('active');
    else b.classList.remove('active');
  });
  
  drawColorbar();
  
  // Recolor meshes
  if (meshL) recolorMesh('lh', meshL);
  if (meshR) recolorMesh('rh', meshR);
  
  // Refresh tooltip if open
  const tooltip = document.getElementById('tooltip');
  if (tooltip && tooltip.style.display === 'block' && hoveredRoi >= 0) {
    if (tooltipPinned) tooltip.innerHTML = buildPinnedHtml(hoveredRoi, pinnedVertexIdx);
    else tooltip.innerHTML = buildHoverHtml(hoveredRoi, hoveredVertexIdx);
  }
}

// ── Per-vertex colours from scalar map + colormap ─────────────────────────
function buildVertexColors(hemiKey) {
  const md   = meshData[hemiKey];
  const nv   = md.n_verts;
  const mapData = PAYLOAD.maps[activeMapIdx];
  const vals = mapData[hemiKey];
  const vmin = mapData.vmin;
  const vmax = mapData.vmax;
  
  const colors = new Float32Array(nv * 4);
  for (let i = 0; i < nv; i++) {
    let r, g, b;
    if (md.vertex_to_roi[i] < 0) {
      r = NO_PARCEL_RGB[0]/255; g = NO_PARCEL_RGB[1]/255; b = NO_PARCEL_RGB[2]/255;
    } else {
      const t = vmax > vmin ? (vals[i] - vmin) / (vmax - vmin) : 0;
      const [R,G,B] = cmapRGB(t, currentCmap);
      r = R/255; g = G/255; b = B/255;
    }
    colors[i*4]=r; colors[i*4+1]=g; colors[i*4+2]=b; colors[i*4+3]=1.0;
  }
  return colors;
}

function recolorMesh(hemiKey, mesh) {
  const colors = buildVertexColors(hemiKey);
  const attr = mesh.geometry.attributes.color;
  // color is RGBA (4 components)
  for (let i = 0; i < colors.length; i++) attr.array[i] = colors[i];
  attr.needsUpdate = true;
}

// ── Three.js setup ───────────────────────────────────────────────────────
function setupScene(containerId, isLeft) {
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(25, H_W / H_H, 0.1, 5000);
  camera.position.set(isLeft ? -CAM_DIST : CAM_DIST, 0, 0);
  camera.up.set(0, 0, 1);
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setSize(H_W, H_H);
  renderer.setPixelRatio(Math.max(window.devicePixelRatio, 2));
  document.getElementById(containerId).appendChild(renderer.domElement);

  scene.add(new THREE.AmbientLight(0xffffff, 0.6));
  const headlamp = new THREE.PointLight(0xffffff, 0.8);
  headlamp.position.set(0, 0, 0);
  camera.add(headlamp);
  scene.add(camera);

  const controls = new THREE.OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.05;
  controls.enableZoom = false;     // scroll wheel → inflate/deflate
  controls.enablePan  = false;     // free right-click for tooltip pinning

  return { scene, camera, renderer, controls };
}

function buildMesh(hemiKey) {
  const md = meshData[hemiKey];
  const positions = new Float32Array(md.surfaces.mid.positions);
  const normals   = new Float32Array(md.surfaces.mid.normals);
  const colors    = buildVertexColors(hemiKey);

  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  geo.setAttribute('normal',   new THREE.BufferAttribute(normals, 3));
  geo.setAttribute('color',    new THREE.BufferAttribute(colors, 4));
  geo.setIndex(new THREE.BufferAttribute(md.faces, 1));

  const mat = new THREE.MeshStandardMaterial({
    vertexColors: true, roughness: 0.65, metalness: 0.0,
    flatShading: false, side: THREE.DoubleSide,
    transparent: true, opacity: 1.0,
  });
  const mesh = new THREE.Mesh(geo, mat);

  // Wireframe overlay shares the same geometry — toggled with M.
  const wireMat = new THREE.MeshBasicMaterial({
    wireframe: true, color: 0x333333, transparent: true, opacity: 0.15,
  });
  const wire = new THREE.Mesh(geo, wireMat);
  wire.userData.isWireframe = true;
  wire.visible = wireframeVisible;

  return { mesh, wire };
}

// ── Init ─────────────────────────────────────────────────────────────────
function init() {
  const tL = setupScene('container-left', true);
  sceneL = tL.scene; cameraL = tL.camera; rendererL = tL.renderer; controlsL = tL.controls;
  const tR = setupScene('container-right', false);
  sceneR = tR.scene; cameraR = tR.camera; rendererR = tR.renderer; controlsR = tR.controls;

  controlsL.addEventListener('change', () => { lastMovedSide = 'L'; });
  controlsR.addEventListener('change', () => { lastMovedSide = 'R'; });

  const builtL = buildMesh('lh');
  const builtR = buildMesh('rh');
  meshL = builtL.mesh; wireL = builtL.wire; meshL.userData.hemiKey = 'lh';
  meshR = builtR.mesh; wireR = builtR.wire; meshR.userData.hemiKey = 'rh';
  sceneL.add(meshL); sceneL.add(wireL);
  sceneR.add(meshR); sceneR.add(wireR);

  window.addEventListener('resize', onResize);
  window.addEventListener('keydown', onKeyDown);
  window.addEventListener('wheel', onWheel, { passive: true });
  window.addEventListener('mousemove', onMouseMove);
  window.addEventListener('pointerdown', (e) => { if (e.button === 0) { _downT = Date.now(); _leftDown = true; } });
  window.addEventListener('pointerup', onClick);
  window.addEventListener('contextmenu', onContextMenu);

  document.getElementById('loading').style.display = 'none';

  // Build nav menu
  const navMenu = document.getElementById('nav-menu');
  if (navMenu && PAYLOAD.maps.length > 1) {
    PAYLOAD.maps.forEach((mapData, i) => {
      const btn = document.createElement('div');
      btn.className = 'nav-btn';
      btn.textContent = mapData.label || `Map ${i+1}`;
      btn.onclick = () => switchMap(i);
      navMenu.appendChild(btn);
    });
  } else if (navMenu) {
    navMenu.style.display = 'none';
  }

  // Initialize the first map
  switchMap(0);

  animate();
}

function onResize() {
  const w = window.innerWidth / 2, h = window.innerHeight;
  const dpr = Math.max(window.devicePixelRatio, 2);
  [{c: cameraL, r: rendererL}, {c: cameraR, r: rendererR}].forEach(({c, r}) => {
    c.aspect = w / h; c.updateProjectionMatrix();
    r.setPixelRatio(dpr); r.setSize(w, h);
  });
}

function onKeyDown(e) {
  const k = e.key;
  if (k === 'ArrowUp')   { cameraL.position.multiplyScalar(0.9); cameraR.position.multiplyScalar(0.9); }
  if (k === 'ArrowDown') { cameraL.position.multiplyScalar(1.1); cameraR.position.multiplyScalar(1.1); }
  if (k === 'ArrowLeft') {
    morphT = Math.min(2, morphT + 0.1);
    applyMorph();
  }
  if (k === 'ArrowRight') {
    morphT = Math.max(0, morphT - 0.1);
    applyMorph();
  }
  if (k === 'l' || k === 'L') viewLocked = !viewLocked;
  if (k === 'r' || k === 'R') {
    cameraL.position.set(-CAM_DIST, 0, 0); cameraL.up.set(0, 0, 1);
    controlsL.target.set(0, 0, 0); controlsL.update();
    cameraR.position.set( CAM_DIST, 0, 0); cameraR.up.set(0, 0, 1);
    controlsR.target.set(0, 0, 0); controlsR.update();
    morphT = 0; applyMorph();
  }
  if (k === 'h' || k === 'H') {
    const modal = document.getElementById('help-modal');
    if (modal) modal.style.display = (modal.style.display === 'flex') ? 'none' : 'flex';
  }
  if (k === 'o' || k === 'O') {
    cortexOpacity = (cortexOpacity >= 0.99) ? REDUCED_OPACITY : 1.0;
    applyOpacity();
  }
  if (k === 'm' || k === 'M') {
    wireframeVisible = !wireframeVisible;
    if (wireL) wireL.visible = wireframeVisible;
    if (wireR) wireR.visible = wireframeVisible;
  }
  if (k === 'q' || k === 'Q') {
    hoverEnabled = !hoverEnabled;
    if (!hoverEnabled) unpinTooltip();
  }
  if (k === 't' || k === 'T') {
    document.body.classList.toggle('theme-white');
    const tooltip = document.getElementById('tooltip');
    if (tooltip && tooltip.style.display === 'block' && hoveredRoi >= 0) {
      if (tooltipPinned) tooltip.innerHTML = buildPinnedHtml(hoveredRoi, pinnedVertexIdx);
      else tooltip.innerHTML = buildHoverHtml(hoveredRoi, hoveredVertexIdx);
    }
  }
  if (k === ']') { switchMap(activeMapIdx + 1); }
  if (k === '[') { switchMap(activeMapIdx - 1); }
  if (k === 'c' || k === 'C') {
    const mapData = PAYLOAD.maps[activeMapIdx];
    if (mapData.cmap_type === 'diverging') {
      const ci = CMAP_CYCLE_DIV.indexOf(currentCmapDiv);
      currentCmapDiv = CMAP_CYCLE_DIV[(ci + 1) % CMAP_CYCLE_DIV.length];
      currentCmap = currentCmapDiv;
    } else {
      const ci = CMAP_CYCLE_POS.indexOf(currentCmapPos);
      currentCmapPos = CMAP_CYCLE_POS[(ci + 1) % CMAP_CYCLE_POS.length];
      currentCmap = currentCmapPos;
    }
    drawColorbar();
    if (meshL) recolorMesh('lh', meshL);
    if (meshR) recolorMesh('rh', meshR);
  }
}

function applyOpacity() {
  [meshL, meshR].forEach(mesh => {
    if (!mesh) return;
    const m = mesh.material;
    m.transparent = cortexOpacity < 1.0;
    m.opacity = cortexOpacity;
    m.depthWrite = cortexOpacity >= 1.0;
    m.needsUpdate = true;
  });
}

// ── Morph (mid ↔ inflated ↔ sphere) ──────────────────────────────────────
function onWheel(e) {
  const delta = Math.sign(e.deltaY) * -0.05;
  const next = Math.max(0, Math.min(2, morphT + delta));
  if (next !== morphT) {
    morphT = next;
    applyMorph();
  }
}

function applyMorph() {
  [meshL, meshR].forEach(mesh => {
    if (!mesh) return;
    const md = meshData[mesh.userData.hemiKey];
    let p0, p1, n0, n1, t;
    if (morphT <= 1.0) {
      p0 = md.surfaces.mid.positions;       p1 = md.surfaces.inflated.positions;
      n0 = md.surfaces.mid.normals;         n1 = md.surfaces.inflated.normals;
      t = morphT;
    } else {
      p0 = md.surfaces.inflated.positions;  p1 = md.surfaces.sphere.positions;
      n0 = md.surfaces.inflated.normals;    n1 = md.surfaces.sphere.normals;
      t = morphT - 1.0;
    }
    const pos = mesh.geometry.attributes.position.array;
    const nrm = mesh.geometry.attributes.normal.array;
    const N = pos.length;
    for (let i = 0; i < N; i++) {
      pos[i] = p0[i] * (1 - t) + p1[i] * t;
      nrm[i] = n0[i] * (1 - t) + n1[i] * t;
    }
    mesh.geometry.attributes.position.needsUpdate = true;
    mesh.geometry.attributes.normal.needsUpdate = true;
  });
}

// ── Tooltip helpers ──────────────────────────────────────────────────────
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c =>
    ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

function buildHoverHtml(roiIdx, vertexIdx) {
  const shortName = roiNames[roiIdx];
  const longName  = roiLongNames[roiIdx];
  const hKey = shortName.startsWith('R_') ? 'rh' : 'lh';
  const mapData = PAYLOAD.maps[activeMapIdx];
  const mv   = mapData[hKey];
  let valStr = '';
  if (vertexIdx >= 0 && vertexIdx < mv.length) {
    valStr = `<div class="tooltip-map-val">${escapeHtml(mapData.label)}: ${mv[vertexIdx].toFixed(3)}</div>`;
  }
  return `<div class="tooltip-header">
    <strong>${escapeHtml(longName)}</strong>
    <span class="roi-short">(${escapeHtml(shortName)})</span>
  </div>
  ${valStr}
  <div class="tooltip-click-hint">Right-click to pin functional terms</div>`;
}

function buildPinnedHtml(roiIdx, vertexIdx) {
  const shortName = roiNames[roiIdx];
  const longName  = roiLongNames[roiIdx];
  const hKey = shortName.startsWith('R_') ? 'rh' : 'lh';
  const mapData = PAYLOAD.maps[activeMapIdx];
  const mv   = mapData[hKey];
  let valStr = '';
  if (vertexIdx >= 0 && vertexIdx < mv.length) {
    valStr = `<div class="tooltip-map-val">${escapeHtml(mapData.label)}: ${mv[vertexIdx].toFixed(3)}</div>`;
  }
  const q = topQuery[roiIdx] || [];
  const s = topSynth[roiIdx] || [];

  // Per-db value-normalised greyscale: brightest = top of list, darkest = bottom.
  const isWhite = document.body.classList.contains('theme-white');
  function shade(val, vmin, vmax) {
    if (vmax <= vmin) return isWhite ? 120 : 200;
    const t = (val - vmin) / (vmax - vmin);
    return isWhite ? Math.round(150 - t * 150) : Math.round(110 + t * 130);
  }

  function dbBlock(label, terms) {
    if (terms.length === 0) {
      return `<div class="tooltip-db">
        <div class="tooltip-db-label">${escapeHtml(label)}</div>
        <div class="tooltip-empty">no terms with positive value</div>
      </div>`;
    }
    const vals = terms.map(t => t[1]);
    const vmin = Math.min(...vals);
    const vmax = Math.max(...vals);
    const cells = terms.map(([term, val]) => {
      const g = shade(val, vmin, vmax);
      const color = `rgb(${g},${g},${g})`;
      return `<div class="tooltip-cell" style="color:${color}">` +
             `<span class="term">${escapeHtml(term)}</span>` +
             `<span class="val">${Number(val).toFixed(2)}</span></div>`;
    }).join('');
    return `<div class="tooltip-db">
      <div class="tooltip-db-label">${escapeHtml(label)}</div>
      <div class="tooltip-db-grid">${cells}</div>
    </div>`;
  }

  return `<div class="tooltip-header">
    <strong>${escapeHtml(longName)}</strong>
    <span class="roi-short">(${escapeHtml(shortName)})</span>
  </div>
  ${valStr}
  <div class="tooltip-click-hint">Click anywhere to return to hover</div>
  <div class="tooltip-body">
    ${dbBlock('NeuroQuery', q)}
    ${dbBlock('NeuroSynth', s)}
  </div>`;
}

// Viewport margins — clear nav-menu (top ~55px) and help-bar (bottom ~35px).
const TIP_MARGIN_TOP    = 60;
const TIP_MARGIN_BOTTOM = 38;
const TIP_MARGIN_SIDE   =  8;

// Hover tooltip: simple cursor offset, no arrow nub.
const TIP_HOVER_OFFSET = 18;
function placeTooltipAtCursor(tooltip, clientX, clientY) {
  const w = tooltip.offsetWidth, h = tooltip.offsetHeight;
  const W = window.innerWidth,   H = window.innerHeight;
  let x = clientX + TIP_HOVER_OFFSET;
  let y = clientY + TIP_HOVER_OFFSET;
  if (x + w > W - TIP_MARGIN_SIDE) x = clientX - TIP_HOVER_OFFSET - w;
  x = Math.max(TIP_MARGIN_SIDE,   Math.min(W - w - TIP_MARGIN_SIDE,   x));
  y = Math.max(TIP_MARGIN_TOP,    Math.min(H - h - TIP_MARGIN_BOTTOM, y));
  tooltip.style.left = x + 'px';
  tooltip.style.top  = y + 'px';
}

// Pinned tooltip: anchors to dot with adaptive arrow that slides along the edge.
const DOT_GAP   = 60;
const ARROW_MIN = 14;  // % — keeps arrow off rounded corners
const ARROW_MAX = 86;
function placeTooltipAtDot(tooltip, sx, sy) {
  const tw = tooltip.offsetWidth, th = tooltip.offsetHeight;
  const W  = window.innerWidth,   H  = window.innerHeight;
  const spaces = {
    right:  W - sx - DOT_GAP,
    left:   sx - DOT_GAP,
    bottom: H - sy - DOT_GAP - TIP_MARGIN_BOTTOM,
    top:    sy - DOT_GAP - TIP_MARGIN_TOP,
  };
  const side = Object.entries(spaces).sort((a,b) => b[1]-a[1])[0][0];
  let x, y, arrow;
  if (side === 'right')  { x = sx + DOT_GAP;       y = sy - th/2;       arrow = 'left';   }
  if (side === 'left')   { x = sx - DOT_GAP - tw;  y = sy - th/2;       arrow = 'right';  }
  if (side === 'bottom') { x = sx - tw/2;           y = sy + DOT_GAP;    arrow = 'top';    }
  if (side === 'top')    { x = sx - tw/2;           y = sy - DOT_GAP-th; arrow = 'bottom'; }
  x = Math.max(TIP_MARGIN_SIDE,   Math.min(W - tw - TIP_MARGIN_SIDE,   x));
  y = Math.max(TIP_MARGIN_TOP,    Math.min(H - th - TIP_MARGIN_BOTTOM, y));
  tooltip.style.left = x + 'px';
  tooltip.style.top  = y + 'px';
  tooltip.setAttribute('data-arrow', arrow);
  const pct = (arrow === 'left' || arrow === 'right')
    ? Math.max(ARROW_MIN, Math.min(ARROW_MAX, (sy - y) / th * 100))
    : Math.max(ARROW_MIN, Math.min(ARROW_MAX, (sx - x) / tw * 100));
  tooltip.style.setProperty('--arrow-pos', pct + '%');
}

// ── Raycasting ───────────────────────────────────────────────────────────
function pickRoiAt(clientX, clientY) {
  // Returns { mesh, vertexIdx, roi, side } or null. Snaps to whichever of the
  // three face vertices is closest to the actual hit point so the leader line
  // anchors precisely (face[0] alone can be 5-15 mm off).
  const isLeft = clientX < window.innerWidth / 2;
  const rcCamera = isLeft ? cameraL : cameraR;
  const targetMesh = isLeft ? meshL : meshR;
  const containerId = isLeft ? 'container-left' : 'container-right';
  const rect = document.getElementById(containerId).getBoundingClientRect();
  const mx = ((clientX - rect.left) / rect.width) * 2 - 1;
  const my = -((clientY - rect.top) / rect.height) * 2 + 1;
  if (!targetMesh) return null;
  raycaster.setFromCamera(new THREE.Vector2(mx, my), rcCamera);
  const hits = raycaster.intersectObject(targetMesh, true);
  if (hits.length === 0) return null;
  const faceIdx = hits[0].faceIndex;
  if (faceIdx == null) return null;
  const indexAttr = targetMesh.geometry.index;
  const face = [
    indexAttr.array[faceIdx * 3],
    indexAttr.array[faceIdx * 3 + 1],
    indexAttr.array[faceIdx * 3 + 2],
  ];
  const hitLocal = targetMesh.worldToLocal(hits[0].point.clone());
  const posArr = targetMesh.geometry.attributes.position.array;
  let pickedVert = face[0];
  let bestD2 = Infinity;
  for (const vi of face) {
    const dx = posArr[vi*3]   - hitLocal.x;
    const dy = posArr[vi*3+1] - hitLocal.y;
    const dz = posArr[vi*3+2] - hitLocal.z;
    const d2 = dx*dx + dy*dy + dz*dz;
    if (d2 < bestD2) { bestD2 = d2; pickedVert = vi; }
  }
  const md = meshData[targetMesh.userData.hemiKey];
  const roi = md.vertex_to_roi[pickedVert];
  if (roi < 0) return null;
  return { mesh: targetMesh, vertexIdx: pickedVert, roi: roi, side: isLeft ? 'L' : 'R' };
}

// ── Dot marker (div) ─────────────────────────────────────────────────────
function placeMarker(hostMesh, vertexIdx, side) {
  pinnedHostMesh = hostMesh;
  pinnedVertexIdx = vertexIdx;
  pinnedSide = side;
  syncMarker();
}

function removeMarker() {
  pinnedHostMesh = null;
  pinnedVertexIdx = -1;
  pinnedSide = null;
  document.getElementById('dot').style.display = 'none';
}

function syncMarker() {
  if (!pinnedHostMesh || pinnedVertexIdx < 0) return;
  const cam = pinnedSide === 'L' ? cameraL : cameraR;
  const cRect = document.getElementById(
    pinnedSide === 'L' ? 'container-left' : 'container-right'
  ).getBoundingClientRect();
  const pos  = pinnedHostMesh.geometry.attributes.position.array;
  const norm = pinnedHostMesh.geometry.attributes.normal.array;
  const i3   = pinnedVertexIdx * 3;
  pinnedHostMesh.updateMatrixWorld();

  const worldPos = new THREE.Vector3(pos[i3], pos[i3+1], pos[i3+2])
    .applyMatrix4(pinnedHostMesh.matrixWorld);

  // Hide dot+tooltip when vertex faces away from camera (back of brain)
  const worldNorm = new THREE.Vector3(norm[i3], norm[i3+1], norm[i3+2])
    .transformDirection(pinnedHostMesh.matrixWorld);
  const toCamera = new THREE.Vector3().subVectors(cam.position, worldPos).normalize();
  const occluded = worldNorm.dot(toCamera) <= 0;

  const dot     = document.getElementById('dot');
  const tooltip = document.getElementById('tooltip');
  if (occluded) {
    dot.style.display = 'none';
    if (tooltip) tooltip.style.display = 'none';
    return;
  }

  const wp = worldPos.clone().project(cam);
  const sx = cRect.left + (wp.x + 1) * 0.5 * cRect.width;
  const sy = cRect.top  + (1 - wp.y) * 0.5 * cRect.height;
  dot.style.display = 'block';
  dot.style.left = sx + 'px';
  dot.style.top  = sy + 'px';
  if (tooltip && tooltipPinned) {
    tooltip.style.display = 'block';
    placeTooltipAtDot(tooltip, sx, sy);
  }
}

function onMouseMove(e) {
  if (!hoverEnabled) return;
  if (tooltipPinned) return;
  const tooltip = document.getElementById('tooltip');
  const hit = pickRoiAt(e.clientX, e.clientY);
  if (!hit) {
    tooltip.style.display = 'none';
    hoveredRoi = -1;
    hoveredVertexIdx = -1;
    return;
  }
  hoveredVertexIdx = hit.vertexIdx;
  if (hit.roi !== hoveredRoi) {
    hoveredRoi = hit.roi;
    tooltip.innerHTML = buildHoverHtml(hit.roi, hit.vertexIdx);
  }
  tooltip.className = '';
  tooltip.style.pointerEvents = 'none';
  tooltip.style.display = 'block';
  placeTooltipAtCursor(tooltip, e.clientX, e.clientY);
}

// Left-click anywhere returns to hover mode. Drag-rotate ends in a click on
// mouseup, so this also dismisses pinned tooltips after rotating.
function unpinTooltip() {
  tooltipPinned = false;
  const tooltip = document.getElementById('tooltip');
  tooltip.className = '';
  tooltip.style.pointerEvents = 'none';
  tooltip.style.display = 'none';
  hoveredRoi = -1;
  hoveredVertexIdx = -1;
  removeMarker();
}

function onClick(e) {
  if (e.button !== 0) return;
  const wasDown = _leftDown; _leftDown = false;
  if (!hoverEnabled || !tooltipPinned || !wasDown) return;
  if (e.target.closest('#tooltip')) return;
  if (Date.now() - _downT > 200) return;
  unpinTooltip();
}

function onContextMenu(e) {
  if (!hoverEnabled) return;
  if (e.target.closest('#tooltip')) return;
  e.preventDefault();
  const hit = pickRoiAt(e.clientX, e.clientY);
  if (!hit) { if (tooltipPinned) unpinTooltip(); return; }
  const tooltip = document.getElementById('tooltip');
  tooltipPinned = true;
  tooltip.className = 'pinned';
  tooltip.style.pointerEvents = 'auto';
  tooltip.innerHTML = buildPinnedHtml(hit.roi, hit.vertexIdx);
  tooltip.style.display = 'block';
  placeMarker(hit.mesh, hit.vertexIdx, hit.side);  // syncMarker places tooltip
}

// ── Animate (with locked camera mirror) ──────────────────────────────────
function animate() {
  requestAnimationFrame(animate);
  if (controlsL) controlsL.update();
  if (controlsR) controlsR.update();
  syncMarker();

  if (viewLocked && cameraL && cameraR) {
    if (lastMovedSide === 'L') {
      const p = cameraL.position;
      cameraR.position.set(-p.x, p.y, p.z);
      cameraR.up.copy(cameraL.up);
      controlsR.target.set(0, 0, 0); controlsR.update();
    } else {
      const p = cameraR.position;
      cameraL.position.set(-p.x, p.y, p.z);
      cameraL.up.copy(cameraR.up);
      controlsL.target.set(0, 0, 0); controlsL.update();
    }
  }

  if (sceneL && cameraL) rendererL.render(sceneL, cameraL);
  if (sceneR && cameraR) rendererR.render(sceneR, cameraR);
}

init();
