/* Поведение привязано к data-атрибутам, поэтому макросы можно дополнять. */
(function () {
  "use strict";

  function updateCheckboxCount(menu) {
    const count = menu.querySelector("[data-checkbox-count]");
    if (count) count.textContent = menu.querySelectorAll('input[type="checkbox"]:checked').length;
  }

  // Фокус возвращаем только с клавиатуры: клик снаружи уже выбрал новую цель.
  function closeCheckboxMenu(menu, restoreFocus) {
    menu.open = false;
    if (restoreFocus) menu.querySelector("summary").focus({ preventScroll: true });
  }

  document.addEventListener("change", event => {
    const menu = event.target.closest("details.checkbox-menu");
    if (menu) updateCheckboxCount(menu);
  });
  document.addEventListener("click", event => {
    document.querySelectorAll("details.checkbox-menu[open]").forEach(menu => {
      if (!menu.contains(event.target)) closeCheckboxMenu(menu);
    });
  });
  document.addEventListener("keydown", event => {
    if (event.key !== "Escape") return;
    document.querySelectorAll("details.checkbox-menu[open]").forEach(menu => {
      event.preventDefault();
      closeCheckboxMenu(menu, true);
    });
  });
  document.querySelectorAll("details.checkbox-menu").forEach(updateCheckboxCount);

  const busyForms = new Map();
  const confirmedForms = new WeakSet();
  const confirmedButtons = new WeakSet();
  const feedbackStates = new WeakMap();
  const dialog = document.querySelector("[data-confirm-dialog]");
  let pendingConfirmation = null;

  function attribute(form, button, name) {
    return button?.hasAttribute(name) ? button.getAttribute(name) : (form?.getAttribute(name) ?? null);
  }

  function askConfirmation(source, form, button, resume) {
    const question = attribute(form, source, "data-confirm");
    if (!dialog) {
      // На странице без общего диалога подтверждение всё равно обязательно.
      if (window.confirm(question)) resume();
      return;
    }
    if (dialog.open) return;
    const accept = dialog.querySelector("[data-confirm-accept]");
    dialog.querySelector("[data-confirm-text]").textContent = question;
    accept.querySelector("[data-button-label]").textContent = attribute(form, source, "data-confirm-ok") || "Продолжить";
    const danger = attribute(form, source, "data-confirm-danger") !== null;
    accept.classList.toggle("btn--danger", danger);
    accept.classList.toggle("btn--primary", !danger);
    pendingConfirmation = { resume, opener: button || document.activeElement };
    dialog.showModal();
  }

  if (dialog) {
    dialog.querySelector("[data-confirm-cancel]").addEventListener("click", () => dialog.close());
    dialog.querySelector("[data-confirm-accept]").addEventListener("click", () => {
      const pending = pendingConfirmation;
      pendingConfirmation = null;
      dialog.close();
      pending?.opener?.focus({ preventScroll: true });
      pending?.resume();
    });
    dialog.addEventListener("close", () => {
      pendingConfirmation?.opener?.focus({ preventScroll: true });
      pendingConfirmation = null;
    });
  }

  function setBusy(form, submitter, label) {
    if (busyForms.has(form)) return;
    const buttons = Array.from(form.elements).filter(el =>
      (el instanceof HTMLButtonElement || el instanceof HTMLInputElement) && ["submit", "image"].includes(el.type));
    const active = submitter || buttons.find(button => !button.disabled);
    const state = {
      aria: form.getAttribute("aria-busy"),
      tabindex: form.getAttribute("tabindex"),
      buttons: buttons.map(button => ({ button, disabled: button.disabled, aria: button.getAttribute("aria-busy"), html: button.innerHTML, value: button.value })),
      timer: null
    };
    busyForms.set(form, state);
    form.setAttribute("aria-busy", "true");
    // Следующий такт сохраняет name/value и formaction исходного submitter.
    state.timer = window.setTimeout(() => {
      if (form.contains(document.activeElement)) {
        form.tabIndex = -1;
        form.focus({ preventScroll: true });
      }
      buttons.forEach(button => { button.disabled = true; });
      if (active) {
        active.setAttribute("aria-busy", "true");
        if (active instanceof HTMLInputElement) active.value = label;
        else active.textContent = label;
      }
    }, 0);
  }

  function restoreAttribute(element, name, value) {
    if (value === null) element.removeAttribute(name);
    else element.setAttribute(name, value);
  }

  function resetBusy(form) {
    const state = busyForms.get(form);
    if (!state) return;
    window.clearTimeout(state.timer);
    restoreAttribute(form, "aria-busy", state.aria);
    restoreAttribute(form, "tabindex", state.tabindex);
    state.buttons.forEach(({ button, disabled, aria, html, value }) => {
      button.disabled = disabled;
      restoreAttribute(button, "aria-busy", aria);
      if (button instanceof HTMLInputElement) button.value = value;
      else button.innerHTML = html;
    });
    busyForms.delete(form);
  }

  document.addEventListener("submit", event => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || event.defaultPrevented) return;
    if (busyForms.has(form)) { event.preventDefault(); return; }
    const button = event.submitter;
    if (attribute(form, button, "data-confirm") && !confirmedForms.has(form)) {
      event.preventDefault();
      event.stopImmediatePropagation();
      askConfirmation(button, form, button, () => {
        if (!form.isConnected || (button && (!button.isConnected || button.disabled))) return;
        confirmedForms.add(form);
        try { form.requestSubmit(button || undefined); }
        finally { confirmedForms.delete(form); }
      });
      return;
    }

  }, true);

  document.addEventListener("submit", event => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || event.defaultPrevented) return;
    const label = attribute(form, event.submitter, "data-busy-label");
    if (label) setBusy(form, event.submitter, label);
  });

  // Кнопка без отправки формы тоже может защищать действие подтверждением.
  document.addEventListener("click", event => {
    const button = event.target instanceof Element ? event.target.closest("button[data-confirm], input[data-confirm]") : null;
    if (!button || button.disabled || event.defaultPrevented || confirmedButtons.has(button)) return;
    if (button.form && ["submit", "image"].includes(button.type)) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    askConfirmation(button, null, button, () => {
      confirmedButtons.add(button);
      try { button.click(); } finally { confirmedButtons.delete(button); }
    });
  }, true);

  function feedback(button, text) {
    let state = feedbackStates.get(button);
    if (!state) {
      const label = button.querySelector("[data-button-label]") || button;
      state = { label, html: label.innerHTML, timer: null };
      feedbackStates.set(button, state);
    }
    clearTimeout(state.timer);
    state.label.textContent = text;
    state.timer = setTimeout(() => {
      state.label.innerHTML = state.html;
      feedbackStates.delete(button);
    }, 1500);
  }

  function isCopyField(source) {
    return source instanceof HTMLInputElement || source instanceof HTMLTextAreaElement || source instanceof HTMLSelectElement;
  }

  function fallbackCopy(source) {
    let temporary = null;
    const active = document.activeElement;
    if (isCopyField(source)) {
      temporary = document.createElement("textarea");
      temporary.value = source.value;
      temporary.className = "visually-hidden";
      (source.closest('dialog[open]') || document.body).append(temporary);
      temporary.select();
    } else {
      const range = document.createRange();
      range.selectNodeContents(source);
      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
    }
    try { return document.execCommand("copy"); } catch (_) { return false; }
    finally { temporary?.remove(); active?.focus({ preventScroll: true }); }
  }

  async function copyFrom(button) {
    const source = document.getElementById(button.dataset.copyTarget);
    if (!source) return;
    const text = isCopyField(source) ? source.value : source.textContent;
    let copied = false;
    if (navigator.clipboard && window.isSecureContext) {
      try { await navigator.clipboard.writeText(text); copied = true; } catch (_) { /* HTTP и запрет доступа используют выделение. */ }
    }
    if (!copied) copied = fallbackCopy(source);
    feedback(button, copied ? "Скопировано" : "Скопируйте выделенное");
  }

  const sidebar = document.querySelector("[data-sidebar]");
  const toggle = document.querySelector("[data-sidebar-toggle]");
  const backdrop = document.querySelector("[data-sidebar-close][hidden]");
  const desktop = window.matchMedia("(min-width: 861px)");
  let drawerOpen = false;
  let previousInert = [];

  function setSidebarOpen(open, restoreFocus = true) {
    if (!sidebar || !toggle || !backdrop) return;
    open = Boolean(open && !desktop.matches);
    if (drawerOpen === open) return;
    drawerOpen = open;
    document.body.classList.toggle("sidebar-open", open);
    toggle.setAttribute("aria-expanded", String(open));
    backdrop.hidden = !open;
    if (open) {
      const behind = Array.from(document.querySelectorAll("[data-sidebar-behind]"));
      previousInert = behind.map(element => [element, element.inert]);
      behind.forEach(element => { element.inert = true; });
      sidebar.focus({ preventScroll: true });
    } else {
      previousInert.forEach(([element, inert]) => { element.inert = inert; });
      previousInert = [];
      if (restoreFocus) toggle.focus({ preventScroll: true });
      else if (document.activeElement?.matches("[data-sidebar-close]")) sidebar.focus({ preventScroll: true });
    }
  }
  desktop.addEventListener("change", event => { if (event.matches) setSidebarOpen(false, false); });
  document.addEventListener("keydown", event => {
    if (!drawerOpen) return;
    if (event.key === "Escape") { event.preventDefault(); setSidebarOpen(false); }
    if (event.key !== "Tab") return;
    const focusable = Array.from(sidebar.querySelectorAll('a[href], button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex="0"]')).filter(el => el.getClientRects().length);
    const first = focusable[0], last = focusable[focusable.length - 1];
    if (!first) { event.preventDefault(); sidebar.focus(); }
    else if (event.shiftKey && [first, sidebar].includes(document.activeElement)) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && [last, sidebar].includes(document.activeElement)) { event.preventDefault(); first.focus(); }
  });

  function updateFileStatus(input) {
    const status = document.getElementById(input.dataset.fileInput);
    if (!status || !status.hasAttribute("data-file-status")) return;
    const files = input.files;
    status.textContent = files.length === 0 ? status.dataset.emptyText : files.length === 1 ? files[0].name : `Выбрано: ${files.length}`;
  }
  function updateFiles(root = document) { root.querySelectorAll("[data-file-input]").forEach(updateFileStatus); }
  document.addEventListener("change", event => { if (event.target.matches("[data-file-input]")) updateFileStatus(event.target); });
  document.addEventListener("reset", event => { setTimeout(() => updateFiles(event.target), 0); });

  document.addEventListener("click", event => {
    const target = event.target;
    if (!(target instanceof Element)) return;
    if (target.closest("[data-sidebar-toggle]")) setSidebarOpen(!drawerOpen);
    if (target.closest("[data-sidebar-close]")) setSidebarOpen(false);
    const close = target.closest("[data-banner-close]");
    if (close) {
      const banner = close.closest("[data-banner]");
      const stack = banner?.closest("[data-flash-stack]");
      banner?.remove();
      if (stack && !stack.querySelector("[data-banner]")) stack.remove();
    }
    const copy = target.closest("[data-copy-target]");
    if (copy) copyFrom(copy);
    const modalClose = target.closest("[data-dialog-close]");
    if (modalClose) modalClose.closest("dialog")?.close();
    const modalOpen = target.closest("[data-dialog-open]");
    if (modalOpen) document.getElementById(modalOpen.dataset.dialogOpen)?.showModal();
  });

  window.addEventListener("pageshow", () => {
    Array.from(busyForms.keys()).forEach(resetBusy);
    setSidebarOpen(false, false);
    updateFiles();
  });
  updateFiles();
  window.VenomUI = Object.freeze({ copyFrom, resetBusy, setSidebarOpen, updateFileStatus });
})();
