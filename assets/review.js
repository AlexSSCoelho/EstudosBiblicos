(function () {
  "use strict";

  const dataEl = document.getElementById("study-review-data");
  const railEl = document.getElementById("study-rail");
  const drawerEl = document.getElementById("review-drawer");
  const backdropEl = document.getElementById("review-backdrop");

  if (!dataEl || !railEl || !drawerEl || !backdropEl) return;

  let reviewData = null;
  try {
    reviewData = JSON.parse(dataEl.textContent || "{}");
  } catch {
    return;
  }

  const STUDY_ID = reviewData.study_id || "estudo";
  const STORAGE_PREFIX = "estudos_revisao_v1:" + STUDY_ID + ":";
  const DIFFICULTY_WEIGHTS = { facil: 1, intermediario: 2, dificil: 3 };
  const STATUS_CREDIT = { correto: 1, parcial: 0.5, errado: 0 };
  const OPTION_LETTERS = ["A", "B", "C", "D"];

  const titleEl = document.getElementById("review-drawer-title");
  const resetBtn = document.getElementById("review-reset-btn");
  const closeBtn = document.getElementById("review-close-btn");
  const progressWrap = document.getElementById("review-progress-wrap");
  const progressLabel = document.getElementById("review-progress-label");
  const answeredLabel = document.getElementById("review-answered-label");
  const progressFill = document.getElementById("review-progress-fill");
  const bodyEl = document.getElementById("review-drawer-body");
  const prevBtn = document.getElementById("review-prev-btn");
  const nextBtn = document.getElementById("review-next-btn");

  const sectionsById = new Map();
  (reviewData.revisao_secoes || []).forEach((sec) => {
    sectionsById.set(sec.section_id, sec);
  });

  const activeReadingByTarget = new Map();
  (reviewData.leitura_ativa || []).forEach((item) => {
    activeReadingByTarget.set(item.target_id, item);
  });

  let activeSectionId = null;
  let lastTriggerEl = null;

  /* ------------------------------------------------------------------------
   * Utilitários de texto, embaralhamento e avaliação offline
   * --------------------------------------------------------------------- */

  function shuffleArray(list) {
    const arr = list.slice();
    for (let i = arr.length - 1; i > 0; i -= 1) {
      const j = Math.floor(Math.random() * (i + 1));
      const tmp = arr[i];
      arr[i] = arr[j];
      arr[j] = tmp;
    }
    return arr;
  }

  function normalizeText(text) {
    return String(text || "")
      .normalize("NFKD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .replace(/[^a-z0-9\s]/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function stemPt(token) {
    let t = String(token || "");
    if (t.length <= 4) return t;
    if (t.endsWith("coes")) return t.slice(0, -4) + "cao";
    if (t.endsWith("oes")) return t.slice(0, -3) + "ao";
    if (t.endsWith("aes")) return t.slice(0, -3) + "ao";
    if (t.endsWith("mente") && t.length > 7) return t.slice(0, -5);
    if (t.endsWith("idades") && t.length > 8) return t.slice(0, -6);
    if (t.endsWith("idade") && t.length > 7) return t.slice(0, -5);
    if ((t.endsWith("ando") || t.endsWith("endo") || t.endsWith("indo")) && t.length > 6) {
      return t.slice(0, -4);
    }
    if ((t.endsWith("ados") || t.endsWith("adas") || t.endsWith("idos") || t.endsWith("idas")) && t.length > 6) {
      return t.slice(0, -4);
    }
    if ((t.endsWith("ar") || t.endsWith("er") || t.endsWith("ir")) && t.length > 5) {
      return t.slice(0, -2);
    }
    if (t.endsWith("es") && t.length > 5) return t.slice(0, -2);
    if (t.endsWith("s") && t.length > 4) return t.slice(0, -1);
    return t;
  }

  function levenshtein(a, b) {
    if (a === b) return 0;
    if (!a.length) return b.length;
    if (!b.length) return a.length;
    const prev = new Array(b.length + 1);
    const curr = new Array(b.length + 1);
    for (let j = 0; j <= b.length; j += 1) prev[j] = j;
    for (let i = 1; i <= a.length; i += 1) {
      curr[0] = i;
      for (let j = 1; j <= b.length; j += 1) {
        const cost = a[i - 1] === b[j - 1] ? 0 : 1;
        curr[j] = Math.min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost);
      }
      for (let j = 0; j <= b.length; j += 1) prev[j] = curr[j];
    }
    return prev[b.length];
  }

  function containsPhrase(haystack, needle) {
    if (!needle) return false;
    const paddedHaystack = " " + haystack + " ";
    const paddedNeedle = " " + needle + " ";
    return paddedHaystack.includes(paddedNeedle);
  }

  function evaluateFlashcard(item, rawInput) {
    const input = normalizeText(rawInput);
    if (!input) {
      return { status: "errado" };
    }

    const accepted = [item.resposta_principal, ...(item.aceitas || [])]
      .map(normalizeText)
      .filter(Boolean);

    for (let i = 0; i < accepted.length; i += 1) {
      const acc = accepted[i];
      if (input === acc) {
        return { status: "correto" };
      }
      if (acc.length >= 5) {
        const maxDist = acc.length >= 10 ? 2 : 1;
        if (levenshtein(input, acc) <= maxDist) {
          return { status: "correto" };
        }
      }
      if (containsPhrase(input, acc) && input.length <= acc.length + 28) {
        return { status: "correto" };
      }
    }

    const partials = (item.parciais || []).map(normalizeText).filter(Boolean);
    for (let i = 0; i < partials.length; i += 1) {
      const partial = partials[i];
      if (containsPhrase(input, partial)) {
        return { status: "parcial" };
      }
      if (partial.length >= 6 && levenshtein(input, partial) <= 1) {
        return { status: "parcial" };
      }
    }

    const inputTokens = new Set(input.split(" ").filter((t) => t.length >= 4).map(stemPt));
    const principalTokens = normalizeText(item.resposta_principal)
      .split(" ")
      .filter((t) => t.length >= 4)
      .map(stemPt);
    if (principalTokens.length >= 2) {
      const hits = principalTokens.filter((t) => inputTokens.has(t)).length;
      if (hits / principalTokens.length >= 0.5) {
        return { status: "parcial" };
      }
    }

    return { status: "errado" };
  }

  function matchesTerm(input, inputTokens, inputStems, rawTerm) {
    const term = normalizeText(rawTerm);
    if (!term) return false;
    if (term.includes(" ")) {
      return containsPhrase(input, term);
    }
    if (inputTokens.includes(term)) return true;
    const stemmedTerm = stemPt(term);
    if (inputStems.has(stemmedTerm)) return true;
    if (term.length >= 6) {
      return inputTokens.some((tok) => tok.length >= 5 && levenshtein(tok, term) <= 1);
    }
    return false;
  }

  function evaluateOpenAnswer(item, rawInput) {
    const input = normalizeText(rawInput);
    const inputTokens = input.split(" ").filter(Boolean);
    const inputStems = new Set(inputTokens.map(stemPt));
    const rubrica = item.rubrica || { nucleos: [], sinais_erro: [] };

    const nucleoResults = (rubrica.nucleos || []).map((nucleo) => {
      const expressions = (nucleo.expressoes || []).map(normalizeText).filter(Boolean);
      let hit = expressions.some((expr) => containsPhrase(input, expr));
      if (!hit) {
        hit = (nucleo.termos || []).some((term) =>
          matchesTerm(input, inputTokens, inputStems, term)
        );
      }
      return { rotulo: nucleo.rotulo, hit };
    });

    const triggeredErrors = [];
    (rubrica.sinais_erro || []).forEach((group) => {
      const terms = Array.isArray(group) ? group : [group];
      const allPresent = terms.every((t) => matchesTerm(input, inputTokens, inputStems, t));
      if (allPresent) {
        triggeredErrors.push(terms.join(" + "));
      }
    });

    const hitCount = nucleoResults.filter((n) => n.hit).length;
    const totalCount = nucleoResults.length;
    let status = "errado";
    if (triggeredErrors.length > 0) {
      status = hitCount > 0 ? "parcial" : "errado";
    } else if (totalCount > 0 && hitCount === totalCount) {
      status = "correto";
    } else if (hitCount >= 1) {
      status = "parcial";
    }

    return { status, nucleoResults, triggeredErrors };
  }

  /* ------------------------------------------------------------------------
   * Estado e persistência por seção (localStorage)
   * --------------------------------------------------------------------- */

  function storageKey(sectionId) {
    return STORAGE_PREFIX + sectionId;
  }

  function createFreshState(section) {
    const order = shuffleArray(section.itens.map((item) => item.id));
    const optionOrders = {};
    section.itens.forEach((item) => {
      if (item.tipo === "quiz") {
        optionOrders[item.id] = shuffleArray([0, 1, 2, 3]);
      }
    });
    return {
      order,
      optionOrders,
      answers: {},
      currentIndex: 0,
      completed: false,
      lastScore: null,
    };
  }

  function loadSectionState(sectionId) {
    const section = sectionsById.get(sectionId);
    if (!section) return null;

    try {
      const raw = window.localStorage.getItem(storageKey(sectionId));
      if (raw) {
        const parsed = JSON.parse(raw);
        const validIds = new Set(section.itens.map((item) => item.id));
        if (
          Array.isArray(parsed.order) &&
          parsed.order.length === section.itens.length &&
          parsed.order.every((id) => validIds.has(id))
        ) {
          return parsed;
        }
      }
    } catch {
      // Ignora erro de acesso ou JSON corrompido
    }
    const fresh = createFreshState(section);
    saveSectionState(sectionId, fresh);
    return fresh;
  }

  function saveSectionState(sectionId, state) {
    try {
      window.localStorage.setItem(storageKey(sectionId), JSON.stringify(state));
    } catch {
      // Ambiente sem localStorage disponível
    }
  }

  function computeSectionScore(section, state) {
    let totalWeight = 0;
    let earnedWeight = 0;
    let correctCount = 0;
    let partialCount = 0;
    let wrongCount = 0;
    let highWeightTotal = 0;
    let highWeightCorrect = 0;

    section.itens.forEach((item) => {
      const weight = DIFFICULTY_WEIGHTS[item.dificuldade] || 1;
      totalWeight += weight;
      const ans = state.answers[item.id];
      const status = ans ? ans.status : "errado";
      earnedWeight += weight * (STATUS_CREDIT[status] || 0);
      if (status === "correto") correctCount += 1;
      else if (status === "parcial") partialCount += 1;
      else wrongCount += 1;

      if (item.dificuldade === "dificil") {
        highWeightTotal += 1;
        if (status === "correto") highWeightCorrect += 1;
      }
    });

    const score = totalWeight > 0 ? Math.round((earnedWeight / totalWeight) * 100) / 10 : 0;
    return {
      score,
      scoreFormatted: score.toFixed(1).replace(".", ","),
      correctCount,
      partialCount,
      wrongCount,
      highWeightTotal,
      highWeightCorrect,
    };
  }

  /* ------------------------------------------------------------------------
   * Construção e posicionamento da trilha marginal direita (desktop)
   * --------------------------------------------------------------------- */

  function renderRail() {
    railEl.innerHTML = "";
    const studyBody = document.querySelector(".study-body");
    if (!studyBody) return;

    const headings = Array.from(studyBody.querySelectorAll("h2[id], h3[id]"));
    headings.forEach((heading) => {
      const id = heading.id;
      const section = sectionsById.get(id);
      if (section) {
        const card = document.createElement("div");
        card.className = "rail-card";
        card.dataset.targetId = id;
        card.dataset.cardKind = "review";

        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "rail-review-btn";
        btn.dataset.sectionId = id;
        btn.setAttribute("aria-label", "Abrir revisão ativa da seção: " + section.section_title);
        btn.addEventListener("click", () => openDrawer(id, btn));

        card.appendChild(btn);
        railEl.appendChild(card);
        updateRailButton(btn, section, loadSectionState(id));
      }

      const activeReading = activeReadingByTarget.get(id);
      if (activeReading && activeReading.perguntas && activeReading.perguntas.length) {
        const card = document.createElement("div");
        card.className = "rail-card rail-reading-prompt";
        card.dataset.targetId = id;
        card.dataset.cardKind = "reading";

        const label = document.createElement("p");
        label.className = "rail-reading-label";
        label.textContent = "Para ler com atenção";
        card.appendChild(label);

        activeReading.perguntas.forEach((question) => {
          const p = document.createElement("p");
          p.className = "rail-reading-text";
          p.textContent = question;
          card.appendChild(p);
        });

        railEl.appendChild(card);
      }
    });
  }

  function updateRailButton(btn, section, state) {
    const total = section.itens.length;
    const answeredCount = Object.keys(state.answers || {}).length;
    btn.classList.toggle("rail-review-btn--done", Boolean(state.completed));

    let badgeText = total + " questões";
    let copyText = "Testar compreensão";
    if (state.completed && state.lastScore !== null && state.lastScore !== undefined) {
      badgeText = "Nota " + Number(state.lastScore).toFixed(1).replace(".", ",");
      copyText = "Revisar novamente";
    } else if (answeredCount > 0) {
      badgeText = answeredCount + "/" + total;
      copyText = "Continuar revisão";
    }

    btn.innerHTML =
      '<span class="rail-review-top">' +
      '  <span class="rail-review-kicker">Revisão ativa</span>' +
      '  <span class="rail-review-badge"></span>' +
      "</span>" +
      '<span class="rail-review-copy">' +
      '  <span class="rail-review-copy-text"></span>' +
      '  <span class="rail-review-arrow" aria-hidden="true">→</span>' +
      "</span>";
    btn.querySelector(".rail-review-badge").textContent = badgeText;
    btn.querySelector(".rail-review-copy-text").textContent = copyText;
  }

  function refreshRailButton(sectionId) {
    const section = sectionsById.get(sectionId);
    const btn = railEl.querySelector('.rail-review-btn[data-section-id="' + sectionId + '"]');
    if (section && btn) {
      updateRailButton(btn, section, loadSectionState(sectionId));
      schedulePositionRail();
    }
  }

  let positionScheduled = false;
  function positionRailItems() {
    positionScheduled = false;
    if (!window.matchMedia("(min-width: 1180px)").matches) {
      railEl.style.minHeight = "";
      return;
    }

    const railRect = railEl.getBoundingClientRect();
    const cards = Array.from(railEl.querySelectorAll(".rail-card"));
    let cursorBottom = 0;
    const minGap = 16;

    cards.forEach((card) => {
      const target = document.getElementById(card.dataset.targetId);
      if (!target) return;
      const desiredTop = target.getBoundingClientRect().top - railRect.top + 2;
      const top = Math.max(0, desiredTop, cursorBottom);
      card.style.top = Math.round(top) + "px";
      cursorBottom = top + card.offsetHeight + minGap;
    });

    railEl.style.minHeight = Math.ceil(cursorBottom) + "px";
  }

  function schedulePositionRail() {
    if (positionScheduled) return;
    positionScheduled = true;
    window.requestAnimationFrame(positionRailItems);
  }

  /* ------------------------------------------------------------------------
   * Slide-over de revisão ativa
   * --------------------------------------------------------------------- */

  function openDrawer(sectionId, triggerEl) {
    if (!sectionsById.has(sectionId)) return;
    activeSectionId = sectionId;
    lastTriggerEl = triggerEl || document.activeElement;

    backdropEl.hidden = false;
    drawerEl.hidden = false;
    renderDrawer();
    closeBtn.focus();
  }

  function closeDrawer() {
    backdropEl.hidden = true;
    drawerEl.hidden = true;
    activeSectionId = null;
    if (lastTriggerEl && typeof lastTriggerEl.focus === "function") {
      lastTriggerEl.focus();
    }
  }

  function getOrderedItems(section, state) {
    const map = new Map(section.itens.map((item) => [item.id, item]));
    return state.order.map((id) => map.get(id)).filter(Boolean);
  }

  function statusLabel(status) {
    if (status === "correto") return "Correto";
    if (status === "parcial") return "Parcial";
    return "Errado";
  }

  function typeLabel(tipo) {
    if (tipo === "quiz") return "Múltipla escolha";
    if (tipo === "flashcard") return "Flashcard";
    return "Pergunta aberta";
  }

  function renderQuizQuestion(item, state, existingAnswer) {
    const perm = state.optionOrders[item.id] || [0, 1, 2, 3];
    let selectedPermPos = null;
    if (existingAnswer && typeof existingAnswer.selectedOrigIdx === "number") {
      selectedPermPos = perm.indexOf(existingAnswer.selectedOrigIdx);
    }

    const typeEl = document.createElement("p");
    typeEl.className = "review-item-type";
    typeEl.textContent = typeLabel(item.tipo);
    bodyEl.appendChild(typeEl);

    const promptEl = document.createElement("h3");
    promptEl.className = "review-item-prompt";
    promptEl.textContent = item.enunciado;
    bodyEl.appendChild(promptEl);

    const optionsWrap = document.createElement("div");
    optionsWrap.className = "review-options";
    bodyEl.appendChild(optionsWrap);

    let pendingOrigIdx = existingAnswer ? existingAnswer.selectedOrigIdx : null;
    const submitRow = document.createElement("div");
    submitRow.className = "review-submit-row";
    const submitBtn = document.createElement("button");
    submitBtn.type = "button";
    submitBtn.className = "review-submit-btn";
    submitBtn.textContent = "Confirmar resposta";
    submitBtn.disabled = Boolean(existingAnswer) || pendingOrigIdx === null;

    const optionButtons = [];
    perm.forEach((origIdx, displayIdx) => {
      const opt = item.alternativas[origIdx];
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "review-option";

      const letter = document.createElement("span");
      letter.className = "review-option-letter";
      letter.textContent = OPTION_LETTERS[displayIdx] || String(displayIdx + 1);

      const textSpan = document.createElement("span");
      textSpan.textContent = opt.texto;

      btn.appendChild(letter);
      btn.appendChild(textSpan);

      if (existingAnswer) {
        btn.disabled = true;
        if (opt.correta) btn.classList.add("review-option--correct");
        else if (displayIdx === selectedPermPos) btn.classList.add("review-option--wrong");
      } else {
        btn.addEventListener("click", () => {
          pendingOrigIdx = origIdx;
          optionButtons.forEach((b) => b.classList.remove("review-option--selected"));
          btn.classList.add("review-option--selected");
          submitBtn.disabled = false;
        });
      }

      optionButtons.push(btn);
      optionsWrap.appendChild(btn);
    });

    if (!existingAnswer) {
      submitBtn.addEventListener("click", () => {
        if (pendingOrigIdx === null) return;
        const chosen = item.alternativas[pendingOrigIdx];
        state.answers[item.id] = {
          type: "quiz",
          selectedOrigIdx: pendingOrigIdx,
          status: chosen && chosen.correta ? "correto" : "errado",
        };
        saveSectionState(activeSectionId, state);
        refreshRailButton(activeSectionId);
        renderDrawer();
      });
      submitRow.appendChild(submitBtn);
      bodyEl.appendChild(submitRow);
    } else {
      const feedback = document.createElement("div");
      feedback.className = "review-feedback review-feedback--" + existingAnswer.status;
      const st = document.createElement("p");
      st.className = "review-feedback-status";
      st.textContent = existingAnswer.status === "correto" ? "Correto" : "Incorreto";
      const just = document.createElement("p");
      just.textContent = item.justificativa;
      feedback.appendChild(st);
      feedback.appendChild(just);
      bodyEl.appendChild(feedback);
    }
  }

  function renderFlashcardQuestion(item, state, existingAnswer) {
    const typeEl = document.createElement("p");
    typeEl.className = "review-item-type";
    typeEl.textContent = typeLabel(item.tipo);
    bodyEl.appendChild(typeEl);

    const promptEl = document.createElement("h3");
    promptEl.className = "review-item-prompt";
    promptEl.textContent = item.frente;
    bodyEl.appendChild(promptEl);

    const input = document.createElement("input");
    input.type = "text";
    input.className = "review-input";
    input.placeholder = "Digite a resposta (aceita variação sem acentos)...";
    input.value = existingAnswer ? existingAnswer.input : "";
    input.disabled = Boolean(existingAnswer);
    bodyEl.appendChild(input);

    const hint = document.createElement("p");
    hint.className = "review-field-hint";
    hint.textContent = "Para termos gregos ou hebraicos, use a transliteração simples ou o conceito em português.";
    bodyEl.appendChild(hint);

    if (!existingAnswer) {
      const submitRow = document.createElement("div");
      submitRow.className = "review-submit-row";
      const submitBtn = document.createElement("button");
      submitBtn.type = "button";
      submitBtn.className = "review-submit-btn";
      submitBtn.textContent = "Verificar flashcard";
      submitBtn.disabled = !input.value.trim();

      const submitHandler = () => {
        const val = input.value.trim();
        if (!val) return;
        const result = evaluateFlashcard(item, val);
        state.answers[item.id] = {
          type: "flashcard",
          input: val,
          status: result.status,
        };
        saveSectionState(activeSectionId, state);
        refreshRailButton(activeSectionId);
        renderDrawer();
      };

      input.addEventListener("input", () => {
        submitBtn.disabled = !input.value.trim();
      });
      input.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && input.value.trim()) {
          e.preventDefault();
          submitHandler();
        }
      });
      submitBtn.addEventListener("click", submitHandler);

      submitRow.appendChild(submitBtn);
      bodyEl.appendChild(submitRow);
      window.setTimeout(() => input.focus(), 30);
    } else {
      const feedback = document.createElement("div");
      feedback.className = "review-feedback review-feedback--" + existingAnswer.status;

      const st = document.createElement("p");
      st.className = "review-feedback-status";
      st.textContent = statusLabel(existingAnswer.status);
      feedback.appendChild(st);

      const expected = document.createElement("p");
      const strong = document.createElement("strong");
      strong.textContent = "Resposta esperada: ";
      expected.appendChild(strong);
      expected.appendChild(document.createTextNode(item.resposta_principal));
      feedback.appendChild(expected);

      const note = document.createElement("p");
      note.textContent = item.nota_explicativa;
      feedback.appendChild(note);

      bodyEl.appendChild(feedback);
    }
  }

  function renderOpenQuestion(item, state, existingAnswer) {
    const typeEl = document.createElement("p");
    typeEl.className = "review-item-type";
    typeEl.textContent = typeLabel(item.tipo);
    bodyEl.appendChild(typeEl);

    const promptEl = document.createElement("h3");
    promptEl.className = "review-item-prompt";
    promptEl.textContent = item.enunciado;
    bodyEl.appendChild(promptEl);

    const textarea = document.createElement("textarea");
    textarea.className = "review-textarea";
    textarea.rows = 4;
    textarea.placeholder = "Explique com suas palavras com base na lógica do texto...";
    textarea.value = existingAnswer ? existingAnswer.input : "";
    textarea.disabled = Boolean(existingAnswer);
    bodyEl.appendChild(textarea);

    const hint = document.createElement("p");
    hint.className = "review-field-hint";
    hint.textContent = "Responda de forma objetiva em 1 a 3 frases.";
    bodyEl.appendChild(hint);

    if (!existingAnswer) {
      const submitRow = document.createElement("div");
      submitRow.className = "review-submit-row";
      const submitBtn = document.createElement("button");
      submitBtn.type = "button";
      submitBtn.className = "review-submit-btn";
      submitBtn.textContent = "Avaliar resposta";
      submitBtn.disabled = !textarea.value.trim();

      textarea.addEventListener("input", () => {
        submitBtn.disabled = !textarea.value.trim();
      });

      submitBtn.addEventListener("click", () => {
        const val = textarea.value.trim();
        if (!val) return;
        const result = evaluateOpenAnswer(item, val);
        state.answers[item.id] = {
          type: "aberta",
          input: val,
          autoStatus: result.status,
          status: result.status,
          selfConfirmed: false,
          nucleoResults: result.nucleoResults,
          triggeredErrors: result.triggeredErrors,
        };
        saveSectionState(activeSectionId, state);
        refreshRailButton(activeSectionId);
        renderDrawer();
      });

      submitRow.appendChild(submitBtn);
      bodyEl.appendChild(submitRow);
      window.setTimeout(() => textarea.focus(), 30);
    } else {
      const feedback = document.createElement("div");
      feedback.className = "review-feedback review-feedback--" + existingAnswer.status;

      const st = document.createElement("p");
      st.className = "review-feedback-status";
      st.textContent =
        statusLabel(existingAnswer.status) +
        (existingAnswer.selfConfirmed ? " (confirmada manualmente)" : "");
      feedback.appendChild(st);

      if (existingAnswer.nucleoResults && existingAnswer.nucleoResults.length) {
        const list = document.createElement("ul");
        list.className = "review-nucleos-list";
        existingAnswer.nucleoResults.forEach((nuc) => {
          const li = document.createElement("li");
          li.className = "review-nucleo-item " + (nuc.hit ? "review-nucleo-item--hit" : "review-nucleo-item--miss");
          li.textContent = (nuc.hit ? "✓ " : "○ ") + nuc.rotulo;
          list.appendChild(li);
        });
        feedback.appendChild(list);
      }

      if (existingAnswer.triggeredErrors && existingAnswer.triggeredErrors.length) {
        const warn = document.createElement("div");
        warn.className = "review-error-hint";
        warn.textContent =
          "Atenção conceitual: sua resposta mencionou expressão associada a um equívoco evitado pelo estudo.";
        feedback.appendChild(warn);
      }

      const modelBox = document.createElement("div");
      modelBox.className = "review-model-box";
      const modelP = document.createElement("p");
      const strong = document.createElement("strong");
      strong.textContent = "Síntese de referência do estudo: ";
      modelP.appendChild(strong);
      modelP.appendChild(document.createTextNode(item.resposta_modelo));
      modelBox.appendChild(modelP);

      if (item.trecho_ancora) {
        const anchorP = document.createElement("p");
        anchorP.style.fontSize = "0.78rem";
        anchorP.style.color = "var(--muted)";
        anchorP.textContent = "Referência: " + item.trecho_ancora;
        modelBox.appendChild(anchorP);
      }
      feedback.appendChild(modelBox);

      if (existingAnswer.autoStatus !== "correto") {
        const confirmBtn = document.createElement("button");
        confirmBtn.type = "button";
        confirmBtn.className = "review-self-confirm-btn";
        confirmBtn.textContent = existingAnswer.selfConfirmed
          ? "Desfazer confirmação manual"
          : "Minha resposta expressava essa ideia";
        confirmBtn.addEventListener("click", () => {
          existingAnswer.selfConfirmed = !existingAnswer.selfConfirmed;
          existingAnswer.status = existingAnswer.selfConfirmed
            ? "correto"
            : existingAnswer.autoStatus;
          if (state.completed) {
            const section = sectionsById.get(activeSectionId);
            state.lastScore = computeSectionScore(section, state).score;
          }
          saveSectionState(activeSectionId, state);
          refreshRailButton(activeSectionId);
          renderDrawer();
        });
        feedback.appendChild(confirmBtn);
      }

      bodyEl.appendChild(feedback);
    }
  }

  function renderSummary(section, state, orderedItems) {
    const summary = computeSectionScore(section, state);
    state.completed = true;
    state.lastScore = summary.score;
    saveSectionState(activeSectionId, state);
    refreshRailButton(activeSectionId);

    const scoreCard = document.createElement("div");
    scoreCard.className = "review-summary-score-card";

    const scoreEl = document.createElement("p");
    scoreEl.className = "review-summary-score";
    scoreEl.textContent = summary.scoreFormatted + " / 10";
    scoreCard.appendChild(scoreEl);

    const subEl = document.createElement("p");
    subEl.className = "review-summary-sub";
    let diag =
      summary.correctCount +
      " correta(s) · " +
      summary.partialCount +
      " parcial(is) · " +
      summary.wrongCount +
      " incorreta(s).";
    if (summary.highWeightTotal > 0) {
      diag +=
        " Nas questões de síntese mais exigentes, você acertou " +
        summary.highWeightCorrect +
        " de " +
        summary.highWeightTotal +
        ".";
    }
    subEl.textContent = diag;
    scoreCard.appendChild(subEl);
    bodyEl.appendChild(scoreCard);

    const list = document.createElement("div");
    list.className = "review-summary-list";
    orderedItems.forEach((item, idx) => {
      const ans = state.answers[item.id] || { status: "errado" };
      const card = document.createElement("div");
      card.className = "review-summary-item";

      const top = document.createElement("div");
      top.className = "review-summary-item-top";
      const left = document.createElement("span");
      left.textContent = (idx + 1) + ". " + typeLabel(item.tipo);
      const right = document.createElement("span");
      right.textContent = statusLabel(ans.status);
      if (ans.status === "correto") right.style.color = "var(--forest-2)";
      else if (ans.status === "parcial") right.style.color = "#5c3f10";
      else right.style.color = "#7d2c14";
      top.appendChild(left);
      top.appendChild(right);
      card.appendChild(top);

      const qText = document.createElement("p");
      qText.textContent = item.tipo === "flashcard" ? item.frente : item.enunciado;
      card.appendChild(qText);

      const keyNote = document.createElement("small");
      if (item.tipo === "quiz") keyNote.textContent = item.justificativa;
      else if (item.tipo === "flashcard") {
        keyNote.textContent = item.resposta_principal + " — " + item.nota_explicativa;
      } else {
        keyNote.textContent = item.resposta_modelo;
      }
      card.appendChild(keyNote);

      list.appendChild(card);
    });
    bodyEl.appendChild(list);
  }

  function renderDrawer() {
    if (!activeSectionId) return;
    const section = sectionsById.get(activeSectionId);
    const state = loadSectionState(activeSectionId);
    if (!section || !state) return;

    titleEl.textContent = section.section_title;
    const orderedItems = getOrderedItems(section, state);
    const total = orderedItems.length;
    const answeredCount = Object.keys(state.answers || {}).length;
    const isSummary = state.currentIndex >= total;

    progressWrap.hidden = false;
    if (isSummary) {
      progressLabel.textContent = "Resumo final da seção";
      progressFill.style.width = "100%";
    } else {
      progressLabel.textContent = "Questão " + (state.currentIndex + 1) + " de " + total;
      progressFill.style.width = Math.round(((state.currentIndex + 1) / total) * 100) + "%";
    }
    answeredLabel.textContent = answeredCount + " de " + total + " respondidas";

    bodyEl.innerHTML = "";
    if (isSummary) {
      renderSummary(section, state, orderedItems);
      prevBtn.disabled = false;
      nextBtn.disabled = false;
      nextBtn.textContent = "Concluir";
    } else {
      const item = orderedItems[state.currentIndex];
      const existingAnswer = state.answers[item.id] || null;

      if (item.tipo === "quiz") renderQuizQuestion(item, state, existingAnswer);
      else if (item.tipo === "flashcard") renderFlashcardQuestion(item, state, existingAnswer);
      else renderOpenQuestion(item, state, existingAnswer);

      prevBtn.disabled = state.currentIndex === 0;
      const isLast = state.currentIndex === total - 1;
      const allAnswered = answeredCount === total;
      nextBtn.textContent = isLast ? "Ver resultado" : "Próxima";
      nextBtn.disabled = isLast ? !allAnswered : !existingAnswer;
    }
  }

  /* ------------------------------------------------------------------------
   * Eventos globais
   * --------------------------------------------------------------------- */

  closeBtn.addEventListener("click", closeDrawer);
  backdropEl.addEventListener("click", closeDrawer);

  resetBtn.addEventListener("click", () => {
    if (!activeSectionId) return;
    const section = sectionsById.get(activeSectionId);
    if (!section) return;
    const fresh = createFreshState(section);
    saveSectionState(activeSectionId, fresh);
    refreshRailButton(activeSectionId);
    renderDrawer();
  });

  prevBtn.addEventListener("click", () => {
    if (!activeSectionId) return;
    const state = loadSectionState(activeSectionId);
    if (!state || state.currentIndex <= 0) return;
    state.currentIndex -= 1;
    saveSectionState(activeSectionId, state);
    renderDrawer();
  });

  nextBtn.addEventListener("click", () => {
    if (!activeSectionId) return;
    const section = sectionsById.get(activeSectionId);
    const state = loadSectionState(activeSectionId);
    if (!section || !state) return;
    if (state.currentIndex >= section.itens.length) {
      closeDrawer();
      return;
    }
    state.currentIndex += 1;
    saveSectionState(activeSectionId, state);
    renderDrawer();
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !drawerEl.hidden) {
      closeDrawer();
    }
  });

  renderRail();
  positionRailItems();

  window.addEventListener("resize", schedulePositionRail);
  window.addEventListener("load", schedulePositionRail);
  window.addEventListener("study:layout-change", schedulePositionRail);
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(schedulePositionRail);
  }

  const studyBody = document.querySelector(".study-body");
  if (studyBody) {
    studyBody.addEventListener("toggle", schedulePositionRail, true);
    if (typeof ResizeObserver === "function") {
      const observer = new ResizeObserver(schedulePositionRail);
      observer.observe(studyBody);
    }
  }
})();
