/* =====================================================================
   ElectroGrid — ENHANCE LAYER (JS)
   - Reveal on scroll, counter, ripple, tilt
   - Toast API: window.egToast(...)
   - Command palette (Ctrl+K)
   - Status bar with live server check
   - Auto-add scrolled class to navbar
   ===================================================================== */
(function () {
  'use strict';

  const D = document;
  const W = window;
  const ready = (fn) => (D.readyState !== 'loading') ? fn() : D.addEventListener('DOMContentLoaded', fn);
  const reduced = W.matchMedia && W.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ============================================================
     0. AUTO PAGE ANIMATION — main > .container ostida
     ============================================================ */
  function applyAutoAnim() {
    if (reduced) return;
    // Dashboard-style containers — birinchi to'plamga animatsiya
    const candidates = D.querySelectorAll(
      'main > .container, main > .container-fluid, main > .py-4, body > .container, body > .container-fluid'
    );
    candidates.forEach((el) => {
      if (!el.classList.contains('eg-anim-on-load')) {
        el.classList.add('eg-anim-on-load');
      }
    });
  }

  /* ============================================================
     1. REVEAL ON SCROLL (.eg-reveal -> .eg-visible)
     ============================================================ */
  function setupReveal() {
    if (reduced || !('IntersectionObserver' in W)) {
      D.querySelectorAll('.eg-reveal').forEach(el => el.classList.add('eg-visible'));
      return;
    }
    const io = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          e.target.classList.add('eg-visible');
          io.unobserve(e.target);
        }
      });
    }, { threshold: 0.12 });
    D.querySelectorAll('.eg-reveal').forEach(el => io.observe(el));
  }

  /* ============================================================
     2. COUNTER ANIMATION
     <span class="eg-counter" data-to="1234">0</span>
     Avto: KPI raqamlar (.kpi-value, .stat-value, .ps-val)
     ============================================================ */
  function animateCounter(el, target, duration) {
    duration = duration || 1100;
    const decimals = (String(target).split('.')[1] || '').length;
    const start = performance.now();
    const from = 0;
    function tick(now) {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      const value = from + (target - from) * eased;
      el.textContent = decimals > 0 ? value.toFixed(decimals) : Math.round(value).toLocaleString('uz-UZ');
      if (t < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }
  function setupCounters() {
    if (reduced) return;
    const els = D.querySelectorAll('.eg-counter[data-to], .kpi-value, .stat-value, .ps-val');
    if (!els.length) return;
    if (!('IntersectionObserver' in W)) {
      els.forEach(prepCounter);
      return;
    }
    const io = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          prepCounter(e.target);
          io.unobserve(e.target);
        }
      });
    }, { threshold: 0.4 });
    els.forEach(el => io.observe(el));
  }
  function prepCounter(el) {
    if (el.dataset.egCounted) return;
    const raw = (el.dataset.to || el.textContent || '').replace(/\s/g, '').replace(/,/g, '.');
    const num = parseFloat(raw.match(/-?\d+(\.\d+)?/)?.[0]);
    if (isNaN(num)) return;
    el.dataset.egCounted = '1';
    animateCounter(el, num);
  }

  /* ============================================================
     3. RIPPLE EFFECT — barcha .btn va button
     ============================================================ */
  function setupRipple() {
    D.addEventListener('click', (ev) => {
      const btn = ev.target.closest('.btn, button');
      if (!btn || btn.classList.contains('eg-no-ripple')) return;
      if (btn.matches('.navbar-toggler')) return;
      const rect = btn.getBoundingClientRect();
      const r = D.createElement('span');
      r.className = 'eg-ripple';
      r.style.left = (ev.clientX - rect.left) + 'px';
      r.style.top  = (ev.clientY - rect.top) + 'px';
      btn.appendChild(r);
      setTimeout(() => r.remove(), 650);
    });
  }

  /* ============================================================
     4. CARD TILT (3D) — .eg-tilt
     ============================================================ */
  function setupTilt() {
    if (reduced) return;
    // Auto: yirik kartalarga
    D.querySelectorAll('.kpi-card, .stat-card, .promo-stat').forEach(c => {
      if (!c.classList.contains('eg-tilt')) c.classList.add('eg-tilt');
    });
    D.querySelectorAll('.eg-tilt').forEach(card => {
      let rect = null;
      card.addEventListener('mouseenter', () => { rect = card.getBoundingClientRect(); });
      card.addEventListener('mousemove', (e) => {
        if (!rect) rect = card.getBoundingClientRect();
        const x = (e.clientX - rect.left) / rect.width - 0.5;
        const y = (e.clientY - rect.top) / rect.height - 0.5;
        card.style.transform = `translateY(-4px) perspective(900px) rotateX(${(-y * 4).toFixed(2)}deg) rotateY(${(x * 5).toFixed(2)}deg)`;
      });
      card.addEventListener('mouseleave', () => {
        rect = null;
        card.style.transform = '';
      });
    });
  }

  /* ============================================================
     5. NAVBAR SCROLL CLASS
     ============================================================ */
  function setupNavbarScroll() {
    const nav = D.querySelector('.navbar.sticky-top');
    if (!nav) return;
    const onScroll = () => {
      nav.classList.toggle('eg-scrolled', W.scrollY > 6);
    };
    onScroll();
    W.addEventListener('scroll', onScroll, { passive: true });
  }

  /* ============================================================
     6. TOAST API — window.egToast({ title, msg, type, duration })
     ============================================================ */
  function ensureToastHost() {
    let host = D.getElementById('eg-toast-host');
    if (!host) {
      host = D.createElement('div');
      host.id = 'eg-toast-host';
      D.body.appendChild(host);
    }
    return host;
  }
  W.egToast = function (opts) {
    opts = opts || {};
    const type = opts.type || 'info';
    const icons = { success: 'fa-check-circle', warning: 'fa-triangle-exclamation', error: 'fa-circle-xmark', info: 'fa-circle-info' };
    const host = ensureToastHost();
    const t = D.createElement('div');
    t.className = 'eg-toast ' + type;
    t.innerHTML = `
      <div class="ico"><i class="fas ${icons[type] || icons.info}"></i></div>
      <div class="body">
        ${opts.title ? `<div class="title">${escapeHtml(opts.title)}</div>` : ''}
        ${opts.msg ? `<div class="msg">${escapeHtml(opts.msg)}</div>` : ''}
      </div>
      <button class="close-x" aria-label="Yopish">&times;</button>
    `;
    host.appendChild(t);
    const close = () => {
      t.classList.add('eg-out');
      setTimeout(() => t.remove(), 360);
    };
    t.querySelector('.close-x').addEventListener('click', close);
    setTimeout(close, opts.duration || 4200);
    return { close };
  };
  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }

  /* ============================================================
     7. COMMAND PALETTE (Ctrl+K)
     ============================================================ */
  const PALETTE_ITEMS = [
    { icon: 'fa-house',          title: 'Bosh sahifa',          url: '/',          tag: 'Home' },
    { icon: 'fa-gauge-high',     title: 'Dashboard',            url: '/dashboard', tag: 'Asosiy' },
    { icon: 'fa-map-location-dot', title: 'Xarita',             url: '/map',       tag: 'Map' },
    { icon: 'fa-table',          title: 'Jadval',               url: '/table',     tag: 'Table' },
    { icon: 'fa-chart-line',     title: 'Grafiklar',            url: '/graphs',    tag: 'Charts' },
    { icon: 'fa-brain',          title: 'AI Model',             url: '/model',     tag: 'AI' },
    { icon: 'fa-cloud-bolt',     title: 'Bashorat',             url: '/forecast',  tag: 'Forecast' },
    { icon: 'fa-code-compare',   title: 'Solishtirish',         url: '/compare',   tag: 'Compare' },
    { icon: 'fa-calendar-days',  title: 'Kalendar',             url: '/calendar',  tag: 'Calendar' },
    { icon: 'fa-ticket',         title: 'Tiketlar',             url: '/tickets',   tag: 'Tickets' },
    { icon: 'fa-clipboard-list', title: 'Audit jurnali',        url: '/audit',     tag: 'Audit' },
    { icon: 'fa-moon',           title: 'Mavzuni almashtirish (Light/Dark)', action: 'theme', tag: 'Theme' },
  ];

  function buildPalette() {
    const back = D.createElement('div');
    back.id = 'eg-palette-backdrop';
    back.innerHTML = `
      <div id="eg-palette" role="dialog" aria-label="Buyruq paneli">
        <div class="pal-input-wrap">
          <i class="fas fa-magnifying-glass"></i>
          <input type="text" placeholder="Sahifa qidirish yoki buyruq…" autocomplete="off" />
          <span class="pal-kbd">ESC</span>
        </div>
        <div class="pal-list"></div>
      </div>
    `;
    D.body.appendChild(back);
    return back;
  }

  function setupPalette() {
    const back = buildPalette();
    const input = back.querySelector('input');
    const list = back.querySelector('.pal-list');
    let activeIdx = 0;

    function render(filter) {
      const q = (filter || '').trim().toLowerCase();
      const items = PALETTE_ITEMS.filter(it => !q || it.title.toLowerCase().includes(q) || (it.tag || '').toLowerCase().includes(q));
      activeIdx = 0;
      if (!items.length) {
        list.innerHTML = `<div class="pal-empty">Hech narsa topilmadi</div>`;
        return;
      }
      list.innerHTML = items.map((it, i) => `
        <a class="pal-item ${i === 0 ? 'active' : ''}" data-idx="${i}" ${it.url ? `href="${it.url}"` : ''} data-action="${it.action || ''}">
          <span class="pi-icon"><i class="fas ${it.icon}"></i></span>
          <span>${escapeHtml(it.title)}</span>
          <span class="pi-meta">${escapeHtml(it.tag || '')}</span>
        </a>
      `).join('');
      // refresh items
      list._items = [...list.querySelectorAll('.pal-item')];
    }

    function open() {
      back.classList.add('show');
      input.value = '';
      render('');
      setTimeout(() => input.focus(), 30);
    }
    function close() { back.classList.remove('show'); }

    function move(delta) {
      const items = list._items || [];
      if (!items.length) return;
      items[activeIdx]?.classList.remove('active');
      activeIdx = (activeIdx + delta + items.length) % items.length;
      items[activeIdx].classList.add('active');
      items[activeIdx].scrollIntoView({ block: 'nearest' });
    }
    function commit() {
      const items = list._items || [];
      const it = items[activeIdx];
      if (!it) return;
      const action = it.dataset.action;
      if (action === 'theme') {
        const cur = D.documentElement.getAttribute('data-theme') || 'light';
        const next = cur === 'dark' ? 'light' : 'dark';
        D.documentElement.setAttribute('data-theme', next);
        try { localStorage.setItem('theme-mode', next); } catch (e) {}
        close();
      } else if (it.href) {
        W.location.href = it.href;
      }
    }

    input.addEventListener('input', () => render(input.value));
    back.addEventListener('click', (e) => { if (e.target === back) close(); });
    D.addEventListener('keydown', (e) => {
      const meta = e.ctrlKey || e.metaKey;
      if (meta && (e.key === 'k' || e.key === 'K')) {
        e.preventDefault();
        back.classList.contains('show') ? close() : open();
      } else if (back.classList.contains('show')) {
        if (e.key === 'Escape') close();
        else if (e.key === 'ArrowDown') { e.preventDefault(); move(1); }
        else if (e.key === 'ArrowUp')   { e.preventDefault(); move(-1); }
        else if (e.key === 'Enter')     { e.preventDefault(); commit(); }
      }
    });
    list.addEventListener('mouseover', (e) => {
      const item = e.target.closest('.pal-item');
      if (!item) return;
      (list._items || []).forEach(x => x.classList.remove('active'));
      item.classList.add('active');
      activeIdx = parseInt(item.dataset.idx, 10) || 0;
    });

    // Hint badge in navbar (if author-badge area exists, append before it)
    try {
      const nav = D.querySelector('.navbar .navbar-collapse');
      if (nav && !D.querySelector('.eg-palette-hint')) {
        const hint = D.createElement('button');
        hint.type = 'button';
        hint.className = 'eg-palette-hint eg-no-ripple ms-auto me-2';
        hint.innerHTML = `<i class="fas fa-magnifying-glass"></i> Qidirish <kbd>Ctrl</kbd><kbd>K</kbd>`;
        hint.addEventListener('click', open);
        // Insert as first child of the collapse area on the right side
        nav.appendChild(hint);
      }
    } catch (e) { /* ignore */ }
  }

  /* ============================================================
     8. STATUS BAR (footer)
     ============================================================ */
  function setupStatusBar() {
    if (D.getElementById('eg-status-bar')) return;
    const bar = D.createElement('div');
    bar.id = 'eg-status-bar';
    bar.innerHTML = `
      <span class="sb-tag">LIVE</span>
      <span class="sb-item"><span class="eg-pulse-dot"></span> Server: <b id="sb-srv">OK</b></span>
      <span class="sb-sep">|</span>
      <span class="sb-item"><i class="fas fa-database"></i> DB: <b>OK</b></span>
      <span class="sb-sep">|</span>
      <span class="sb-item"><i class="fas fa-robot"></i> Bot: <b>OK</b></span>
      <span class="sb-sep">|</span>
      <span class="sb-item"><i class="fas fa-clock"></i> <span id="sb-time"></span></span>
      <span class="sb-sep d-none d-md-inline">|</span>
      <span class="sb-item d-none d-md-inline-flex"><i class="fas fa-bolt"></i> ElectroGrid v2.0</span>
    `;
    D.body.appendChild(bar);
    D.body.classList.add('eg-has-status-bar');
    // show after slight delay
    setTimeout(() => bar.classList.add('show'), 600);
    // live time
    function pad(n) { return n < 10 ? '0' + n : n; }
    function tick() {
      const t = new Date();
      const el = D.getElementById('sb-time');
      if (el) el.textContent = pad(t.getHours()) + ':' + pad(t.getMinutes()) + ':' + pad(t.getSeconds());
    }
    tick();
    setInterval(tick, 1000);
  }

  /* ============================================================
     9. INIT
     ============================================================ */
  ready(() => {
    try { applyAutoAnim(); } catch (e) {}
    try { setupReveal(); } catch (e) {}
    try { setupCounters(); } catch (e) {}
    try { setupRipple(); } catch (e) {}
    try { setupTilt(); } catch (e) {}
    try { setupNavbarScroll(); } catch (e) {}
    try { setupPalette(); } catch (e) {}
    try { setupStatusBar(); } catch (e) {}
  });
})();
