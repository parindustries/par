/**
 * PAR Industries i18n runtime — selector, preference storage, first-visit locale redirect.
 * Content is pre-rendered per locale; this script only handles navigation.
 */
(function () {
  'use strict';

  var config = window.PAR_I18N;
  if (!config) return;

  var STORAGE_KEY = config.storageKey || 'par_lang';
  var BOT_RE = /bot|crawl|spider|slurp|bingpreview|facebookexternalhit|linkedinbot|mediapartners|googlebot/i;

  function getStoredLocale() {
    try {
      return localStorage.getItem(STORAGE_KEY);
    } catch (e) {
      return null;
    }
  }

  function setStoredLocale(localeId) {
    try {
      localStorage.setItem(STORAGE_KEY, localeId);
    } catch (e) {}
  }

  function detectCurrentLocale() {
    var path = window.location.pathname;
    var locales = config.locales;
    var match = null;
    var matchLen = -1;

    Object.keys(locales).forEach(function (id) {
      var prefix = locales[id].path;
      if (!prefix) return;
      var segment = '/' + prefix + '/';
      if (path === '/' + prefix || path.indexOf(segment) === 0) {
        if (prefix.length > matchLen) {
          match = id;
          matchLen = prefix.length;
        }
      }
    });

    return match || config.default;
  }

  function normalizeBrowserLocale(tag) {
    if (!tag) return null;
    var lower = tag.toLowerCase().replace('_', '-');
    var map = {
      'en': 'en', 'de': 'de', 'es': 'es', 'fr': 'fr', 'pt': 'pt-br', 'pt-br': 'pt-br',
      'ar': 'ar', 'ru': 'ru', 'it': 'it', 'ja': 'ja', 'zh': 'zh-cn', 'zh-cn': 'zh-cn', 'zh-hans': 'zh-cn'
    };
    if (map[lower]) return map[lower];
    var base = lower.split('-')[0];
    return map[base] || null;
  }

  function resolveBrowserLocale() {
    var list = navigator.languages || [navigator.language || ''];
    for (var i = 0; i < list.length; i++) {
      var resolved = normalizeBrowserLocale(list[i]);
      if (resolved && config.locales[resolved]) return resolved;
    }
    return config.default;
  }

  function pageName() {
    var path = window.location.pathname;
    var pages = config.pages || ['index.html', 'productsRange.html', 'ourCustomers.html'];
    for (var i = 0; i < pages.length; i++) {
      if (path.endsWith('/' + pages[i]) || path.endsWith(pages[i])) return pages[i];
    }
    return 'index.html';
  }

  function localeUrl(localeId, page) {
    var loc = config.locales[localeId];
    if (!loc) return window.location.href;
    var base = loc.path ? '/' + loc.path : '';
    if (page === 'index.html') {
      return base ? base + '/' : '/';
    }
    return (base || '') + '/' + page;
  }

  function maybeRedirect() {
    if (BOT_RE.test(navigator.userAgent || '')) return;
    var stored = getStoredLocale();
    var current = detectCurrentLocale();
    var page = pageName();
    var here = window.location.pathname + window.location.search + window.location.hash;

    if (stored && config.locales[stored]) {
      var storedTarget = localeUrl(stored, page);
      if (here !== storedTarget) {
        window.location.replace(storedTarget);
      }
      return;
    }

    if (current !== config.default) return;

    var preferred = resolveBrowserLocale();
    if (!preferred || preferred === config.default) return;

    var target = localeUrl(preferred, page);
    if (here !== target) {
      window.location.replace(target);
    }
  }

  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function buildSelector(container) {
    var current = container.getAttribute('data-current-locale') || detectCurrentLocale();
    var currentLoc = config.locales[current] || config.locales[config.default];

    var wrap = document.createElement('div');
    wrap.className = 'lang-selector-wrap';

    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'lang-selector-btn';
    btn.setAttribute('aria-haspopup', 'listbox');
    btn.setAttribute('aria-expanded', 'false');
    btn.setAttribute('aria-label', 'Select language');
    btn.innerHTML = '<i class="icofont-globe lang-selector-icon" aria-hidden="true"></i><span class="lang-selector-label">' +
      (currentLoc ? escapeHtml(currentLoc.native) : 'English') + '</span><i class="icofont-simple-down lang-selector-caret" aria-hidden="true"></i>';

    var menu = document.createElement('div');
    menu.className = 'lang-selector-menu';
    menu.setAttribute('role', 'listbox');
    menu.setAttribute('aria-label', 'Select language');
    menu.hidden = true;

    var menuHeader = document.createElement('div');
    menuHeader.className = 'lang-selector-menu-header';
    menuHeader.textContent = 'Select language';
    menu.appendChild(menuHeader);

    var menuList = document.createElement('ul');
    menuList.className = 'lang-selector-menu-list';

    Object.keys(config.locales).forEach(function (id) {
      var loc = config.locales[id];
      var item = document.createElement('li');
      item.setAttribute('role', 'option');
      item.setAttribute('aria-selected', id === current ? 'true' : 'false');

      var link = document.createElement('a');
      link.href = localeUrl(id, pageName());
      link.lang = loc.hreflang || id;
      link.dir = loc.dir || 'ltr';
      if (id === current) link.className = 'active';
      link.innerHTML =
        '<span class="lang-option-text">' +
          '<span class="lang-option-native">' + escapeHtml(loc.native) + '</span>' +
          '<span class="lang-option-secondary">' + escapeHtml(loc.name) + '</span>' +
        '</span>' +
        (id === current
          ? '<i class="icofont-check lang-option-check" aria-hidden="true"></i>'
          : '<span class="lang-option-check" aria-hidden="true"></span>');

      link.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        setStoredLocale(id);
        window.location.assign(localeUrl(id, pageName()));
      });

      item.appendChild(link);
      menuList.appendChild(item);
    });

    menu.appendChild(menuList);

    function closeMenu() {
      menu.hidden = true;
      btn.setAttribute('aria-expanded', 'false');
      wrap.classList.remove('open');
    }

    function openMenu() {
      menu.hidden = false;
      btn.setAttribute('aria-expanded', 'true');
      wrap.classList.add('open');
    }

    wrap.addEventListener('click', function (e) {
      e.stopPropagation();
    });

    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      if (menu.hidden) openMenu();
      else closeMenu();
    });

    document.addEventListener('click', function () {
      closeMenu();
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closeMenu();
    });

    wrap.appendChild(btn);
    wrap.appendChild(menu);
    container.innerHTML = '';
    container.appendChild(wrap);
  }

  function init() {
    maybeRedirect();
    var container = document.getElementById('lang-selector');
    if (container) buildSelector(container);
    var mobile = document.getElementById('lang-selector-mobile');
    if (mobile) buildSelector(mobile);

    var current = detectCurrentLocale();
    if (!getStoredLocale()) {
      setStoredLocale(current);
    }

    if (config.locales[current] && config.locales[current].dir === 'rtl') {
      document.documentElement.setAttribute('dir', 'rtl');
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
