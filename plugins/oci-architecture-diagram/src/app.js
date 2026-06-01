(() => {
  const architectures = window.OCI_ARCHITECTURES || [];
  const list = document.querySelector("#architecture-list");
  const search = document.querySelector("#architecture-search");
  const frame = document.querySelector("#diagram-frame");
  const title = document.querySelector("#architecture-title");
  const summary = document.querySelector("#architecture-summary");
  const menu = document.querySelector("#architecture-menu");
  const menuToggle = document.querySelector("#menu-toggle");
  const menuBackdrop = document.querySelector("#menu-backdrop");
  let selectedId = new URLSearchParams(window.location.search).get("diagram") || architectures[0]?.id || "";

  function normalize(value) {
    return value.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  }

  function embeddedPath(path) {
    const url = new URL(path, window.location.href);
    url.searchParams.set("embed", "1");
    return `${url.pathname}${url.search}`;
  }

  function setMenuOpen(isOpen) {
    document.body.classList.toggle("menu-open", isOpen);
    menuToggle.setAttribute("aria-expanded", String(isOpen));
  }

  function hideRepeatedFrameTitle() {
    try {
      const doc = frame.contentDocument;
      const frameTitle = doc?.querySelector("main > header h1");
      if (frameTitle && normalize(frameTitle.textContent || "") === normalize(title.textContent || "")) {
        doc.body.classList.add("embedded");
        const repeatedHeader = frameTitle.closest("header");
        if (repeatedHeader) repeatedHeader.style.display = "none";
      }
    } catch (_error) {
      // Cross-origin frames are not expected in the local gallery, but the viewer should still work.
    }
  }

  function resizeFrameToContent() {
    try {
      const doc = frame.contentDocument;
      if (!doc) return;

      doc.documentElement.style.overflowY = "hidden";
      doc.body.style.overflowY = "hidden";
      const contentHeight = Math.max(
        doc.body.scrollHeight,
        doc.documentElement.scrollHeight,
        doc.body.offsetHeight,
        doc.documentElement.offsetHeight
      );
      frame.style.height = `${contentHeight}px`;
    } catch (_error) {
      frame.style.height = "";
    }
  }

  function prepareFrame() {
    hideRepeatedFrameTitle();
    resizeFrameToContent();
    window.setTimeout(resizeFrameToContent, 80);
    window.setTimeout(resizeFrameToContent, 240);
  }

  function selectArchitecture(id, pushState = true) {
    const selected = architectures.find((item) => item.id === id) || architectures[0];
    if (!selected) return;

    selectedId = selected.id;
    title.textContent = selected.title;
    summary.textContent = selected.summary;
    frame.src = embeddedPath(selected.path);

    document.querySelectorAll(".architecture-button").forEach((button) => {
      button.classList.toggle("is-active", button.dataset.architectureId === selected.id);
    });

    if (pushState) {
      const url = new URL(window.location.href);
      url.searchParams.set("diagram", selected.id);
      window.history.replaceState({}, "", url);
    }
  }

  function renderList(filter = "") {
    const query = normalize(filter.trim());
    const items = architectures.filter((item) => {
      const content = normalize(`${item.title} ${item.category} ${item.summary}`);
      return !query || content.includes(query);
    });

    list.textContent = "";
    if (!items.length) {
      const empty = document.createElement("p");
      empty.className = "empty-state";
      empty.textContent = "No results";
      list.append(empty);
      return;
    }

    items.forEach((item) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "architecture-button";
      button.dataset.architectureId = item.id;
      button.innerHTML = `
        <span class="architecture-name">${item.title}</span>
        <span class="architecture-meta">${item.category}</span>
      `;
      button.addEventListener("click", () => {
        selectArchitecture(item.id);
        setMenuOpen(false);
      });
      list.append(button);
    });

    selectArchitecture(items.some((item) => item.id === selectedId) ? selectedId : items[0].id, false);
  }

  search.addEventListener("input", () => renderList(search.value));
  frame.addEventListener("load", prepareFrame);
  window.addEventListener("resize", resizeFrameToContent);
  menuToggle.addEventListener("click", () => setMenuOpen(!document.body.classList.contains("menu-open")));
  menuBackdrop.addEventListener("click", () => setMenuOpen(false));
  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape") setMenuOpen(false);
  });
  window.addEventListener("popstate", () => {
    selectedId = new URLSearchParams(window.location.search).get("diagram") || selectedId;
    renderList(search.value);
  });

  renderList();
})();
