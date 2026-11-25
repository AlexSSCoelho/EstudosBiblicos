(function () {
  "use strict";

  const dataEl = document.getElementById("sermon-editor-data");
  if (!dataEl) return;

  let sermonData;
  try {
    sermonData = JSON.parse(dataEl.textContent || "{}");
  } catch {
    return;
  }
  if (!sermonData || !sermonData.id) return;

  const STORAGE_TOKEN = "estudos_gh_token_v1";
  const STORAGE_REPO = "estudos_gh_repo_v1";
  const STORAGE_BRANCH = "estudos_gh_branch_v1";
  const GENERAL_SECTION_ID = "__geral__";

  const authBtn = document.getElementById("sermon-auth-btn");
  const authorBar = document.getElementById("sermon-author-bar");
  const syncStatusEl = document.getElementById("sermon-sync-status");
  const generalNoteBtn = document.getElementById("sermon-general-note-btn");
  const allNotesBtn = document.getElementById("sermon-all-notes-btn");
  const notesCountEl = document.getElementById("sermon-notes-count");
  const editCurrentBtn = document.getElementById("sermon-edit-current-btn");
  const newRevisionBtn = document.getElementById("sermon-new-revision-btn");
  const generalNoteSlot = document.getElementById("sermon-general-note-slot");
  const studyBody = document.querySelector(".study-body");

  const state = {
    token: "",
    repo: sermonData.github_repo || "AlexSSCoelho/EstudosBiblicos",
    branch: sermonData.github_branch || "main",
    notesSha: null,
    notes: {},
    sections: [],
    sectionAnchors: new Map(),
    editingSections: new Set(),
    activeOverlay: null,
    lastFocused: null,
  };

  /* ------------------------------------------------------------------
   * Utilitários gerais e segurança
   * ------------------------------------------------------------------ */

  function readStorage(key) {
    try {
      return window.localStorage.getItem(key) || "";
    } catch {
      return "";
    }
  }

  function writeStorage(key, value) {
    try {
      if (value) window.localStorage.setItem(key, value);
      else window.localStorage.removeItem(key);
    } catch {
      // Ignora indisponibilidade de localStorage
    }
  }

  function escapeHtml(text) {
    return String(text || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function slugify(value) {
    return String(value || "")
      .normalize("NFKD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "");
  }

  function utf8ToBase64(text) {
    const bytes = new TextEncoder().encode(text);
    let binary = "";
    const chunkSize = 0x8000;
    for (let i = 0; i < bytes.length; i += chunkSize) {
      const slice = bytes.subarray(i, i + chunkSize);
      binary += String.fromCharCode.apply(null, slice);
    }
    return btoa(binary);
  }

  function base64ToUtf8(b64) {
    const clean = String(b64 || "").replace(/\s+/g, "");
    const binary = atob(clean);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i += 1) {
      bytes[i] = binary.charCodeAt(i);
    }
    return new TextDecoder("utf-8").decode(bytes);
  }

  function encodeRepoPath(repoPath) {
    return String(repoPath || "")
      .replace(/^\/+/, "")
      .split("/")
      .filter(Boolean)
      .map((segment) => encodeURIComponent(segment))
      .join("/");
  }

  function formatTimestampBr(iso) {
    if (!iso) return "";
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return "";
    const pad = (n) => String(n).padStart(2, "0");
    return (
      pad(date.getDate()) +
      "/" +
      pad(date.getMonth() + 1) +
      "/" +
      date.getFullYear() +
      " " +
      pad(date.getHours()) +
      ":" +
      pad(date.getMinutes())
    );
  }

  function yamlQuote(value) {
    const str = String(value || "").trim();
    if (/^[a-zA-Z0-9._-]+$/.test(str)) {
      return str;
    }
    return JSON.stringify(str);
  }

  function buildSermonMarkdown(meta, body) {
    const lines = ["---"];
    lines.push("id: " + yamlQuote(meta.id));
    lines.push("sermao_id: " + yamlQuote(meta.sermao_id));
    lines.push("revisao: " + yamlQuote(meta.revisao));
    lines.push("tipo: pregacao");
    lines.push("titulo: " + yamlQuote(meta.titulo));

    const optionalFields = [
      "passagem",
      "tema",
      "data",
      "igreja",
      "traducao",
      "resumo",
      "nota_revisao",
      "estudo_origem",
    ];
    optionalFields.forEach((field) => {
      const val = String(meta[field] || "").trim();
      if (val) {
        lines.push(field + ": " + yamlQuote(val));
      }
    });

    lines.push("---");
    lines.push("");
    const cleanedBody = String(body || "").replace(/\r\n/g, "\n").trim();
    return lines.join("\n") + cleanedBody + "\n";
  }

  function parseFrontMatterText(rawMarkdown) {
    const normalized = String(rawMarkdown || "").replace(/\r\n/g, "\n");
    const match = normalized.match(/^---\n([\s\S]*?)\n---\n?([\s\S]*)$/);
    if (!match) {
      return { meta: {}, body: normalized.trim() };
    }
    const meta = {};
    match[1].split("\n").forEach((line) => {
      const sep = line.indexOf(":");
      if (sep <= 0) return;
      const key = line.slice(0, sep).trim();
      let val = line.slice(sep + 1).trim();
      if (!key) return;
      if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
        try {
          val = val.startsWith('"') ? JSON.parse(val) : val.slice(1, -1);
        } catch {
          val = val.slice(1, -1);
        }
      }
      if (val === "null" || val === "~") val = "";
      meta[key] = val;
    });
    return { meta, body: match[2].trim() };
  }

  function renderSimpleMarkdownPreview(markdownText) {
    const lines = String(markdownText || "").replace(/\r\n/g, "\n").split("\n");
    const out = [];
    let paragraph = [];
    let listType = null;
    let quoteLines = [];

    function renderInline(raw) {
      let safe = escapeHtml(raw);
      safe = safe.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
      safe = safe.replace(/\*(.+?)\*/g, "<em>$1</em>");
      safe = safe.replace(/`([^`]+)`/g, "<code>$1</code>");
      return safe;
    }

    function flushParagraph() {
      if (!paragraph.length) return;
      out.push("<p>" + renderInline(paragraph.join(" ")) + "</p>");
      paragraph = [];
    }

    function flushList() {
      if (!listType) return;
      out.push("</" + listType + ">");
      listType = null;
    }

    function flushQuote() {
      if (!quoteLines.length) return;
      out.push("<blockquote><p>" + renderInline(quoteLines.join(" ")) + "</p></blockquote>");
      quoteLines = [];
    }

    lines.forEach((rawLine) => {
      const line = rawLine.trim();
      if (!line) {
        flushParagraph();
        flushList();
        flushQuote();
        return;
      }

      if (/^---+$/.test(line)) {
        flushParagraph();
        flushList();
        flushQuote();
        out.push("<hr>");
        return;
      }

      const heading = line.match(/^(#{1,4})\s+(.+)$/);
      if (heading) {
        flushParagraph();
        flushList();
        flushQuote();
        const level = Math.min(4, Math.max(2, heading[1].length));
        out.push("<h" + level + ">" + renderInline(heading[2]) + "</h" + level + ">");
        return;
      }

      const quote = line.match(/^>\s?(.*)$/);
      if (quote) {
        flushParagraph();
        flushList();
        quoteLines.push(quote[1]);
        return;
      }

      const ul = line.match(/^[-*]\s+(.+)$/);
      if (ul) {
        flushParagraph();
        flushQuote();
        if (listType && listType !== "ul") flushList();
        if (!listType) {
          listType = "ul";
          out.push("<ul>");
        }
        out.push("<li>" + renderInline(ul[1]) + "</li>");
        return;
      }

      const ol = line.match(/^\d+\.\s+(.+)$/);
      if (ol) {
        flushParagraph();
        flushQuote();
        if (listType && listType !== "ol") flushList();
        if (!listType) {
          listType = "ol";
          out.push("<ol>");
        }
        out.push("<li>" + renderInline(ol[1]) + "</li>");
        return;
      }

      flushList();
      flushQuote();
      paragraph.push(line);
    });

    flushParagraph();
    flushList();
    flushQuote();
    return out.join("\n") || '<p class="sermon-field-help">Nenhum conteúdo para pré-visualizar.</p>';
  }

  /* ------------------------------------------------------------------
   * Cliente GitHub Contents API
   * ------------------------------------------------------------------ */

  function githubHeaders(tokenOverride) {
    const token = tokenOverride !== undefined ? tokenOverride : state.token;
    return {
      Accept: "application/vnd.github+json",
      Authorization: "Bearer " + token,
      "X-GitHub-Api-Version": "2022-11-28",
    };
  }

  async function ghVerifyAccess(token, repo) {
    const url = "https://api.github.com/repos/" + repo;
    const resp = await fetch(url, {
      method: "GET",
      headers: githubHeaders(token),
      cache: "no-store",
    });
    if (!resp.ok) {
      const detail = await resp.json().catch(() => ({}));
      const msg = detail && detail.message ? detail.message : "HTTP " + resp.status;
      throw new Error("Não foi possível acessar o repositório (" + msg + ").");
    }
    const info = await resp.json();
    if (info.permissions && info.permissions.push === false) {
      throw new Error("Este token só tem permissão de leitura. Ative 'Contents: Read and write'.");
    }
    return info;
  }

  async function ghGetFile(repoPath) {
    const url =
      "https://api.github.com/repos/" +
      state.repo +
      "/contents/" +
      encodeRepoPath(repoPath) +
      "?ref=" +
      encodeURIComponent(state.branch);
    const resp = await fetch(url, {
      method: "GET",
      headers: githubHeaders(),
      cache: "no-store",
    });
    if (resp.status === 404) {
      return { exists: false, sha: null, content: null };
    }
    if (!resp.ok) {
      const detail = await resp.json().catch(() => ({}));
      const msg = detail && detail.message ? detail.message : "HTTP " + resp.status;
      const error = new Error(msg);
      error.status = resp.status;
      throw error;
    }
    const payload = await resp.json();
    return {
      exists: true,
      sha: payload.sha || null,
      content: payload.content ? base64ToUtf8(payload.content) : "",
    };
  }

  async function ghListDirectory(dirPath) {
    const url =
      "https://api.github.com/repos/" +
      state.repo +
      "/contents/" +
      encodeRepoPath(dirPath) +
      "?ref=" +
      encodeURIComponent(state.branch);
    const resp = await fetch(url, {
      method: "GET",
      headers: githubHeaders(),
      cache: "no-store",
    });
    if (!resp.ok) return [];
    const payload = await resp.json();
    return Array.isArray(payload) ? payload : [];
  }

  async function ghPutFile(repoPath, textContent, commitMessage, sha) {
    const url =
      "https://api.github.com/repos/" +
      state.repo +
      "/contents/" +
      encodeRepoPath(repoPath);
    const body = {
      message: commitMessage,
      content: utf8ToBase64(textContent),
      branch: state.branch,
    };
    if (sha) body.sha = sha;

    const resp = await fetch(url, {
      method: "PUT",
      headers: {
        ...githubHeaders(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    if (!resp.ok) {
      const detail = await resp.json().catch(() => ({}));
      const msg = detail && detail.message ? detail.message : "HTTP " + resp.status;
      const error = new Error(msg);
      error.status = resp.status;
      throw error;
    }
    return resp.json();
  }

  function notesFilePath() {
    return "anotacoes/" + sermonData.id + ".json";
  }

  function setSyncStatus(text) {
    if (syncStatusEl) syncStatusEl.textContent = text;
  }

  /* ------------------------------------------------------------------
   * Descoberta de seções e gerenciamento de notas por seção
   * ------------------------------------------------------------------ */

  function collectSections() {
    state.sections = [];
    if (!studyBody) return;
    const headings = Array.from(studyBody.querySelectorAll("h2, h3"));
    const usedIds = new Set();
    headings.forEach((heading, idx) => {
      let id = heading.id || slugify(heading.textContent) || "secao-" + (idx + 1);
      while (usedIds.has(id)) {
        id = id + "-" + (idx + 1);
      }
      usedIds.add(id);
      if (!heading.id) heading.id = id;
      state.sections.push({
        id,
        title: (heading.textContent || "").trim(),
        level: heading.tagName.toLowerCase(),
        element: heading,
      });
    });
  }

  function notesCount() {
    return Object.values(state.notes).filter((entry) => entry && String(entry.text || "").trim()).length;
  }

  function updateNotesCounter() {
    const count = notesCount();
    if (notesCountEl) notesCountEl.textContent = String(count);
    const hasGeneral = Boolean(
      state.notes[GENERAL_SECTION_ID] && String(state.notes[GENERAL_SECTION_ID].text || "").trim()
    );
    if (generalNoteBtn) {
      generalNoteBtn.textContent = hasGeneral ? "Nota geral (salva)" : "Nota geral";
    }
  }

  function unmountNoteAnchors() {
    state.sectionAnchors.forEach((anchor) => anchor.remove());
    state.sectionAnchors.clear();
    state.editingSections.clear();
    if (generalNoteSlot) {
      generalNoteSlot.innerHTML = "";
      generalNoteSlot.hidden = true;
    }
  }

  function mountNoteAnchors() {
    unmountNoteAnchors();
    state.sections.forEach((sec) => {
      const anchor = document.createElement("div");
      anchor.className = "sermon-note-anchor";
      anchor.dataset.sectionId = sec.id;
      sec.element.insertAdjacentElement("afterend", anchor);
      state.sectionAnchors.set(sec.id, anchor);
      renderSectionAnchor(sec.id);
    });
    renderGeneralNoteSlot();
  }

  function renderGeneralNoteSlot() {
    if (!generalNoteSlot) return;
    const note = state.notes[GENERAL_SECTION_ID];
    const isEditing = state.editingSections.has(GENERAL_SECTION_ID);
    if (!isEditing && (!note || !String(note.text || "").trim())) {
      generalNoteSlot.innerHTML = "";
      generalNoteSlot.hidden = true;
      return;
    }
    generalNoteSlot.hidden = false;
    renderAnchorContent(generalNoteSlot, GENERAL_SECTION_ID, "Anotações gerais da pregação", true);
  }

  function renderSectionAnchor(sectionId) {
    if (sectionId === GENERAL_SECTION_ID) {
      renderGeneralNoteSlot();
      return;
    }
    const anchor = state.sectionAnchors.get(sectionId);
    if (!anchor) return;
    const sec = state.sections.find((s) => s.id === sectionId);
    const title = sec ? sec.title : sectionId;
    renderAnchorContent(anchor, sectionId, title, false);
  }

  function renderAnchorContent(container, sectionId, sectionTitle, isGeneral) {
    const note = state.notes[sectionId];
    const existingText = note && note.text ? String(note.text) : "";
    const isEditing = state.editingSections.has(sectionId);
    container.innerHTML = "";

    if (isEditing) {
      const form = document.createElement("div");
      form.className = "sermon-note-form";

      const label = document.createElement("label");
      label.className = "sermon-note-form-label";
      const inputId = "note-input-" + sectionId;
      label.setAttribute("for", inputId);
      label.textContent = isGeneral
        ? "Anotações gerais (" + sermonData.revisao + ")"
        : "Nota da seção: " + sectionTitle;

      const textarea = document.createElement("textarea");
      textarea.className = "sermon-note-textarea";
      textarea.id = inputId;
      textarea.placeholder = isGeneral
        ? "Impressões gerais pós-pregação, tempo total, ideias para a próxima revisão..."
        : "Anote ajustes, ilustrações, referências ou pontos para melhorar nesta seção...";
      textarea.value = existingText;

      const actions = document.createElement("div");
      actions.className = "sermon-note-form-actions";

      const leftGroup = document.createElement("div");
      if (existingText.trim()) {
        const delBtn = document.createElement("button");
        delBtn.type = "button";
        delBtn.className = "sermon-btn sermon-btn--danger";
        delBtn.textContent = "Excluir nota";
        delBtn.addEventListener("click", () => {
          saveSectionNote(sectionId, sectionTitle, "", feedbackEl, [saveBtn, cancelBtn, delBtn]);
        });
        leftGroup.appendChild(delBtn);
      }

      const rightGroup = document.createElement("div");
      rightGroup.className = "sermon-note-form-right";

      const cancelBtn = document.createElement("button");
      cancelBtn.type = "button";
      cancelBtn.className = "sermon-btn sermon-btn--ghost";
      cancelBtn.textContent = "Cancelar";
      cancelBtn.addEventListener("click", () => {
        state.editingSections.delete(sectionId);
        renderSectionAnchor(sectionId);
      });

      const saveBtn = document.createElement("button");
      saveBtn.type = "button";
      saveBtn.className = "sermon-btn sermon-btn--primary";
      saveBtn.textContent = "Salvar no GitHub";
      saveBtn.addEventListener("click", () => {
        saveSectionNote(
          sectionId,
          sectionTitle,
          textarea.value,
          feedbackEl,
          [saveBtn, cancelBtn]
        );
      });

      rightGroup.appendChild(cancelBtn);
      rightGroup.appendChild(saveBtn);
      actions.appendChild(leftGroup);
      actions.appendChild(rightGroup);

      const feedbackEl = document.createElement("p");
      feedbackEl.className = "sermon-feedback-msg";
      feedbackEl.hidden = true;

      form.appendChild(label);
      form.appendChild(textarea);
      form.appendChild(actions);
      form.appendChild(feedbackEl);
      container.appendChild(form);
      textarea.focus();
      return;
    }

    if (existingText.trim()) {
      const card = document.createElement("div");
      card.className = "sermon-note-card";

      const head = document.createElement("div");
      head.className = "sermon-note-card-head";

      const kicker = document.createElement("span");
      kicker.className = "sermon-note-card-kicker";
      kicker.textContent = isGeneral ? "Anotações gerais" : "Nota da seção";

      const meta = document.createElement("div");
      meta.className = "sermon-note-card-meta";
      if (note.updated_at) {
        const timeEl = document.createElement("span");
        timeEl.textContent = formatTimestampBr(note.updated_at);
        meta.appendChild(timeEl);
      }

      const editBtn = document.createElement("button");
      editBtn.type = "button";
      editBtn.className = "sermon-note-inline-btn";
      editBtn.textContent = "Editar";
      editBtn.addEventListener("click", () => {
        state.editingSections.add(sectionId);
        renderSectionAnchor(sectionId);
      });
      meta.appendChild(editBtn);

      head.appendChild(kicker);
      head.appendChild(meta);

      const textEl = document.createElement("p");
      textEl.className = "sermon-note-card-text";
      textEl.textContent = existingText;

      card.appendChild(head);
      card.appendChild(textEl);
      container.appendChild(card);
      return;
    }

    const trigger = document.createElement("button");
    trigger.type = "button";
    trigger.className = "sermon-note-trigger";
    trigger.textContent = "+ Anotar nesta seção";
    trigger.addEventListener("click", () => {
      state.editingSections.add(sectionId);
      renderSectionAnchor(sectionId);
    });
    container.appendChild(trigger);
  }

  async function loadNotesFromGitHub() {
    setSyncStatus("Carregando anotações do GitHub...");
    try {
      const file = await ghGetFile(notesFilePath());
      if (file.exists && file.content) {
        const parsed = JSON.parse(file.content);
        state.notesSha = file.sha;
        state.notes = parsed && typeof parsed.sections === "object" && parsed.sections ? parsed.sections : {};
      } else {
        state.notesSha = null;
        state.notes = {};
      }
      updateNotesCounter();
      renderGeneralNoteSlot();
      state.sections.forEach((sec) => renderSectionAnchor(sec.id));
      const count = notesCount();
      setSyncStatus(
        count > 0
          ? "GitHub conectado · " + count + (count === 1 ? " nota sincronizada" : " notas sincronizadas")
          : "GitHub conectado · pronto para anotar"
      );
    } catch (err) {
      setSyncStatus("Erro ao ler notas: " + (err && err.message ? err.message : "falha de rede"));
    }
  }

  async function saveSectionNote(sectionId, sectionTitle, rawText, feedbackEl, buttonsToDisable) {
    const trimmed = String(rawText || "").trim();
    buttonsToDisable.forEach((btn) => {
      if (btn) btn.disabled = true;
    });
    if (feedbackEl) {
      feedbackEl.hidden = false;
      feedbackEl.className = "sermon-feedback-msg";
      feedbackEl.textContent = "Salvando no GitHub...";
    }

    const nowIso = new Date().toISOString();
    const attemptSave = async (isRetry) => {
      const nextSections = { ...state.notes };
      if (trimmed) {
        nextSections[sectionId] = {
          title: sectionTitle,
          text: trimmed,
          updated_at: nowIso,
        };
      } else {
        delete nextSections[sectionId];
      }

      const payload = {
        version: 1,
        study_id: sermonData.id,
        sermao_id: sermonData.sermao_id,
        revisao: sermonData.revisao,
        updated_at: nowIso,
        sections: nextSections,
      };
      const commitAction = trimmed ? "atualizar nota" : "remover nota";
      const commitMsg = "notes(pregacoes): " + commitAction + " em " + sermonData.id + " (" + sectionTitle + ")";
      try {
        const result = await ghPutFile(
          notesFilePath(),
          JSON.stringify(payload, null, 2) + "\n",
          commitMsg,
          state.notesSha
        );
        state.notesSha = result && result.content ? result.content.sha : state.notesSha;
        state.notes = nextSections;
        state.editingSections.delete(sectionId);
        updateNotesCounter();
        renderSectionAnchor(sectionId);
        setSyncStatus("Nota salva no GitHub às " + formatTimestampBr(nowIso).slice(11));
      } catch (err) {
        if (!isRetry && err && (err.status === 409 || err.status === 422)) {
          const latest = await ghGetFile(notesFilePath());
          state.notesSha = latest.sha;
          if (latest.exists && latest.content) {
            try {
              const parsed = JSON.parse(latest.content);
              state.notes = parsed && parsed.sections ? parsed.sections : {};
            } catch {
              // mantém estado atual
            }
          }
          return attemptSave(true);
        }
        throw err;
      }
    };

    try {
      await attemptSave(false);
    } catch (err) {
      if (feedbackEl) {
        feedbackEl.hidden = false;
        feedbackEl.className = "sermon-feedback-msg sermon-feedback-msg--err";
        feedbackEl.textContent = "Erro ao salvar: " + (err && err.message ? err.message : "falha de rede");
      }
      buttonsToDisable.forEach((btn) => {
        if (btn) btn.disabled = false;
      });
    }
  }

  /* ------------------------------------------------------------------
   * Controle de Modais / Drawer
   * ------------------------------------------------------------------ */

  let backdropEl = null;

  function ensureBackdrop() {
    if (!backdropEl) {
      backdropEl = document.createElement("div");
      backdropEl.className = "sermon-modal-backdrop";
      backdropEl.hidden = true;
      backdropEl.addEventListener("click", closeOverlay);
      document.body.appendChild(backdropEl);
    }
    return backdropEl;
  }

  function closeOverlay() {
    if (state.activeOverlay) {
      state.activeOverlay.remove();
      state.activeOverlay = null;
    }
    if (backdropEl) backdropEl.hidden = true;
    if (state.lastFocused && typeof state.lastFocused.focus === "function") {
      state.lastFocused.focus();
      state.lastFocused = null;
    }
  }

  function openOverlay(element) {
    closeOverlay();
    state.lastFocused = document.activeElement;
    const backdrop = ensureBackdrop();
    backdrop.hidden = false;
    state.activeOverlay = element;
    document.body.appendChild(element);
  }

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && state.activeOverlay) {
      closeOverlay();
    }
  });

  /* ------------------------------------------------------------------
   * Modal: Modo Autor (Configuração do Token do GitHub)
   * ------------------------------------------------------------------ */

  function openAuthModal() {
    const modal = document.createElement("section");
    modal.className = "sermon-modal";
    modal.id = "sermon-auth-modal";
    modal.setAttribute("role", "dialog");
    modal.setAttribute("aria-modal", "true");
    modal.setAttribute("aria-labelledby", "sermon-auth-title");

    modal.innerHTML =
      '<div class="sermon-modal-header">' +
      '  <div>' +
      '    <p class="sermon-modal-kicker">Acesso privado no navegador</p>' +
      '    <h2 id="sermon-auth-title">Modo autor (GitHub)</h2>' +
      '  </div>' +
      '  <button type="button" class="review-close-btn" id="sermon-modal-close" aria-label="Fechar">&times;</button>' +
      '</div>' +
      '<div class="sermon-modal-body">' +
      '  <p class="sermon-field-help" style="margin-top:0;margin-bottom:14px;">' +
      '    Conecte um <strong>Fine-grained Personal Access Token</strong> com permissão ' +
      '    <code>Contents: Read and write</code> apenas para este repositório. O token fica salvo somente neste navegador.' +
      '    <a href="https://github.com/settings/personal-access-tokens/new" target="_blank" rel="noopener noreferrer">Gerar token no GitHub</a>.' +
      '  </p>' +
      '  <div class="sermon-field">' +
      '    <label for="sermon-gh-token">Token do GitHub</label>' +
      '    <input type="password" class="sermon-field-input" id="sermon-gh-token" autocomplete="off" placeholder="github_pat_...">' +
      '  </div>' +
      '  <details style="margin-top:10px;">' +
      '    <summary style="cursor:pointer;font-size:.8rem;font-weight:700;color:var(--muted);">Opções avançadas (repositório e branch)</summary>' +
      '    <div style="margin-top:10px;">' +
      '      <div class="sermon-field">' +
      '        <label for="sermon-gh-repo">Repositório (owner/repo)</label>' +
      '        <input type="text" class="sermon-field-input" id="sermon-gh-repo">' +
      '      </div>' +
      '      <div class="sermon-field">' +
      '        <label for="sermon-gh-branch">Branch</label>' +
      '        <input type="text" class="sermon-field-input" id="sermon-gh-branch">' +
      '      </div>' +
      '    </div>' +
      '  </details>' +
      '  <p class="sermon-feedback-msg" id="sermon-auth-feedback" hidden></p>' +
      '</div>' +
      '<div class="sermon-modal-footer">' +
      '  <div>' +
      (state.token
        ? '<button type="button" class="sermon-btn sermon-btn--danger" id="sermon-auth-disconnect">Desconectar</button>'
        : "") +
      '  </div>' +
      '  <div class="sermon-note-form-right">' +
      '    <button type="button" class="sermon-btn sermon-btn--ghost" id="sermon-auth-cancel">Cancelar</button>' +
      '    <button type="button" class="sermon-btn sermon-btn--primary" id="sermon-auth-save">Testar e conectar</button>' +
      '  </div>' +
      '</div>';

    openOverlay(modal);

    const tokenInput = modal.querySelector("#sermon-gh-token");
    const repoInput = modal.querySelector("#sermon-gh-repo");
    const branchInput = modal.querySelector("#sermon-gh-branch");
    const feedback = modal.querySelector("#sermon-auth-feedback");
    const saveBtn = modal.querySelector("#sermon-auth-save");
    const disconnectBtn = modal.querySelector("#sermon-auth-disconnect");

    tokenInput.value = state.token;
    repoInput.value = state.repo;
    branchInput.value = state.branch;

    modal.querySelector("#sermon-modal-close").addEventListener("click", closeOverlay);
    modal.querySelector("#sermon-auth-cancel").addEventListener("click", closeOverlay);

    if (disconnectBtn) {
      disconnectBtn.addEventListener("click", () => {
        state.token = "";
        state.notes = {};
        state.notesSha = null;
        writeStorage(STORAGE_TOKEN, "");
        applyAuthorMode(false);
        closeOverlay();
      });
    }

    saveBtn.addEventListener("click", async () => {
      const token = tokenInput.value.trim();
      const repo = repoInput.value.trim() || sermonData.github_repo || "AlexSSCoelho/EstudosBiblicos";
      const branch = branchInput.value.trim() || sermonData.github_branch || "main";

      if (!token) {
        feedback.hidden = false;
        feedback.className = "sermon-feedback-msg sermon-feedback-msg--err";
        feedback.textContent = "Informe o token do GitHub para ativar o modo autor.";
        tokenInput.focus();
        return;
      }

      saveBtn.disabled = true;
      feedback.hidden = false;
      feedback.className = "sermon-feedback-msg";
      feedback.textContent = "Validando acesso ao repositório...";

      try {
        await ghVerifyAccess(token, repo);
        state.token = token;
        state.repo = repo;
        state.branch = branch;
        writeStorage(STORAGE_TOKEN, token);
        writeStorage(STORAGE_REPO, repo);
        writeStorage(STORAGE_BRANCH, branch);
        closeOverlay();
        await applyAuthorMode(true);
      } catch (err) {
        feedback.className = "sermon-feedback-msg sermon-feedback-msg--err";
        feedback.textContent = err && err.message ? err.message : "Falha ao validar token.";
        saveBtn.disabled = false;
      }
    });

    tokenInput.focus();
  }

  /* ------------------------------------------------------------------
   * Drawer: Resumo de Todas as Notas desta Revisão
   * ------------------------------------------------------------------ */

  function openAllNotesDrawer() {
    const drawer = document.createElement("aside");
    drawer.className = "sermon-notes-drawer";
    drawer.id = "sermon-notes-drawer";
    drawer.setAttribute("role", "dialog");
    drawer.setAttribute("aria-modal", "true");
    drawer.setAttribute("aria-labelledby", "sermon-notes-drawer-title");

    drawer.innerHTML =
      '<div class="sermon-modal-header">' +
      '  <div>' +
      '    <p class="sermon-modal-kicker">Anotações · ' + escapeHtml(sermonData.revisao) + '</p>' +
      '    <h2 id="sermon-notes-drawer-title">Todas as notas desta revisão</h2>' +
      '  </div>' +
      '  <button type="button" class="review-close-btn" id="sermon-drawer-close" aria-label="Fechar">&times;</button>' +
      '</div>' +
      '<div class="sermon-modal-body" id="sermon-notes-drawer-body"></div>' +
      '<div class="sermon-modal-footer">' +
      '  <span class="sermon-field-help" style="margin:0;">As notas são salvas em <code>' + escapeHtml(notesFilePath()) + '</code>.</span>' +
      '  <button type="button" class="sermon-btn sermon-btn--secondary" id="sermon-drawer-done">Fechar</button>' +
      '</div>';

    openOverlay(drawer);

    const body = drawer.querySelector("#sermon-notes-drawer-body");
    const orderedEntries = getOrderedNotes();

    if (!orderedEntries.length) {
      const empty = document.createElement("p");
      empty.className = "sermon-field-help";
      empty.textContent = "Ainda não há anotações nesta revisão. Clique em 'Nota geral' ou em '+ Anotar nesta seção' abaixo de qualquer título.";
      body.appendChild(empty);
    } else {
      orderedEntries.forEach((entry) => {
        const item = document.createElement("div");
        item.className = "sermon-notes-list-item";

        const heading = document.createElement("h3");
        heading.textContent = entry.title;

        const text = document.createElement("p");
        text.textContent = entry.text;

        const jumpBtn = document.createElement("button");
        jumpBtn.type = "button";
        jumpBtn.className = "sermon-note-inline-btn";
        jumpBtn.textContent = "Ir para seção e editar";
        jumpBtn.addEventListener("click", () => {
          closeOverlay();
          state.editingSections.add(entry.id);
          renderSectionAnchor(entry.id);
          const targetEl =
            entry.id === GENERAL_SECTION_ID
              ? generalNoteSlot
              : document.getElementById(entry.id);
          if (targetEl) targetEl.scrollIntoView({ behavior: "smooth", block: "center" });
        });

        item.appendChild(heading);
        item.appendChild(text);
        item.appendChild(jumpBtn);
        body.appendChild(item);
      });
    }

    drawer.querySelector("#sermon-drawer-close").addEventListener("click", closeOverlay);
    drawer.querySelector("#sermon-drawer-done").addEventListener("click", closeOverlay);
  }

  function getOrderedNotes() {
    const ordered = [];
    const seen = new Set();
    if (state.notes[GENERAL_SECTION_ID] && String(state.notes[GENERAL_SECTION_ID].text || "").trim()) {
      ordered.push({
        id: GENERAL_SECTION_ID,
        title: "Anotações gerais",
        text: state.notes[GENERAL_SECTION_ID].text,
        updated_at: state.notes[GENERAL_SECTION_ID].updated_at || "",
      });
      seen.add(GENERAL_SECTION_ID);
    }
    state.sections.forEach((sec) => {
      const entry = state.notes[sec.id];
      if (entry && String(entry.text || "").trim()) {
        ordered.push({
          id: sec.id,
          title: sec.title,
          text: entry.text,
          updated_at: entry.updated_at || "",
        });
        seen.add(sec.id);
      }
    });
    Object.keys(state.notes).forEach((key) => {
      if (seen.has(key)) return;
      const entry = state.notes[key];
      if (entry && String(entry.text || "").trim()) {
        ordered.push({
          id: key,
          title: entry.title || key,
          text: entry.text,
          updated_at: entry.updated_at || "",
        });
      }
    });
    return ordered;
  }

  /* ------------------------------------------------------------------
   * Modal: Editor de Revisão (Editar atual ou Criar R2/R3...)
   * ------------------------------------------------------------------ */

  async function resolveNextRevisionNumber() {
    let nextNum = Number(sermonData.next_revisao_numero || 2);
    try {
      const entries = await ghListDirectory(sermonData.source_dir);
      entries.forEach((entry) => {
        if (!entry || !entry.name) return;
        const match = String(entry.name).match(/^r([1-9]\d*)\.md$/i);
        if (match) {
          const found = parseInt(match[1], 10);
          if (found >= nextNum) nextNum = found + 1;
        }
      });
    } catch {
      // Usa o valor calculado no build caso a listagem falhe
    }
    return nextNum;
  }

  async function openRevisionEditor(mode) {
    const isNew = mode === "new";
    const referenceNotes = getOrderedNotes();

    const modal = document.createElement("section");
    modal.className = "sermon-modal sermon-modal--editor";
    modal.id = "sermon-editor-modal";
    modal.setAttribute("role", "dialog");
    modal.setAttribute("aria-modal", "true");
    modal.setAttribute("aria-labelledby", "sermon-editor-title");

    let targetRevNumber = Number(sermonData.revisao_numero || 1);
    let targetRevLabel = sermonData.revisao || "R1";
    let targetId = sermonData.id;
    let targetPath = sermonData.source_path;
    let currentSha = null;

    let initialMeta = { ...sermonData.metadata };
    let initialBody = sermonData.body || "";

    modal.innerHTML =
      '<div class="sermon-modal-header">' +
      '  <div>' +
      '    <p class="sermon-modal-kicker" id="sermon-editor-kicker">Preparando editor...</p>' +
      '    <h2 id="sermon-editor-title">Carregando dados do GitHub...</h2>' +
      '  </div>' +
      '  <button type="button" class="review-close-btn" id="sermon-editor-close" aria-label="Fechar">&times;</button>' +
      '</div>' +
      '<div class="sermon-modal-body" id="sermon-editor-body">' +
      '  <p class="sermon-field-help">Sincronizando a versão mais recente do arquivo...</p>' +
      '</div>';

    openOverlay(modal);
    modal.querySelector("#sermon-editor-close").addEventListener("click", closeOverlay);

    // Busca versão fresca no GitHub para evitar editar texto desatualizado
    try {
      const latest = await ghGetFile(sermonData.source_path);
      if (latest.exists && latest.content) {
        currentSha = latest.sha;
        const parsed = parseFrontMatterText(latest.content);
        initialBody = parsed.body;
        initialMeta = {
          ...initialMeta,
          titulo: parsed.meta.titulo || initialMeta.titulo || "",
          passagem: parsed.meta.passagem !== undefined ? parsed.meta.passagem : initialMeta.passagem || "",
          tema: parsed.meta.tema !== undefined ? parsed.meta.tema : initialMeta.tema || "",
          data: parsed.meta.data !== undefined ? parsed.meta.data : initialMeta.data || "",
          igreja: parsed.meta.igreja || parsed.meta.local || initialMeta.igreja || "",
          traducao: parsed.meta.traducao !== undefined ? parsed.meta.traducao : initialMeta.traducao || "",
          resumo: parsed.meta.resumo !== undefined ? parsed.meta.resumo : initialMeta.resumo || "",
          nota_revisao: parsed.meta.nota_revisao !== undefined ? parsed.meta.nota_revisao : initialMeta.nota_revisao || "",
          estudo_origem: parsed.meta.estudo_origem !== undefined ? parsed.meta.estudo_origem : initialMeta.estudo_origem || "",
        };
      }
    } catch {
      // Mantém fallback embutido na página
    }

    if (isNew) {
      targetRevNumber = await resolveNextRevisionNumber();
      targetRevLabel = "R" + targetRevNumber;
      targetId = sermonData.sermao_id + "-r" + targetRevNumber;
      targetPath = sermonData.source_dir + "/r" + targetRevNumber + ".md";
      currentSha = null;
      // Em nova revisão, data/igreja/nota começam limpas (opcionais) para a nova ministração
      initialMeta = {
        ...initialMeta,
        data: "",
        igreja: "",
        nota_revisao: "",
      };
    }

    if (!document.body.contains(modal)) return;

    const kickerEl = modal.querySelector("#sermon-editor-kicker");
    const titleEl = modal.querySelector("#sermon-editor-title");
    kickerEl.textContent = isNew
      ? "Nova revisão a partir de " + sermonData.revisao + " · " + targetPath
      : "Editando " + targetRevLabel + " · " + targetPath;
    titleEl.textContent = isNew
      ? "Criar revisão " + targetRevLabel
      : "Editar revisão " + targetRevLabel;

    const hasSidebar = referenceNotes.length > 0;
    const editorBody = modal.querySelector("#sermon-editor-body");
    editorBody.innerHTML =
      '<div id="sermon-save-result"></div>' +
      '<div class="sermon-editor-layout' + (hasSidebar ? "" : " sermon-editor-layout--single") + '">' +
      '  <div class="sermon-editor-main">' +
      '    <div class="sermon-meta-grid">' +
      '      <div class="sermon-field sermon-field--wide">' +
      '        <label for="ed-titulo">Título *</label>' +
      '        <input type="text" class="sermon-field-input" id="ed-titulo" required>' +
      '      </div>' +
      '      <div class="sermon-field">' +
      '        <label for="ed-passagem">Passagem (opcional)</label>' +
      '        <input type="text" class="sermon-field-input" id="ed-passagem" placeholder="Ex.: Salmo 23.1–6">' +
      '      </div>' +
      '      <div class="sermon-field">' +
      '        <label for="ed-tema">Tema (opcional)</label>' +
      '        <input type="text" class="sermon-field-input" id="ed-tema" placeholder="Ex.: Fidelidade de Deus">' +
      '      </div>' +
      '      <div class="sermon-field">' +
      '        <label for="ed-data">Data (opcional)</label>' +
      '        <input type="date" class="sermon-field-input" id="ed-data">' +
      '      </div>' +
      '      <div class="sermon-field">' +
      '        <label for="ed-igreja">Local / Igreja (opcional)</label>' +
      '        <input type="text" class="sermon-field-input" id="ed-igreja" placeholder="Ex.: IPR Paranaíba-MS">' +
      '      </div>' +
      '      <div class="sermon-field">' +
      '        <label for="ed-traducao">Tradução (opcional)</label>' +
      '        <input type="text" class="sermon-field-input" id="ed-traducao" placeholder="Ex.: ACF, NVI, ARA">' +
      '      </div>' +
      '      <div class="sermon-field sermon-field--wide">' +
      '        <label for="ed-resumo">Resumo breve (opcional)</label>' +
      '        <input type="text" class="sermon-field-input" id="ed-resumo" placeholder="Uma frase curta para o catálogo">' +
      '      </div>' +
      '      <div class="sermon-field sermon-field--full">' +
      '        <label for="ed-nota-revisao">Nota desta revisão (opcional)</label>' +
      '        <input type="text" class="sermon-field-input" id="ed-nota-revisao" placeholder="Ex.: Reorganizado ponto 2 e ajustada conclusão">' +
      '      </div>' +
      '    </div>' +
      '    <div class="sermon-editor-tabs">' +
      '      <label for="ed-body" style="font-size:.78rem;font-weight:700;color:var(--forest-2);">Texto da pregação (Markdown)</label>' +
      '      <div class="sermon-tab-group" role="tablist">' +
      '        <button type="button" class="sermon-tab-btn is-active" id="ed-tab-write" role="tab" aria-selected="true">Escrever</button>' +
      '        <button type="button" class="sermon-tab-btn" id="ed-tab-preview" role="tab" aria-selected="false">Pré-visualizar</button>' +
      '      </div>' +
      '    </div>' +
      '    <textarea class="sermon-markdown-input" id="ed-body" spellcheck="true"></textarea>' +
      '    <div class="sermon-preview-pane prose" id="ed-preview" hidden></div>' +
      '    <p class="sermon-feedback-msg" id="ed-feedback" hidden></p>' +
      '  </div>' +
      (hasSidebar
        ? '  <aside class="sermon-editor-sidebar" aria-label="Notas de referência">' +
          '    <h3>Notas da ' + escapeHtml(sermonData.revisao) + ' (' + referenceNotes.length + ')</h3>' +
          '    <div id="ed-ref-notes-list"></div>' +
          '  </aside>'
        : "") +
      '</div>';

    const footer = document.createElement("div");
    footer.className = "sermon-modal-footer";
    footer.innerHTML =
      '<div class="sermon-note-form-right">' +
      '  <button type="button" class="sermon-btn sermon-btn--ghost" id="ed-download-btn">Baixar .md</button>' +
      '</div>' +
      '<div class="sermon-note-form-right">' +
      '  <button type="button" class="sermon-btn sermon-btn--ghost" id="ed-cancel-btn">Cancelar</button>' +
      '  <button type="button" class="sermon-btn sermon-btn--primary" id="ed-save-btn">' +
      (isNew ? "Salvar " + escapeHtml(targetRevLabel) + " no GitHub" : "Atualizar " + escapeHtml(targetRevLabel) + " no GitHub") +
      '  </button>' +
      '</div>';
    modal.appendChild(footer);

    // Preenche campos
    const fTitulo = modal.querySelector("#ed-titulo");
    const fPassagem = modal.querySelector("#ed-passagem");
    const fTema = modal.querySelector("#ed-tema");
    const fData = modal.querySelector("#ed-data");
    const fIgreja = modal.querySelector("#ed-igreja");
    const fTraducao = modal.querySelector("#ed-traducao");
    const fResumo = modal.querySelector("#ed-resumo");
    const fNotaRevisao = modal.querySelector("#ed-nota-revisao");
    const fBody = modal.querySelector("#ed-body");
    const previewPane = modal.querySelector("#ed-preview");
    const feedback = modal.querySelector("#ed-feedback");
    const saveResult = modal.querySelector("#sermon-save-result");
    const tabWrite = modal.querySelector("#ed-tab-write");
    const tabPreview = modal.querySelector("#ed-tab-preview");
    const saveBtn = modal.querySelector("#ed-save-btn");
    const downloadBtn = modal.querySelector("#ed-download-btn");

    fTitulo.value = initialMeta.titulo || "";
    fPassagem.value = initialMeta.passagem || "";
    fTema.value = initialMeta.tema || "";
    fData.value = initialMeta.data || "";
    fIgreja.value = initialMeta.igreja || "";
    fTraducao.value = initialMeta.traducao || "";
    fResumo.value = initialMeta.resumo || "";
    fNotaRevisao.value = initialMeta.nota_revisao || "";
    fBody.value = initialBody;

    if (hasSidebar) {
      const refList = modal.querySelector("#ed-ref-notes-list");
      referenceNotes.forEach((entry) => {
        const box = document.createElement("div");
        box.className = "sermon-ref-note";
        const heading = document.createElement("strong");
        heading.textContent = entry.title;
        const p = document.createElement("p");
        p.textContent = entry.text;
        box.appendChild(heading);
        box.appendChild(p);
        refList.appendChild(box);
      });
    }

    function collectMarkdown() {
      const meta = {
        id: targetId,
        sermao_id: sermonData.sermao_id,
        revisao: targetRevLabel,
        titulo: fTitulo.value.trim(),
        passagem: fPassagem.value.trim(),
        tema: fTema.value.trim(),
        data: fData.value.trim(),
        igreja: fIgreja.value.trim(),
        traducao: fTraducao.value.trim(),
        resumo: fResumo.value.trim(),
        nota_revisao: fNotaRevisao.value.trim(),
        estudo_origem: initialMeta.estudo_origem || "",
      };
      return { meta, markdown: buildSermonMarkdown(meta, fBody.value) };
    }

    tabWrite.addEventListener("click", () => {
      tabWrite.classList.add("is-active");
      tabWrite.setAttribute("aria-selected", "true");
      tabPreview.classList.remove("is-active");
      tabPreview.setAttribute("aria-selected", "false");
      fBody.hidden = false;
      previewPane.hidden = true;
    });

    tabPreview.addEventListener("click", () => {
      tabPreview.classList.add("is-active");
      tabPreview.setAttribute("aria-selected", "true");
      tabWrite.classList.remove("is-active");
      tabWrite.setAttribute("aria-selected", "false");
      previewPane.innerHTML = renderSimpleMarkdownPreview(fBody.value);
      fBody.hidden = true;
      previewPane.hidden = false;
    });

    modal.querySelector("#ed-cancel-btn").addEventListener("click", closeOverlay);

    downloadBtn.addEventListener("click", () => {
      const { markdown } = collectMarkdown();
      const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = isNew ? "r" + targetRevNumber + ".md" : targetId + ".md";
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    });

    saveBtn.addEventListener("click", async () => {
      const { meta, markdown } = collectMarkdown();
      if (!meta.titulo) {
        feedback.hidden = false;
        feedback.className = "sermon-feedback-msg sermon-feedback-msg--err";
        feedback.textContent = "O título da pregação é obrigatório.";
        fTitulo.focus();
        return;
      }
      if (!fBody.value.trim()) {
        feedback.hidden = false;
        feedback.className = "sermon-feedback-msg sermon-feedback-msg--err";
        feedback.textContent = "O texto da pregação não pode ficar vazio.";
        fBody.focus();
        return;
      }

      saveBtn.disabled = true;
      feedback.hidden = false;
      feedback.className = "sermon-feedback-msg";
      feedback.textContent = "Enviando " + targetRevLabel + " para o GitHub...";

      try {
        const commitMsg = isNew
          ? "feat(pregacoes): criar revisão " + targetRevLabel + " de " + meta.titulo
          : "fix(pregacoes): atualizar revisão " + targetRevLabel + " de " + meta.titulo;

        const result = await ghPutFile(targetPath, markdown, commitMsg, currentSha);
        currentSha = result && result.content ? result.content.sha : currentSha;

        if (isNew) {
          sermonData.next_revisao_numero = Math.max(
            Number(sermonData.next_revisao_numero || 2),
            targetRevNumber + 1
          );
          updateNewRevisionButtonLabel();
        } else {
          sermonData.metadata = { ...sermonData.metadata, ...meta };
          sermonData.body = fBody.value.trim();
        }

        const commitUrl =
          result && result.commit && result.commit.html_url
            ? result.commit.html_url
            : "https://github.com/" + state.repo + "/commits/" + state.branch;
        const actionsUrl = "https://github.com/" + state.repo + "/actions";

        saveResult.innerHTML =
          '<div class="sermon-save-banner">' +
          '  <strong>' + escapeHtml(targetRevLabel) + ' salva com sucesso no GitHub!</strong> ' +
          '  Arquivo gravado em <code>' + escapeHtml(targetPath) + '</code>.<br>' +
          '  O GitHub Actions já foi acionado para gerar o novo HTML e o PDF (leva cerca de 1 a 2 minutos). ' +
          '  <a href="' + escapeHtml(commitUrl) + '" target="_blank" rel="noopener noreferrer">Ver commit</a> · ' +
          '  <a href="' + escapeHtml(actionsUrl) + '" target="_blank" rel="noopener noreferrer">Acompanhar publicação</a>' +
          '</div>';

        feedback.hidden = true;
        saveBtn.disabled = false;
        setSyncStatus(targetRevLabel + " enviada ao GitHub · publicação em andamento");
        editorBody.scrollTop = 0;
      } catch (err) {
        feedback.hidden = false;
        feedback.className = "sermon-feedback-msg sermon-feedback-msg--err";
        feedback.textContent = "Erro ao salvar no GitHub: " + (err && err.message ? err.message : "falha inesperada");
        saveBtn.disabled = false;
      }
    });
  }

  /* ------------------------------------------------------------------
   * Ativação e Inicialização
   * ------------------------------------------------------------------ */

  function updateNewRevisionButtonLabel() {
    if (!newRevisionBtn) return;
    const nextNum = Number(sermonData.next_revisao_numero || 2);
    newRevisionBtn.textContent = "Nova revisão (R" + nextNum + ")";
  }

  async function applyAuthorMode(enabled) {
    if (authBtn) {
      authBtn.classList.toggle("sermon-auth-btn--active", enabled);
      authBtn.setAttribute("aria-pressed", enabled ? "true" : "false");
      authBtn.setAttribute(
        "title",
        enabled ? "Modo autor ativo (gerenciar conexão GitHub)" : "Modo autor (anotações e revisões)"
      );
    }
    if (authorBar) {
      authorBar.hidden = !enabled;
    }

    if (!enabled) {
      unmountNoteAnchors();
      return;
    }

    updateNewRevisionButtonLabel();
    collectSections();
    mountNoteAnchors();
    await loadNotesFromGitHub();
  }

  if (authBtn) {
    authBtn.addEventListener("click", openAuthModal);
  }
  if (generalNoteBtn) {
    generalNoteBtn.addEventListener("click", () => {
      state.editingSections.add(GENERAL_SECTION_ID);
      renderGeneralNoteSlot();
      if (generalNoteSlot) {
        generalNoteSlot.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    });
  }
  if (allNotesBtn) {
    allNotesBtn.addEventListener("click", openAllNotesDrawer);
  }
  if (editCurrentBtn) {
    editCurrentBtn.addEventListener("click", () => openRevisionEditor("edit"));
  }
  if (newRevisionBtn) {
    newRevisionBtn.addEventListener("click", () => openRevisionEditor("new"));
  }

  // Inicialização silenciosa: se não há token salvo, nada de autor é exibido
  state.token = readStorage(STORAGE_TOKEN);
  const savedRepo = readStorage(STORAGE_REPO);
  const savedBranch = readStorage(STORAGE_BRANCH);
  if (savedRepo) state.repo = savedRepo;
  if (savedBranch) state.branch = savedBranch;

  if (state.token) {
    applyAuthorMode(true);
  }
})();
