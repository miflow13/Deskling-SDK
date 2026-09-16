const animationSpecs = [
  {
    id: "idle",
    manifestName: "idle",
    label: "Idle",
    description: "The animation your pet returns to.",
    required: true,
    mode: "pingpong",
    durationMs: 350,
    frames: [],
  },
  {
    id: "click",
    manifestName: "click",
    label: "Click reaction",
    description: "Optional single-click reaction.",
    required: false,
    mode: "once",
    durationMs: 140,
    frames: [],
  },
  {
    id: "double",
    manifestName: "double_click",
    label: "Double-click reaction",
    description: "Optional special reaction.",
    required: false,
    mode: "once",
    durationMs: 220,
    frames: [],
  },
];

const state = {
  activeAnimation: "idle",
  animationTimer: null,
  animationToken: 0,
  clickTimer: null,
  dragging: false,
  dragMoved: false,
  dragStartPointer: null,
  dragStartCenter: null,
  suppressClickUntil: 0,
};

const els = {
  animationList: document.querySelector("#animation-list"),
  petName: document.querySelector("#pet-name"),
  width: document.querySelector("#pet-width"),
  height: document.querySelector("#pet-height"),
  scale: document.querySelector("#pet-scale"),
  sprite: document.querySelector("#pet-sprite"),
  placeholder: document.querySelector("#pet-placeholder"),
  stage: document.querySelector("#pet-stage"),
  desktop: document.querySelector("#desktop-preview"),
  manifest: document.querySelector("#manifest-preview"),
  validation: document.querySelector("#validation-state"),
  packageName: document.querySelector("#package-name-preview"),
  exportButton: document.querySelector("#export-button"),
  exportMessage: document.querySelector("#export-message"),
  resetPreview: document.querySelector("#reset-preview"),
  previewButtons: [...document.querySelectorAll("[data-preview-animation]")],
};

const MAX_FILE_BYTES = 10 * 1024 * 1024;
const MAX_PACKAGE_BYTES = 50 * 1024 * 1024;
const ACCEPTED_EXTENSIONS = new Set(["png", "svg", "webp", "jpg", "jpeg"]);

function getAnimation(id) {
  return animationSpecs.find((animation) => animation.id === id);
}

function extensionFor(file) {
  const raw = file.name.split(".").pop()?.toLowerCase() || "";
  if (ACCEPTED_EXTENSIONS.has(raw)) return raw;
  if (file.type === "image/svg+xml") return "svg";
  if (file.type === "image/png") return "png";
  if (file.type === "image/webp") return "webp";
  if (file.type === "image/jpeg") return "jpg";
  return null;
}

function exportedFrameName(animation, index, file) {
  const ext = extensionFor(file) || "png";
  const number = String(index + 1).padStart(3, "0");
  return `sprites/${animation.manifestName}_${number}.${ext}`;
}

function escapeToml(value) {
  return String(value)
    .replaceAll("\\", "\\\\")
    .replaceAll('"', '\\"')
    .replaceAll("\n", "\\n")
    .replaceAll("\r", "\\r")
    .replaceAll("\t", "\\t");
}

function numberValue(element, fallback) {
  const value = Number(element.value);
  return Number.isFinite(value) && value > 0 ? value : fallback;
}

function slugify(value) {
  const slug = value
    .trim()
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60);
  return slug || "my-deskling";
}

function manifestForCurrentState() {
  const name = els.petName.value.trim() || "My Deskling";
  const width = Math.round(numberValue(els.width, 64));
  const height = Math.round(numberValue(els.height, 64));
  const scale = numberValue(els.scale, 2);
  const idle = getAnimation("idle");
  const click = getAnimation("click");
  const doubleClick = getAnimation("double");

  const lines = [
    "schema_version = 1",
    "",
    "[pet]",
    `name = "${escapeToml(name)}"`,
    `width = ${width}`,
    `height = ${height}`,
    `scale = ${scale}`,
    'default_state = "idle"',
    'default_animation = "idle"',
  ];

  for (const animation of animationSpecs) {
    if (!animation.frames.length) continue;
    lines.push("", `[animations.${animation.manifestName}]`, `mode = "${animation.mode}"`, "frames = [");
    animation.frames.forEach((frame, index) => {
      const fileName = exportedFrameName(animation, index, frame.file);
      lines.push(`  { file = "${fileName}", duration_ms = ${animation.durationMs} },`);
    });
    lines.push("]");
  }

  if (click.frames.length || doubleClick.frames.length) {
    lines.push("", "[interaction]");
    if (click.frames.length) lines.push('click_animation = "click"');
    if (doubleClick.frames.length) lines.push('double_click_animation = "double_click"');
  }

  lines.push("", "[transitions]");
  if (click.frames.length || doubleClick.frames.length) {
    lines.push('idle = ["reaction", "dragging"]');
    lines.push('reaction = ["idle", "dragging"]');
  } else {
    lines.push('idle = ["dragging"]');
  }
  lines.push('dragging = ["idle"]');

  return lines.join("\n") + "\n";
}

function validationResult() {
  const idle = getAnimation("idle");
  if (!els.petName.value.trim()) return { ready: false, message: "Give your pet a name" };
  if (!idle.frames.length) return { ready: false, message: "Waiting for idle frames" };

  const width = Number(els.width.value);
  const height = Number(els.height.value);
  const scale = Number(els.scale.value);
  if (!Number.isFinite(width) || width <= 0 || !Number.isFinite(height) || height <= 0 || !Number.isFinite(scale) || scale <= 0) {
    return { ready: false, message: "Canvas values must be positive" };
  }

  const totalBytes = animationSpecs.flatMap((animation) => animation.frames).reduce((sum, frame) => sum + frame.file.size, 0);
  if (totalBytes > MAX_PACKAGE_BYTES) return { ready: false, message: "Assets exceed the 50 MB package limit" };
  return { ready: true, message: "Ready to export" };
}

function refreshGeneratedState() {
  els.manifest.textContent = manifestForCurrentState();
  const validation = validationResult();
  els.validation.textContent = validation.message;
  els.validation.classList.toggle("ready", validation.ready);
  els.exportButton.disabled = !validation.ready;
  els.packageName.textContent = `${slugify(els.petName.value)}.deskling`;

  for (const button of els.previewButtons) {
    const animation = getAnimation(button.dataset.previewAnimation);
    button.disabled = !animation?.frames.length;
  }
}

function renderAnimationCards() {
  els.animationList.replaceChildren();

  for (const animation of animationSpecs) {
    const card = document.createElement("section");
    card.className = `animation-card${animation.required ? " required" : ""}`;
    card.dataset.animation = animation.id;

    const head = document.createElement("div");
    head.className = "animation-card-head";
    head.innerHTML = `
      <div>
        <strong>${animation.label}</strong>
        <small>${animation.description}</small>
      </div>
    `;

    const controls = document.createElement("div");
    controls.style.display = "flex";
    controls.style.alignItems = "center";
    controls.style.gap = "7px";
    if (animation.required) {
      const chip = document.createElement("span");
      chip.className = "required-chip";
      chip.textContent = "Required";
      controls.append(chip);
    }

    const uploadLabel = document.createElement("label");
    uploadLabel.className = "upload-button";
    uploadLabel.innerHTML = `+ Add frames<input type="file" accept=".png,.svg,.webp,.jpg,.jpeg,image/png,image/svg+xml,image/webp,image/jpeg" multiple>`;
    const fileInput = uploadLabel.querySelector("input");
    fileInput.addEventListener("change", () => addFiles(animation, fileInput.files));
    controls.append(uploadLabel);
    head.append(controls);
    card.append(head);

    const frameStrip = document.createElement("div");
    frameStrip.className = "frame-strip";
    if (!animation.frames.length) {
      const empty = document.createElement("div");
      empty.className = "empty-frames";
      empty.textContent = animation.required ? "Drop in the frames that make your pet feel alive" : "Optional — add one or more frames";
      frameStrip.append(empty);
    } else {
      animation.frames.forEach((frame, index) => {
        const thumb = document.createElement("div");
        thumb.className = "frame-thumb";
        const image = document.createElement("img");
        image.src = frame.url;
        image.alt = `${animation.label} frame ${index + 1}`;
        const indexLabel = document.createElement("span");
        indexLabel.className = "frame-index";
        indexLabel.textContent = String(index + 1);
        const remove = document.createElement("button");
        remove.type = "button";
        remove.title = "Remove frame";
        remove.textContent = "×";
        remove.addEventListener("click", () => removeFrame(animation, index));
        thumb.append(image, indexLabel, remove);
        frameStrip.append(thumb);
      });
    }
    card.append(frameStrip);

    const settings = document.createElement("div");
    settings.className = "animation-settings";
    settings.innerHTML = `
      <label>Playback
        <select data-setting="mode">
          <option value="once">Once</option>
          <option value="loop">Loop</option>
          <option value="pingpong">Ping-pong</option>
        </select>
      </label>
      <label>Frame time (ms)
        <input data-setting="duration" type="number" min="16" max="10000" step="10" value="${animation.durationMs}">
      </label>
    `;
    const mode = settings.querySelector('[data-setting="mode"]');
    mode.value = animation.mode;
    mode.addEventListener("change", () => {
      animation.mode = mode.value;
      refreshGeneratedState();
      if (state.activeAnimation === animation.id) playAnimation(animation.id);
    });
    const duration = settings.querySelector('[data-setting="duration"]');
    duration.addEventListener("change", () => {
      animation.durationMs = Math.max(16, Math.min(10000, Number(duration.value) || 100));
      duration.value = animation.durationMs;
      refreshGeneratedState();
      if (state.activeAnimation === animation.id) playAnimation(animation.id);
    });
    card.append(settings);
    els.animationList.append(card);
  }
}

function addFiles(animation, fileList) {
  const errors = [];
  for (const file of fileList || []) {
    if (!extensionFor(file)) {
      errors.push(`${file.name}: unsupported image type`);
      continue;
    }
    if (file.size > MAX_FILE_BYTES) {
      errors.push(`${file.name}: larger than 10 MB`);
      continue;
    }
    animation.frames.push({ file, url: URL.createObjectURL(file) });
  }
  if (errors.length) els.exportMessage.textContent = errors.join(" · ");
  renderAnimationCards();
  refreshGeneratedState();
  if (animation.id === "idle" && animation.frames.length) playAnimation("idle");
}

function removeFrame(animation, index) {
  const [removed] = animation.frames.splice(index, 1);
  if (removed) URL.revokeObjectURL(removed.url);
  renderAnimationCards();
  refreshGeneratedState();
  if (animation.id === state.activeAnimation || animation.id === "idle") playAnimation("idle");
}

function playbackOrder(animation) {
  const length = animation.frames.length;
  if (length <= 1) return length ? [0] : [];
  if (animation.mode !== "pingpong") return Array.from({ length }, (_, index) => index);
  return [
    ...Array.from({ length }, (_, index) => index),
    ...Array.from({ length: length - 2 }, (_, index) => length - 2 - index),
  ];
}

function showFrame(animation, frameIndex) {
  const frame = animation.frames[frameIndex];
  if (!frame) return;
  els.placeholder.hidden = true;
  els.sprite.hidden = false;
  els.sprite.src = frame.url;
  els.sprite.alt = `${els.petName.value || "Deskling"} — ${animation.label}`;
}

function playAnimation(id) {
  window.clearTimeout(state.animationTimer);
  const token = ++state.animationToken;
  const animation = getAnimation(id);
  state.activeAnimation = id;

  if (!animation?.frames.length) {
    if (id !== "idle") return playAnimation("idle");
    els.sprite.hidden = true;
    els.placeholder.hidden = false;
    return;
  }

  const order = playbackOrder(animation);
  let cursor = 0;

  const advance = () => {
    if (token !== state.animationToken) return;
    showFrame(animation, order[cursor]);
    cursor += 1;

    if (cursor >= order.length) {
      if (animation.mode === "once") {
        state.animationTimer = window.setTimeout(() => playAnimation("idle"), animation.durationMs);
        return;
      }
      cursor = 0;
    }
    state.animationTimer = window.setTimeout(advance, animation.durationMs);
  };

  advance();
}

function resetPreviewPosition() {
  els.stage.style.left = "50%";
  els.stage.style.top = "62%";
  els.stage.style.transform = "translate(-50%, -50%)";
}

function startDrag(event) {
  if (event.button !== 0 || !getAnimation("idle").frames.length) return;
  const stageRect = els.stage.getBoundingClientRect();
  const desktopRect = els.desktop.getBoundingClientRect();
  const center = {
    x: stageRect.left - desktopRect.left + stageRect.width / 2,
    y: stageRect.top - desktopRect.top + stageRect.height / 2,
  };
  els.stage.style.left = `${center.x}px`;
  els.stage.style.top = `${center.y}px`;
  els.stage.style.transform = "translate(-50%, -50%)";
  state.dragging = true;
  state.dragMoved = false;
  state.dragStartPointer = { x: event.clientX, y: event.clientY };
  state.dragStartCenter = center;
  els.stage.classList.add("dragging");
  els.stage.setPointerCapture?.(event.pointerId);
}

function moveDrag(event) {
  if (!state.dragging) return;
  const desktopRect = els.desktop.getBoundingClientRect();
  const dx = event.clientX - state.dragStartPointer.x;
  const dy = event.clientY - state.dragStartPointer.y;
  if (Math.hypot(dx, dy) > 5) state.dragMoved = true;

  const halfW = els.stage.offsetWidth / 2;
  const halfH = els.stage.offsetHeight / 2;
  const x = Math.max(halfW, Math.min(desktopRect.width - halfW, state.dragStartCenter.x + dx));
  const y = Math.max(halfH + 30, Math.min(desktopRect.height - halfH, state.dragStartCenter.y + dy));
  els.stage.style.left = `${x}px`;
  els.stage.style.top = `${y}px`;
}

function endDrag() {
  if (!state.dragging) return;
  state.dragging = false;
  els.stage.classList.remove("dragging");
  if (state.dragMoved) state.suppressClickUntil = Date.now() + 350;
}

function handleSingleClick() {
  if (Date.now() < state.suppressClickUntil) return;
  window.clearTimeout(state.clickTimer);
  state.clickTimer = window.setTimeout(() => {
    if (getAnimation("click").frames.length) playAnimation("click");
  }, 240);
}

function handleDoubleClick(event) {
  event.preventDefault();
  if (Date.now() < state.suppressClickUntil) return;
  window.clearTimeout(state.clickTimer);
  if (getAnimation("double").frames.length) playAnimation("double");
}

function crc32(bytes) {
  let crc = 0xffffffff;
  for (const byte of bytes) {
    crc = CRC_TABLE[(crc ^ byte) & 0xff] ^ (crc >>> 8);
  }
  return (crc ^ 0xffffffff) >>> 0;
}

const CRC_TABLE = (() => {
  const table = new Uint32Array(256);
  for (let n = 0; n < 256; n += 1) {
    let c = n;
    for (let k = 0; k < 8; k += 1) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    table[n] = c >>> 0;
  }
  return table;
})();

function writeU16(view, offset, value) {
  view.setUint16(offset, value, true);
}

function writeU32(view, offset, value) {
  view.setUint32(offset, value >>> 0, true);
}

function concatBytes(parts) {
  const length = parts.reduce((sum, part) => sum + part.length, 0);
  const output = new Uint8Array(length);
  let offset = 0;
  for (const part of parts) {
    output.set(part, offset);
    offset += part.length;
  }
  return output;
}

function localHeader(nameBytes, dataBytes, crc) {
  const header = new Uint8Array(30);
  const view = new DataView(header.buffer);
  writeU32(view, 0, 0x04034b50);
  writeU16(view, 4, 20);
  writeU16(view, 6, 0x0800);
  writeU16(view, 8, 0);
  writeU16(view, 10, 0);
  writeU16(view, 12, 0x0021);
  writeU32(view, 14, crc);
  writeU32(view, 18, dataBytes.length);
  writeU32(view, 22, dataBytes.length);
  writeU16(view, 26, nameBytes.length);
  writeU16(view, 28, 0);
  return header;
}

function centralHeader(nameBytes, dataBytes, crc, localOffset) {
  const header = new Uint8Array(46);
  const view = new DataView(header.buffer);
  writeU32(view, 0, 0x02014b50);
  writeU16(view, 4, 0x0314);
  writeU16(view, 6, 20);
  writeU16(view, 8, 0x0800);
  writeU16(view, 10, 0);
  writeU16(view, 12, 0);
  writeU16(view, 14, 0x0021);
  writeU32(view, 16, crc);
  writeU32(view, 20, dataBytes.length);
  writeU32(view, 24, dataBytes.length);
  writeU16(view, 28, nameBytes.length);
  writeU16(view, 30, 0);
  writeU16(view, 32, 0);
  writeU16(view, 34, 0);
  writeU16(view, 36, 0);
  writeU32(view, 38, 0x81a40000);
  writeU32(view, 42, localOffset);
  return header;
}

function endOfCentralDirectory(entryCount, centralSize, centralOffset) {
  const end = new Uint8Array(22);
  const view = new DataView(end.buffer);
  writeU32(view, 0, 0x06054b50);
  writeU16(view, 4, 0);
  writeU16(view, 6, 0);
  writeU16(view, 8, entryCount);
  writeU16(view, 10, entryCount);
  writeU32(view, 12, centralSize);
  writeU32(view, 16, centralOffset);
  writeU16(view, 20, 0);
  return end;
}

function buildStoredZip(entries) {
  const encoder = new TextEncoder();
  const localParts = [];
  const centralParts = [];
  let localOffset = 0;

  for (const entry of entries) {
    const nameBytes = encoder.encode(entry.name);
    const dataBytes = entry.data instanceof Uint8Array ? entry.data : new Uint8Array(entry.data);
    const crc = crc32(dataBytes);
    const local = localHeader(nameBytes, dataBytes, crc);
    localParts.push(local, nameBytes, dataBytes);
    centralParts.push(centralHeader(nameBytes, dataBytes, crc, localOffset), nameBytes);
    localOffset += local.length + nameBytes.length + dataBytes.length;
  }

  const central = concatBytes(centralParts);
  const local = concatBytes(localParts);
  const end = endOfCentralDirectory(entries.length, central.length, local.length);
  return concatBytes([local, central, end]);
}

async function packageEntries() {
  const encoder = new TextEncoder();
  const entries = [{ name: "pet.toml", data: encoder.encode(manifestForCurrentState()) }];
  for (const animation of animationSpecs) {
    for (let index = 0; index < animation.frames.length; index += 1) {
      const frame = animation.frames[index];
      entries.push({
        name: exportedFrameName(animation, index, frame.file),
        data: new Uint8Array(await frame.file.arrayBuffer()),
      });
    }
  }
  entries.sort((a, b) => {
    if (a.name === "pet.toml") return -1;
    if (b.name === "pet.toml") return 1;
    return a.name.localeCompare(b.name);
  });
  return entries;
}

async function exportPackage() {
  const validation = validationResult();
  if (!validation.ready) return;
  els.exportButton.disabled = true;
  els.exportButton.textContent = "Building package…";
  els.exportMessage.textContent = "Creating a local, data-only .deskling archive…";

  try {
    const entries = await packageEntries();
    const zipBytes = buildStoredZip(entries);
    const fileName = `${slugify(els.petName.value)}.deskling`;
    const blob = new Blob([zipBytes], { type: "application/zip" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = fileName;
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    els.exportMessage.textContent = `Built ${fileName} locally (${Math.max(1, Math.round(zipBytes.length / 1024))} KB).`;
  } catch (error) {
    console.error(error);
    els.exportMessage.textContent = `Export failed: ${error instanceof Error ? error.message : String(error)}`;
  } finally {
    els.exportButton.textContent = "Export .deskling";
    refreshGeneratedState();
  }
}

for (const input of [els.petName, els.width, els.height, els.scale]) {
  input.addEventListener("input", refreshGeneratedState);
  input.addEventListener("change", refreshGeneratedState);
}

for (const button of els.previewButtons) {
  button.addEventListener("click", () => playAnimation(button.dataset.previewAnimation));
}

els.resetPreview.addEventListener("click", resetPreviewPosition);
els.exportButton.addEventListener("click", exportPackage);
els.stage.addEventListener("pointerdown", startDrag);
els.stage.addEventListener("pointermove", moveDrag);
els.stage.addEventListener("pointerup", endDrag);
els.stage.addEventListener("pointercancel", endDrag);
els.stage.addEventListener("click", handleSingleClick);
els.stage.addEventListener("dblclick", handleDoubleClick);

window.addEventListener("beforeunload", () => {
  for (const animation of animationSpecs) {
    for (const frame of animation.frames) URL.revokeObjectURL(frame.url);
  }
});

renderAnimationCards();
refreshGeneratedState();
resetPreviewPosition();
