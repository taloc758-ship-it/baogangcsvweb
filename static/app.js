const state = {
  path: "",
  encoding: "gb18030",
  delimiter: ",",
  headers: [],
  rows: [],
  editingRowIndex: null,
};

const els = {};

function setStatus(message, kind = "") {
  els.status.textContent = message;
  els.status.dataset.kind = kind;
}

function ensureStateShape() {
  const width = Math.max(state.headers.length, ...state.rows.map((row) => row.length), 0);
  if (width === 0) return;
  while (state.headers.length < width) state.headers.push(`列${state.headers.length + 1}`);
  state.rows = state.rows.map((row) => {
    const next = row.slice(0, width);
    while (next.length < width) next.push("");
    return next;
  });
}

function syncMeta() {
  els.encoding.textContent = state.encoding || "-";
  els.rowCount.textContent = String(state.rows.length);
  els.colCount.textContent = String(state.headers.length);
  els.filePath.textContent = state.path || "-";
  document.title = state.path ? `${state.path} - CSV 编辑器` : "CSV 编辑器";
}

function renderTable() {
  ensureStateShape();
  syncMeta();

  const table = els.table;
  table.innerHTML = "";
  const emptyState = els.emptyState;

  if (!state.headers.length && !state.rows.length) {
    emptyState.classList.remove("hidden");
    table.parentElement.classList.add("hidden");
    return;
  }

  emptyState.classList.add("hidden");
  table.parentElement.classList.remove("hidden");

  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");

  const indexHead = document.createElement("th");
  indexHead.className = "index-col";
  indexHead.textContent = "行号";
  headRow.appendChild(indexHead);

  state.headers.forEach((header, colIndex) => {
    const th = document.createElement("th");
    const input = document.createElement("input");
    input.value = header ?? "";
    input.title = input.value;
    input.addEventListener("input", () => {
      state.headers[colIndex] = input.value;
      input.title = input.value;
    });
    th.appendChild(input);
    headRow.appendChild(th);
  });

  thead.appendChild(headRow);
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  state.rows.forEach((row, rowIndex) => {
    const tr = document.createElement("tr");
    tr.className = "row-clickable";
    tr.title = "双击整行编辑";
    tr.addEventListener("dblclick", () => openRowModal(rowIndex));

    const indexCell = document.createElement("td");
    indexCell.className = "index-col";
    indexCell.textContent = String(rowIndex + 1);
    tr.appendChild(indexCell);

    state.headers.forEach((_, colIndex) => {
      const td = document.createElement("td");
      const text = row[colIndex] ?? "";
      td.textContent = text;
      td.title = text;
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });

  table.appendChild(tbody);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || response.statusText);
  }
  return response.json();
}

function currentTablePayload() {
  return {
    headers: state.headers.map((item) => item ?? ""),
    rows: state.rows.map((row) => state.headers.map((_, colIndex) => row[colIndex] ?? "")),
    encoding: state.encoding,
    delimiter: state.delimiter || ",",
  };
}

function addRow() {
  ensureWidth();
  state.rows.push(Array.from({ length: state.headers.length }, () => ""));
  renderTable();
  openRowModal(state.rows.length - 1);
}

function closeRowModal() {
  state.editingRowIndex = null;
  els.rowModal.classList.add("hidden");
  els.rowForm.innerHTML = "";
  els.rowSubtitle.textContent = "";
}

async function loadFiles(selectPath = "") {
  setStatus("正在读取文件列表...");
  const data = await api("/api/files");
  els.fileSelect.innerHTML = "";
  data.files
    .filter((item) => !item.error)
    .forEach((item) => {
      const option = document.createElement("option");
      option.value = item.path;
      option.textContent = `${item.path}  (${item.rowCount}x${item.columnCount})`;
      els.fileSelect.appendChild(option);
    });

  if (!els.fileSelect.options.length) {
    setStatus("未找到 CSV 文件", "error");
    return;
  }

  const path = selectPath || els.fileSelect.options[0].value;
  els.fileSelect.value = path;
  await loadFile(path);
}

async function loadFile(path) {
  if (!path) return;
  setStatus(`正在加载 ${path} ...`);
  const data = await api(`/api/file?path=${encodeURIComponent(path)}`);
  state.path = data.path;
  state.encoding = data.encoding || "gb18030";
  state.delimiter = data.delimiter || ",";
  state.headers = data.headers || [];
  state.rows = (data.rows || []).map((row) => row.slice());
  renderTable();
  setStatus(`已加载 ${path}`);
}

async function saveFile() {
  if (!state.path) return;
  setStatus("正在保存...");
  const payload = currentTablePayload();
  const result = await api(`/api/file?path=${encodeURIComponent(state.path)}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
  state.encoding = result.encoding || state.encoding;
  syncMeta();
  if (result.changed) {
    const logTip = result.logPath ? `，日志：${result.logPath}` : "";
    setStatus(`已保存 ${state.path}${logTip}`);
  } else {
    setStatus(`已保存 ${state.path}，但没有内容变化，所以没有新日志`);
  }
}

function ensureWidth() {
  if (!state.headers.length) {
    state.headers = ["列1"];
  }
  state.rows = state.rows.map((row) => {
    const next = row.slice(0, state.headers.length);
    while (next.length < state.headers.length) next.push("");
    return next;
  });
}

function deleteRow(index) {
  if (index < 0 || index >= state.rows.length) return;
  if (!window.confirm(`确定删除第 ${index + 1} 行吗？`)) return;
  state.rows.splice(index, 1);
  renderTable();
  closeRowModal();
}

function openRowModal(rowIndex) {
  if (rowIndex < 0 || rowIndex >= state.rows.length) return;
  ensureWidth();
  state.editingRowIndex = rowIndex;
  const row = state.rows[rowIndex];
  els.rowModal.classList.remove("hidden");
  els.rowSubtitle.textContent = `第 ${rowIndex + 1} 行`;
  els.rowForm.innerHTML = "";

  const grid = document.createElement("div");
  grid.className = "field-grid";

  state.headers.forEach((header, colIndex) => {
    const field = document.createElement("div");
    field.className = "field";
    const label = document.createElement("label");
    label.textContent = header || `列${colIndex + 1}`;
    const input = document.createElement("input");
    input.value = row[colIndex] ?? "";
    input.dataset.colIndex = String(colIndex);
    field.appendChild(label);
    field.appendChild(input);
    grid.appendChild(field);
  });

  els.rowForm.appendChild(grid);
}

function applyRowModal() {
  const rowIndex = state.editingRowIndex;
  if (rowIndex === null) return;
  const inputs = Array.from(els.rowForm.querySelectorAll("input"));
  const next = Array.from({ length: state.headers.length }, (_, index) => "");
  inputs.forEach((input) => {
    const colIndex = Number(input.dataset.colIndex);
    next[colIndex] = input.value;
  });
  state.rows[rowIndex] = next;
  renderTable();
  closeRowModal();
}

function bindEvents() {
  els.fileSelect.addEventListener("change", async () => {
    await loadFile(els.fileSelect.value);
  });

  els.refreshFiles.addEventListener("click", async () => {
    await loadFiles(state.path);
  });

  els.reloadFile.addEventListener("click", async () => {
    await loadFile(state.path || els.fileSelect.value);
  });

  els.addRow.addEventListener("click", addRow);
  els.save.addEventListener("click", async () => {
    try {
      await saveFile();
    } catch (err) {
      setStatus(`保存失败：${err.message}`, "error");
    }
  });

  els.closeModal.addEventListener("click", closeRowModal);
  els.cancelRow.addEventListener("click", closeRowModal);
  els.applyRow.addEventListener("click", applyRowModal);
  els.insertRow.addEventListener("click", () => {
    const index = state.editingRowIndex;
    ensureWidth();
    const blank = Array.from({ length: state.headers.length }, () => "");
    if (index === null || index < 0 || index >= state.rows.length) {
      state.rows.push(blank);
      renderTable();
      openRowModal(state.rows.length - 1);
      return;
    }
    state.rows.splice(index + 1, 0, blank);
    renderTable();
    openRowModal(index + 1);
  });
  els.deleteRow.addEventListener("click", () => {
    if (state.editingRowIndex !== null) deleteRow(state.editingRowIndex);
  });
  els.emptyAddRow.addEventListener("click", addRow);
  els.rowModal.addEventListener("click", (event) => {
    if (event.target?.dataset?.closeModal) closeRowModal();
  });
  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !els.rowModal.classList.contains("hidden")) closeRowModal();
  });
}

async function init() {
  els.status = document.getElementById("status");
  els.fileSelect = document.getElementById("file-select");
  els.refreshFiles = document.getElementById("refresh-files");
  els.reloadFile = document.getElementById("reload-file");
  els.addRow = document.getElementById("add-row");
  els.save = document.getElementById("save");
  els.encoding = document.getElementById("encoding");
  els.rowCount = document.getElementById("row-count");
  els.colCount = document.getElementById("col-count");
  els.filePath = document.getElementById("file-path");
  els.table = document.getElementById("csv-table");
  els.emptyState = document.getElementById("empty-state");
  els.rowModal = document.getElementById("row-modal");
  els.rowForm = document.getElementById("row-form");
  els.rowSubtitle = document.getElementById("row-modal-subtitle");
  els.emptyAddRow = document.getElementById("empty-add-row");
  els.closeModal = document.getElementById("close-modal");
  els.cancelRow = document.getElementById("cancel-row");
  els.applyRow = document.getElementById("apply-row");
  els.insertRow = document.getElementById("insert-row");
  els.deleteRow = document.getElementById("delete-row");

  bindEvents();
  try {
    await loadFiles();
  } catch (err) {
    setStatus(`初始化失败：${err.message}`, "error");
  }
}

init();
