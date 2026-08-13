(() => {
  const DATABASE_URL = "./projects.json";
  const SAVE_URL = "/api/projects";
  const STORAGE_KEY = "oci-architecture-projects:" + window.location.pathname;
  const PORTFOLIO_VERSION = "portfolio-v30";
  const list = document.querySelector("#architecture-list");
  const search = document.querySelector("#architecture-search");
  const frame = document.querySelector("#diagram-frame");
  const title = document.querySelector("#architecture-title");
  const pptxButton = document.querySelector("#download-pptx");
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

  let viewerToastTimer;
  function showViewerToast(message, isError = false) {
    let toast = document.querySelector(".viewer-toast");
    if (!toast) {
      toast = document.createElement("div");
      toast.className = "viewer-toast";
      toast.setAttribute("role", "status");
      toast.setAttribute("aria-live", "polite");
      document.body.append(toast);
    }
    toast.textContent = message;
    toast.classList.toggle("is-error", isError);
    toast.classList.add("is-visible");
    window.clearTimeout(viewerToastTimer);
    viewerToastTimer = window.setTimeout(() => toast.classList.remove("is-visible"), 3200);
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

  function projectListTitle(project) {
    const version = projectVersion(project);
    return project.title.replace(new RegExp("\\s+[\\u2014-]\\s+v" + version + "$", "i"), "");
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
      const viewer = frame.closest(".viewer");
      const headerHeight = viewer?.querySelector(".viewer-header")?.getBoundingClientRect().height || 0;
      const maxFrameHeight = Math.max(1, window.innerHeight - headerHeight);
      const maxFrameWidth = viewer?.clientWidth || window.innerWidth;
      const frameHeight = Math.min(maxFrameHeight, maxFrameWidth * 9 / 16);
      frame.style.width = Math.round(frameHeight * 16 / 9) + "px";
      frame.style.height = Math.round(frameHeight) + "px";
      return;
    }
    frame.style.width = "";
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

  function updatePptxAvailability() {
    const supportsPptx = frame.classList.contains("is-deck") && typeof frame.contentWindow?.ociRenderAllSlides === "function";
    pptxButton.hidden = !supportsPptx;
    pptxButton.disabled = !supportsPptx;
  }

  function prepareFrame() {
    resizeFrameToContent();
    updatePptxAvailability();
    window.setTimeout(resizeFrameToContent, 80);
    window.setTimeout(resizeFrameToContent, 240);
    window.setTimeout(updatePptxAvailability, 80);
    window.setTimeout(updatePptxAvailability, 240);
  }

  function currentProject() {
    return projects.find((project) => project.id === selectedId) || projects[0] || null;
  }

  function refreshProjectMetadata() {
    const selected = currentProject();
    if (!selected) return;
    title.textContent = selected.title;
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
    document.body.classList.toggle("showing-deck", isDeck);
    resizeFrameToContent();
    pptxButton.hidden = true;
    pptxButton.disabled = true;
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
      button.title = project.title;
      const name = document.createElement("span");
      name.className = "architecture-name";
      name.textContent = projectListTitle(project);
      const meta = document.createElement("span");
      meta.className = "architecture-version";
      meta.textContent = project.category + " · v" + projectVersion(project);
      meta.textContent = "v" + projectVersion(project);
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
    database.projects = projects;
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

  function escapeXml(value) {
    return String(value).replace(/[<>&'"]/g, (character) => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;", "'": "&apos;", '"': "&quot;" })[character]);
  }

  function pptxGroupShape() {
    return '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>';
  }

  function pptxSlideXml(slide, index) {
    const title = escapeXml(slide.title || "Slide " + (index + 1));
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld><p:spTree>' + pptxGroupShape() + '<p:pic><p:nvPicPr><p:cNvPr id="2" name="' + title + '"/><p:cNvPicPr/><p:nvPr/></p:nvPicPr><p:blipFill><a:blip r:embed="rId2" cstate="print"/><a:stretch><a:fillRect/></a:stretch></p:blipFill><p:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="12192000" cy="6858000"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic></p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>';
  }

  function pptxSlideRelationships(index) {
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/image' + (index + 1) + '.png"/></Relationships>';
  }

  function pptxThemeXml() {
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="OCI Theme"><a:themeElements><a:clrScheme name="OCI"><a:dk1><a:sysClr val="windowText" lastClr="000000"/></a:dk1><a:lt1><a:sysClr val="window" lastClr="FFFFFF"/></a:lt1><a:dk2><a:srgbClr val="172B4D"/></a:dk2><a:lt2><a:srgbClr val="F5F7FA"/></a:lt2><a:accent1><a:srgbClr val="C74634"/></a:accent1><a:accent2><a:srgbClr val="256273"/></a:accent2><a:accent3><a:srgbClr val="547A39"/></a:accent3><a:accent4><a:srgbClr val="5677A4"/></a:accent4><a:accent5><a:srgbClr val="8A6B3F"/></a:accent5><a:accent6><a:srgbClr val="666666"/></a:accent6><a:hlink><a:srgbClr val="0563C1"/></a:hlink><a:folHlink><a:srgbClr val="954F72"/></a:folHlink></a:clrScheme><a:fontScheme name="OCI"><a:majorFont><a:latin typeface="Aptos Display"/><a:ea typeface=""/><a:cs typeface=""/></a:majorFont><a:minorFont><a:latin typeface="Aptos"/><a:ea typeface=""/><a:cs typeface=""/></a:minorFont></a:fontScheme><a:fmtScheme name="OCI"><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="accent1"/></a:solidFill><a:solidFill><a:schemeClr val="lt1"/></a:solidFill></a:fillStyleLst><a:lnStyleLst><a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln><a:ln w="25400"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln><a:ln w="38100"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst><a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst><a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="lt1"/></a:solidFill><a:solidFill><a:schemeClr val="lt2"/></a:solidFill></a:bgFillStyleLst></a:fmtScheme></a:themeElements><a:objectDefaults/><a:extraClrSchemeLst/></a:theme>';
  }

  function pptxSlideMasterXml() {
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld name="OCI Architecture Diagram"><p:spTree>' + pptxGroupShape() + '</p:spTree></p:cSld><p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/><p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst><p:txStyles><p:titleStyle><a:lvl1pPr/></p:titleStyle><p:bodyStyle><a:lvl1pPr/></p:bodyStyle><p:otherStyle><a:defPPr/></p:otherStyle></p:txStyles></p:sldMaster>';
  }

  function buildPptx(slides, projectTitle) {
    const now = new Date().toISOString();
    const slideOverrides = slides.map((_, index) => '<Override PartName="/ppt/slides/slide' + (index + 1) + '.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>').join("");
    const slideIds = slides.map((_, index) => '<p:sldId id="' + (256 + index) + '" r:id="rId' + (index + 3) + '"/>').join("");
    const presentationRelationships = slides.map((_, index) => '<Relationship Id="rId' + (index + 3) + '" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide' + (index + 1) + '.xml"/>').join("");
    const files = [
      { name: "[Content_Types].xml", data: '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/><Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/><Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/><Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/><Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/><Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/><Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>' + slideOverrides + '</Types>' },
      { name: "_rels/.rels", data: '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/></Relationships>' },
      { name: "docProps/core.xml", data: '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>' + escapeXml(projectTitle) + '</dc:title><dc:creator>OCI Architecture Diagram</dc:creator><cp:lastModifiedBy>OCI Architecture Diagram</cp:lastModifiedBy><dcterms:created xsi:type="dcterms:W3CDTF">' + now + '</dcterms:created><dcterms:modified xsi:type="dcterms:W3CDTF">' + now + '</dcterms:modified></cp:coreProperties>' },
      { name: "docProps/app.xml", data: '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"><Application>OCI Architecture Diagram</Application><PresentationFormat>On-screen Show (16:9)</PresentationFormat><Slides>' + slides.length + '</Slides><Notes>0</Notes><HiddenSlides>0</HiddenSlides><MMClips>0</MMClips><ScaleCrop>false</ScaleCrop><Company>Oracle Cloud</Company><LinksUpToDate>false</LinksUpToDate><SharedDoc>false</SharedDoc><HyperlinksChanged>false</HyperlinksChanged><AppVersion>1.0</AppVersion></Properties>' },
      { name: "ppt/presentation.xml", data: '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst><p:sldIdLst>' + slideIds + '</p:sldIdLst><p:sldSz cx="12192000" cy="6858000" type="screen16x9"/><p:notesSz cx="6858000" cy="9144000"/><p:defaultTextStyle><a:defPPr><a:defRPr lang="en-US"/></a:defPPr></p:defaultTextStyle></p:presentation>' },
      { name: "ppt/_rels/presentation.xml.rels", data: '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="theme/theme1.xml"/>' + presentationRelationships + '</Relationships>' },
      { name: "ppt/slideMasters/slideMaster1.xml", data: pptxSlideMasterXml() },
      { name: "ppt/slideMasters/_rels/slideMaster1.xml.rels", data: '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/></Relationships>' },
      { name: "ppt/slideLayouts/slideLayout1.xml", data: '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank" preserve="1"><p:cSld name="Blank"><p:spTree>' + pptxGroupShape() + '</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>' },
      { name: "ppt/slideLayouts/_rels/slideLayout1.xml.rels", data: '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/></Relationships>' },
      { name: "ppt/theme/theme1.xml", data: pptxThemeXml() }
    ];
    slides.forEach((slide, index) => {
      files.push(
        { name: "ppt/slides/slide" + (index + 1) + ".xml", data: pptxSlideXml(slide, index) },
        { name: "ppt/slides/_rels/slide" + (index + 1) + ".xml.rels", data: pptxSlideRelationships(index) },
        { name: "ppt/media/image" + (index + 1) + ".png", data: slide.bytes }
      );
    });
    // ponytail: PPTX stores PNGs without DEFLATE to avoid a browser dependency; add compression only if download size becomes a concern.
    return zipStore(files);
  }

  function triggerDownload(blob, fileName) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = fileName;
    link.hidden = true;
    document.body.append(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  async function downloadPptx() {
    const renderSlides = frame.contentWindow?.ociRenderAllSlides;
    if (typeof renderSlides !== "function") {
      showViewerToast("No fue posible preparar las láminas para PowerPoint.", true);
      return;
    }
    pptxButton.disabled = true;
    try {
      const renderedSlides = await renderSlides();
      if (!Array.isArray(renderedSlides) || renderedSlides.length !== 3) throw new Error("No se generaron las tres láminas requeridas.");
      const slides = await Promise.all(renderedSlides.map(async (slide) => ({ ...slide, bytes: new Uint8Array(await slide.blob.arrayBuffer()) })));
      const project = currentProject();
      triggerDownload(buildPptx(slides, project?.title || "OCI Architecture Diagram"), safeFileName(project?.title || "oci-architecture-diagram") + ".pptx");
      showViewerToast("PPTX generado con Use Case, Architecture y BoM.");
    } catch (error) {
      console.error(error);
      showViewerToast(error.message || "No fue posible generar el PPTX.", true);
    } finally {
      pptxButton.disabled = false;
    }
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
  pptxButton.addEventListener("click", async () => {
    if (await confirmAction("Descargar PowerPoint", "¿Deseas descargar un PPTX con Use Case, Architecture y BoM?", "Descargar")) downloadPptx();
  });
  exportButton.addEventListener("click", requestExport);
  title.addEventListener("dblclick", () => beginInlineEdit(title, "title"));
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
