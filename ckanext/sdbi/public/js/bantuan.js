(function () {
  var input = document.getElementById('bantuan-q');
  var empty = document.getElementById('bantuan-empty');
  var countEl = document.getElementById('bantuan-count');
  var statusEl = document.getElementById('bantuan-status');
  var resetBtn = document.getElementById('bantuan-reset');
  var chips = document.querySelectorAll('.bantuan__chip');
  var items = document.querySelectorAll('.bantuan__item');
  var sections = document.querySelectorAll('.bantuan__category');
  if (!input) return;

  var activeCategory = '';
  var total = items.length;

  function escapeHtml(value) {
    return String(value || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function tokensOf(value) {
    return String(value || '')
      .toLowerCase()
      .trim()
      .split(/\s+/)
      .filter(Boolean);
  }

  function haystack(item) {
    return [
      item.getAttribute('data-q') || '',
      item.getAttribute('data-a') || '',
      item.getAttribute('data-file-label') || '',
    ].join(' ').toLowerCase();
  }

  function matchesTokens(text, tokens) {
    if (!tokens.length) {
      return true;
    }
    return tokens.every(function (token) {
      return text.indexOf(token) !== -1;
    });
  }

  function highlight(text, tokens) {
    var raw = String(text || '');
    if (!tokens.length) {
      return escapeHtml(raw);
    }
    var lower = raw.toLowerCase();
    var ranges = [];
    tokens.forEach(function (token) {
      var from = 0;
      var at = lower.indexOf(token, from);
      while (at !== -1) {
        ranges.push([at, at + token.length]);
        from = at + token.length;
        at = lower.indexOf(token, from);
      }
    });
    ranges.sort(function (a, b) {
      return a[0] - b[0] || b[1] - a[1];
    });
    var merged = [];
    ranges.forEach(function (range) {
      var last = merged[merged.length - 1];
      if (!last || range[0] > last[1]) {
        merged.push(range.slice());
        return;
      }
      last[1] = Math.max(last[1], range[1]);
    });
    var out = '';
    var cursor = 0;
    merged.forEach(function (range) {
      out += escapeHtml(raw.slice(cursor, range[0]));
      out += '<mark>' + escapeHtml(raw.slice(range[0], range[1])) + '</mark>';
      cursor = range[1];
    });
    return out + escapeHtml(raw.slice(cursor));
  }

  function setChip(categoryId) {
    activeCategory = categoryId || '';
    chips.forEach(function (chip) {
      var on = (chip.getAttribute('data-category') || '') === activeCategory;
      chip.classList.toggle('is-active', on);
      chip.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
  }

  function paintItem(item, tokens) {
    var q = item.getAttribute('data-q') || '';
    var a = item.getAttribute('data-a') || '';
    var qText = item.querySelector('.bantuan__q-text');
    var answerText = item.querySelector('.bantuan__answer-text');
    if (qText) {
      qText.innerHTML = highlight(q, tokens);
    }
    if (answerText) {
      answerText.innerHTML = highlight(a, tokens);
    }
  }

  function filter() {
    var tokens = tokensOf(input.value);
    var shown = 0;
    items.forEach(function (item) {
      var categoryId = item.getAttribute('data-category') || '';
      var catOk = !activeCategory || categoryId === activeCategory;
      var textOk = matchesTokens(haystack(item), tokens);
      var show = catOk && textOk;
      item.hidden = !show;
      if (!show) {
        item.open = false;
      }
      paintItem(item, show ? tokens : []);
      if (show) {
        shown += 1;
      }
    });
    var filtered = Boolean(tokens.length || activeCategory);
    sections.forEach(function (section) {
      if (!filtered) {
        section.hidden = false;
        return;
      }
      var any = section.querySelector('.bantuan__item:not([hidden])');
      section.hidden = !any;
    });
    if (empty) {
      empty.hidden = shown !== 0;
    }
    if (resetBtn) {
      resetBtn.disabled = !filtered;
    }
    if (countEl) {
      countEl.textContent = shown + ' dari ' + total + ' pertanyaan';
    }
    if (statusEl) {
      if (!filtered) {
        statusEl.hidden = true;
        statusEl.textContent = '';
      } else {
        var parts = [];
        if (activeCategory) {
          var activeChip = document.querySelector('.bantuan__chip.is-active');
          parts.push('kategori ' + ((activeChip && activeChip.textContent) || activeCategory).trim());
        }
        if (tokens.length) {
          parts.push('pencarian “' + input.value.trim() + '”');
        }
        statusEl.textContent = 'Filter ' + parts.join(' · ');
        statusEl.hidden = false;
      }
    }
  }

  function resetAll() {
    input.value = '';
    setChip('');
    items.forEach(function (item) {
      item.open = false;
    });
    filter();
    input.focus();
  }

  chips.forEach(function (chip) {
    chip.addEventListener('click', function () {
      setChip(chip.getAttribute('data-category') || '');
      filter();
    });
  });

  document.querySelectorAll('[data-bantuan-reset]').forEach(function (button) {
    button.addEventListener('click', resetAll);
  });
  if (resetBtn) {
    resetBtn.addEventListener('click', resetAll);
  }

  input.addEventListener('input', filter);
  input.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') {
      resetAll();
    }
  });
  filter();

  function syncHeaderOffset() {
    var account = document.querySelector('.account-masthead');
    var masthead = document.querySelector('header.masthead');
    var bottom = 0;
    if (account) bottom = Math.max(bottom, account.getBoundingClientRect().bottom);
    if (masthead) bottom = Math.max(bottom, masthead.getBoundingClientRect().bottom);
    if (bottom > 0) {
      document.documentElement.style.setProperty('--bantuan-header-offset', Math.ceil(bottom) + 'px');
    }
  }
  syncHeaderOffset();
  window.addEventListener('resize', syncHeaderOffset);
})();
