(() => {
  const DATABASE_URL = "./projects.json";
  const SAVE_URL = "/api/projects";
  const STORAGE_KEY = "oci-architecture-projects:" + window.location.pathname;
  const PORTFOLIO_VERSION = "portfolio-v12";
  const list = document.querySelector("#architecture-list");
  const search = document.querySelector("#architecture-search");
  const frame = document.querySelector("#diagram-frame");
  const title = document.querySelector("#architecture-title");
  const summary = document.querySelector("#architecture-summary");
  const copySlideButton = document.querySelector("#copy-slide");
  const menuToggle = document.querySelector("#menu-toggle");
  const menuBackdrop = document.querySelector("#menu-backdrop");
  const exportButton = document.querySelector("#export-projects");
  const exportLabel = exportButton.querySelector("span");
  const status = document.querySelector("#project-status");
  const confirmationDialog = document.querySelector("#action-confirmation");
  const confirmationTitle = document.querySelector("#confirmation-title");
  const confirmationMessage = document.querySelector("#confirmation-message");
  const confirmationButton = document.querySelector("#confirm-action");
  const selectedForExport = new Set();
  let database = { version: 1, updatedAt: "", projects: [] };
  let projects = [];
  let selectedId = new URLSearchParams(window.location.search).get("diagram") || "";

  function normalize(value) {
    return String(value || "").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  }

  function setStatus(message, isError = false) {
    status.textContent = message;
    status.classList.toggle("is-error", isError);
  }

  function updateExportControl() {
    const count = selectedForExport.size;
    exportButton.disabled = count === 0;
    exportLabel.textContent = count ? "Exportar ZIP (" + count + ")" : "Exportar ZIP";
  }

  function confirmAction(heading, message, confirmLabel) {
    if (!confirmationDialog?.showModal) return Promise.resolve(window.confirm(message));
    confirmationTitle.textContent = heading;
    confirmationMessage.textContent = message;
    confirmationButton.textContent = confirmLabel;
    return new Promise((resolve) => {
      confirmationDialog.addEventListener("close", () => resolve(confirmationDialog.returnValue === "confirm"), { once: true });
      confirmationDialog.showModal();
    });
  }

  function projectVersion(project) {
    return Number.isInteger(project.version) && project.version > 0 ? project.version : 1;
  }

  function normalizeDatabase(value) {
    const inputProjects = Array.isArray(value?.projects) ? value.projects : [];
    return {
      version: 1,
      updatedAt: typeof value?.updatedAt === "string" ? value.updatedAt : "",
      projects: inputProjects.map((project, index) => ({
        id: String(project.id || "project-" + (index + 1)),
        familyId: String(project.familyId || project.id || "project-" + (index + 1)),
        version: projectVersion(project),
        title: String(project.title || "Proyecto OCI"),
        description: String(project.description || project.summary || ""),
        category: String(project.category || "Proyecto OCI"),
        format: project.format === "deck" ? "deck" : "diagram",
        path: String(project.path || ""),
        updatedAt: typeof project.updatedAt === "string" ? project.updatedAt : ""
      }))
    };
  }

  function databaseTimestamp(value) {
    const timestamp = Date.parse(value?.updatedAt || "");
    return Number.isFinite(timestamp) ? timestamp : 0;
  }

  async function loadDatabase() {
    const embeddedElement = document.querySelector("#project-database");
    let loaded = null;
    try {
      const embedded = JSON.parse(embeddedElement?.textContent || "{}");
      if (Array.isArray(embedded.projects) && embedded.projects.length) loaded = normalizeDatabase(embedded);
    } catch (_error) {
      // A portable package can omit embedded data and fall through to projects.json.
    }
    if (!loaded) {
      try {
        const response = await fetch(DATABASE_URL, { cache: "no-store" });
        if (!response.ok) throw new Error("projects.json unavailable");
        loaded = normalizeDatabase(await response.json());
      } catch (_error) {
        const legacy = Array.isArray(window.OCI_ARCHITECTURES) ? window.OCI_ARCHITECTURES : [];
        loaded = normalizeDatabase({ projects: legacy });
      }
    }
    try {
      const stored = normalizeDatabase(JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}"));
      if (stored.projects.length && databaseTimestamp(stored) > databaseTimestamp(loaded)) loaded = stored;
    } catch (_error) {
      // Invalid local state must never prevent the JSON database from loading.
    }
    return loaded;
  }

  async function persistDatabase(message) {
    database.updatedAt = new Date().toISOString();
    localStorage.setItem(STORAGE_KEY, JSON.stringify(database));
    try {
      const response = await fetch(SAVE_URL, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(database, null, 2)
      });
      if (!response.ok) throw new Error("JSON persistence unavailable");
      setStatus(message + " Guardado en projects.json.");
      return true;
    } catch (_error) {
      setStatus(message + " Guardado localmente; se incluirá en el ZIP.");
      return false;
    }
  }

  function embeddedPath(path) {
    const url = new URL(path, window.location.href);
    url.searchParams.set("embed", "1");
    url.searchParams.set("v", PORTFOLIO_VERSION);
    const tab = new URLSearchParams(window.location.search).get("tab");
    if (tab) url.searchParams.set("tab", tab);
    return url.pathname + url.search;
  }

  function setMenuOpen(isOpen) {
    document.body.classList.toggle("menu-open", isOpen);
    menuToggle.setAttribute("aria-expanded", String(isOpen));
  }

  function resizeFrameToContent() {
    if (frame.classList.contains("is-deck")) {
      frame.style.height = "";
      return;
    }
    try {
      const doc = frame.contentDocument;
      if (!doc) return;
      doc.documentElement.style.overflowY = "hidden";
      doc.body.style.overflowY = "hidden";
      frame.style.height = Math.max(doc.body.scrollHeight, doc.documentElement.scrollHeight) + "px";
    } catch (_error) {
      frame.style.height = "";
    }
  }

  function prepareFrame() {
    resizeFrameToContent();
    const supportsCapture = frame.classList.contains("is-deck") && Boolean(frame.contentDocument?.querySelector("[data-capture-enabled]"));
    copySlideButton.hidden = !supportsCapture;
    copySlideButton.disabled = !supportsCapture;
    window.setTimeout(resizeFrameToContent, 80);
    window.setTimeout(resizeFrameToContent, 240);
  }

  function currentProject() {
    return projects.find((project) => project.id === selectedId) || projects[0] || null;
  }

  function refreshProjectMetadata() {
    const selected = currentProject();
    if (!selected) return;
    title.textContent = selected.title;
    summary.textContent = selected.description;
    document.querySelectorAll(".architecture-button").forEach((button) => {
      const isActive = button.dataset.architectureId === selected.id;
      button.classList.toggle("is-active", isActive);
      button.closest(".project-row")?.classList.toggle("is-active", isActive);
    });
  }

  function selectProject(id, pushState = true) {
    const selected = projects.find((project) => project.id === id) || projects[0];
    if (!selected) return;
    selectedId = selected.id;
    refreshProjectMetadata();
    const isDeck = selected.format === "deck" || selected.path.endsWith("-case-deck.html");
    frame.classList.toggle("is-deck", isDeck);
    copySlideButton.hidden = true;
    copySlideButton.disabled = true;
    frame.src = embeddedPath(selected.path);
    if (pushState) {
      const url = new URL(window.location.href);
      url.searchParams.set("diagram", selected.id);
      window.history.replaceState({}, "", url);
    }
  }

  function renderList(filter = "") {
    const query = normalize(filter.trim());
    const visible = projects.filter((project) => !query || normalize(project.title + " " + project.category + " " + project.description).includes(query));
    list.textContent = "";
    if (!visible.length) {
      const empty = document.createElement("p");
      empty.className = "empty-state";
      empty.textContent = "No hay resultados";
      list.append(empty);
      return;
    }
    visible.forEach((project) => {
      const row = document.createElement("article");
      row.className = "project-row";
      const selectionLabel = document.createElement("label");
      selectionLabel.className = "project-selection";
      selectionLabel.title = "Seleccionar " + project.title + " para exportar";
      const selection = document.createElement("input");
      selection.type = "checkbox";
      selection.checked = selectedForExport.has(project.id);
      selection.setAttribute("aria-label", "Seleccionar " + project.title + " para compartir");
      selection.addEventListener("change", () => {
        if (selection.checked) selectedForExport.add(project.id);
        else selectedForExport.delete(project.id);
        updateExportControl();
      });
      selectionLabel.append(selection);
      const button = document.createElement("button");
      button.type = "button";
      button.className = "architecture-button";
      button.dataset.architectureId = project.id;
      const name = document.createElement("span");
      name.className = "architecture-name";
      name.textContent = project.title;
      const meta = document.createElement("span");
      meta.className = "architecture-meta";
      meta.textContent = project.category + " · v" + projectVersion(project);
      button.append(name, meta);
      button.addEventListener("click", () => {
        selectProject(project.id);
        setMenuOpen(false);
      });
      button.addEventListener("dblclick", (event) => {
        event.preventDefault();
        selectProject(project.id);
        setMenuOpen(false);
        beginInlineEdit(title, "title");
      });
      const duplicate = document.createElement("button");
      duplicate.type = "button";
      duplicate.className = "duplicate-project";
      duplicate.title = "Duplicar " + project.title;
      duplicate.setAttribute("aria-label", "Duplicar " + project.title);
      duplicate.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 8h11v11H8zM5 16H4V5h11v1" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/></svg>';
      duplicate.addEventListener("click", async (event) => {
        event.stopPropagation();
        if (await confirmAction("Duplicar proyecto", "¿Deseas crear una nueva versión de \"" + project.title + "\"?", "Duplicar")) {
          duplicateProject(project);
        }
      });
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "delete-project";
      remove.title = "Eliminar " + project.title;
      remove.setAttribute("aria-label", "Eliminar " + project.title);
      remove.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 7h14m-9 4v6m4-6v6M9 7l1-3h4l1 3m-9 0 1 13h10l1-13" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/></svg>';
      remove.addEventListener("click", async (event) => {
        event.stopPropagation();
        if (await confirmAction("Eliminar proyecto", "¿Deseas eliminar \"" + project.title + "\" de la lista de proyectos?", "Eliminar")) {
          deleteProject(project);
        }
      });
      const actions = document.createElement("div");
      actions.className = "project-row-actions";
      actions.append(duplicate, remove);
      row.append(selectionLabel, button, actions);
      list.append(row);
    });
    refreshProjectMetadata();
    updateExportControl();
  }

  function beginInlineEdit(element, field) {
    const project = currentProject();
    if (!project || element.isContentEditable) return;
    const original = project[field];
    let finished = false;
    element.contentEditable = "true";
    element.classList.add("is-editing");
    element.focus();
    const selection = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(element);
    selection.removeAllRanges();
    selection.addRange(range);
    async function finish(save) {
      if (finished) return;
      finished = true;
      element.contentEditable = "false";
      element.classList.remove("is-editing");
      const value = element.textContent.trim();
      if (!save || !value) {
        element.textContent = original;
        return;
      }
      if (value === original) return;
      const fieldLabel = field === "title" ? "nombre" : "descripción";
      if (!await confirmAction("Guardar cambios", "¿Deseas guardar el " + fieldLabel + " actualizado de \"" + project.title + "\"?", "Guardar")) {
        element.textContent = original;
        return;
      }
      project[field] = value;
      project.updatedAt = new Date().toISOString();
      renderList(search.value);
      refreshProjectMetadata();
      await persistDatabase(field === "title" ? "Nombre actualizado." : "Descripción actualizada.");
    }
    element.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        finish(false);
      } else if (event.key === "Enter") {
        event.preventDefault();
        finish(true);
      }
    }, { once: false });
    element.addEventListener("blur", () => finish(true), { once: true });
  }

  async function duplicateProject(source = currentProject()) {
    if (!source) return;
    const familyId = source.familyId || source.id;
    const nextVersion = Math.max(...projects.filter((project) => (project.familyId || project.id) === familyId).map(projectVersion), 0) + 1;
    const baseTitle = source.baseTitle || source.title.replace(/\s+[—-]\s+v\d+$/i, "");
    let id = familyId + "-v" + nextVersion;
    let suffix = 2;
    while (projects.some((project) => project.id === id)) id = familyId + "-v" + nextVersion + "-" + suffix++;
    const duplicate = {
      ...source,
      id,
      familyId,
      baseTitle,
      version: nextVersion,
      title: baseTitle + " — v" + nextVersion,
      path: window.location.protocol === "file:" ? source.path : "../examples/" + id + ".html",
      updatedAt: new Date().toISOString()
    };
    projects.push(duplicate);
    selectedId = duplicate.id;
    const persisted = await persistDatabase("Versión v" + nextVersion + " creada.");
    if (!persisted) {
      duplicate.path = source.path;
      database.updatedAt = new Date().toISOString();
      localStorage.setItem(STORAGE_KEY, JSON.stringify(database));
    }
    renderList(search.value);
    selectProject(duplicate.id);
  }

  async function deleteProject(project) {
    if (!project || projects.length < 2) {
      setStatus("Debe mantenerse al menos un proyecto.", true);
      return;
    }
    const nextProject = projects.find((item) => item.id !== project.id);
    projects = projects.filter((item) => item.id !== project.id);
    selectedForExport.delete(project.id);
    if (selectedId === project.id) selectedId = nextProject.id;
    await persistDatabase("Proyecto eliminado.");
    renderList(search.value);
    selectProject(selectedId);
  }

  function crc32(bytes) {
    let crc = 0xffffffff;
    for (const byte of bytes) {
      crc ^= byte;
      for (let bit = 0; bit < 8; bit++) crc = (crc >>> 1) ^ ((crc & 1) ? 0xedb88320 : 0);
    }
    return (crc ^ 0xffffffff) >>> 0;
  }

  function dosDateTime(date) {
    const year = Math.max(1980, date.getFullYear());
    return {
      time: (date.getHours() << 11) | (date.getMinutes() << 5) | Math.floor(date.getSeconds() / 2),
      date: ((year - 1980) << 9) | ((date.getMonth() + 1) << 5) | date.getDate()
    };
  }

  function joinBytes(parts) {
    const output = new Uint8Array(parts.reduce((total, part) => total + part.length, 0));
    let offset = 0;
    for (const part of parts) {
      output.set(part, offset);
      offset += part.length;
    }
    return output;
  }

  function zipStore(files) {
    const encoder = new TextEncoder();
    const localParts = [];
    const centralParts = [];
    const stamp = dosDateTime(new Date());
    let offset = 0;
    files.forEach((file) => {
      const name = encoder.encode(file.name.replace(/\\/g, "/"));
      const data = file.data instanceof Uint8Array ? file.data : encoder.encode(String(file.data));
      const crc = crc32(data);
      const local = new Uint8Array(30);
      const localView = new DataView(local.buffer);
      localView.setUint32(0, 0x04034b50, true);
      localView.setUint16(4, 20, true);
      localView.setUint16(6, 0x0800, true);
      localView.setUint16(10, stamp.time, true);
      localView.setUint16(12, stamp.date, true);
      localView.setUint32(14, crc, true);
      localView.setUint32(18, data.length, true);
      localView.setUint32(22, data.length, true);
      localView.setUint16(26, name.length, true);
      localParts.push(local, name, data);
      const central = new Uint8Array(46);
      const centralView = new DataView(central.buffer);
      centralView.setUint32(0, 0x02014b50, true);
      centralView.setUint16(4, 20, true);
      centralView.setUint16(6, 20, true);
      centralView.setUint16(8, 0x0800, true);
      centralView.setUint16(12, stamp.time, true);
      centralView.setUint16(14, stamp.date, true);
      centralView.setUint32(16, crc, true);
      centralView.setUint32(20, data.length, true);
      centralView.setUint32(24, data.length, true);
      centralView.setUint16(28, name.length, true);
      centralView.setUint32(42, offset, true);
      centralParts.push(central, name);
      offset += local.length + name.length + data.length;
    });
    const localData = joinBytes(localParts);
    const centralData = joinBytes(centralParts);
    const end = new Uint8Array(22);
    const endView = new DataView(end.buffer);
    endView.setUint32(0, 0x06054b50, true);
    endView.setUint16(8, files.length, true);
    endView.setUint16(10, files.length, true);
    endView.setUint32(12, centralData.length, true);
    endView.setUint32(16, localData.length, true);
    return new Blob([localData, centralData, end], { type: "application/zip" });
  }

  function safeFileName(value) {
    return normalize(value).replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "project";
  }

  async function fetchBytes(path) {
    const response = await fetch(path, { cache: "no-store" });
    if (!response.ok) throw new Error("No se pudo incluir " + path);
    return new Uint8Array(await response.arrayBuffer());
  }

  async function exportSelectedProjects() {
    const selected = projects.filter((project) => selectedForExport.has(project.id));
    if (!selected.length) {
      return;
    }
    if (window.location.protocol === "http:" && ["127.0.0.1", "localhost", "::1"].includes(window.location.hostname)) {
      const link = document.createElement("a");
      link.href = "/api/export?ids=" + encodeURIComponent(selected.map((project) => project.id).join(","));
      link.download = "oci-architecture-projects.zip";
      link.hidden = true;
      document.body.append(link);
      link.click();
      link.remove();
      setStatus(selected.length + " proyecto(s) enviado(s) al ZIP portable.");
      return;
    }
    exportButton.disabled = true;
    setStatus("Preparando paquete portable…");
    try {
      const encoder = new TextEncoder();
      const portableProjects = [];
      const files = [];
      for (const project of selected) {
        const fileName = safeFileName(project.id) + ".html";
        files.push({ name: "examples/" + fileName, data: await fetchBytes(project.path) });
        portableProjects.push({ ...project, path: "../examples/" + fileName });
      }
      const portableDatabase = { version: 1, updatedAt: new Date().toISOString(), projects: portableProjects };
      const databaseText = JSON.stringify(portableDatabase, null, 2);
      const [indexResponse, appBytes, stylesBytes, iconBytes] = await Promise.all([
        fetch("./index.html", { cache: "no-store" }).then((response) => response.text()),
        fetchBytes("./app.js"),
        fetchBytes("./styles.css"),
        fetchBytes("../assets/icon.svg")
      ]);
      const embeddedDatabase = JSON.stringify(portableDatabase).replace(/</g, "\\u003c");
      const portableIndex = indexResponse.replace(
        /<script id="project-database" type="application\/json">[\s\S]*?<\/script>/,
        "<script id=\"project-database\" type=\"application/json\">" + embeddedDatabase + "</script>"
      );
      files.push(
        { name: "src/index.html", data: encoder.encode(portableIndex) },
        { name: "src/app.js", data: appBytes },
        { name: "src/styles.css", data: stylesBytes },
        { name: "src/projects.json", data: encoder.encode(databaseText) },
        { name: "assets/icon.svg", data: iconBytes },
        { name: "README.txt", data: encoder.encode("OCI Architecture Projects\r\n\r\nAbra src/index.html para navegar los proyectos HTML incluidos. Para persistir ediciones directamente en projects.json, sirva la carpeta con serve_architecture_site.py.\r\n") }
      );
      const blob = zipStore(files);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "oci-architecture-projects-" + new Date().toISOString().slice(0, 10) + ".zip";
      link.hidden = true;
      document.body.append(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      setStatus(selected.length + " proyecto(s) exportado(s) con projects.json.");
    } catch (error) {
      setStatus(error.message || "No fue posible generar el ZIP.", true);
      console.error(error);
    } finally {
      updateExportControl();
    }
  }

  async function requestExport() {
    const count = selectedForExport.size;
    if (!count) return;
    const label = count === 1 ? "el proyecto seleccionado" : count + " proyectos seleccionados";
    if (await confirmAction("Descargar ZIP", "¿Deseas descargar un archivo ZIP con " + label + "?", "Descargar")) {
      exportSelectedProjects();
    }
  }

  search.addEventListener("input", () => renderList(search.value));
  frame.addEventListener("load", prepareFrame);
  window.addEventListener("resize", resizeFrameToContent);
  menuToggle.addEventListener("click", () => setMenuOpen(!document.body.classList.contains("menu-open")));
  menuBackdrop.addEventListener("click", () => setMenuOpen(false));
  copySlideButton.addEventListener("click", () => {
    const copySlide = frame.contentWindow?.ociCopyActiveSlide;
    if (typeof copySlide === "function") copySlide();
    else frame.contentWindow?.postMessage({ type: "oci-copy-active-slide" }, window.location.origin);
  });
  exportButton.addEventListener("click", requestExport);
  title.addEventListener("dblclick", () => beginInlineEdit(title, "title"));
  summary.addEventListener("dblclick", () => beginInlineEdit(summary, "description"));
  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !document.querySelector("[contenteditable=true]")) setMenuOpen(false);
  });
  window.addEventListener("popstate", () => {
    selectedId = new URLSearchParams(window.location.search).get("diagram") || selectedId;
    selectProject(selectedId, false);
    renderList(search.value);
  });

  (async () => {
    database = await loadDatabase();
    projects = database.projects;
    if (!projects.some((project) => project.id === selectedId)) selectedId = projects[0]?.id || "";
    renderList();
    selectProject(selectedId, false);
    setStatus("");
  })();
})();
