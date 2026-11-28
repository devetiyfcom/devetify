BLUR_JS = r"""
(() => {
  const M = '(yanvar|fevral|mart|aprel|may|iyun|iyul|avqust|sentyabr|oktyabr|noyabr|dekabr|january|february|march|april|june|july|august|september|october|november|december|января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря|январь|февраль|март|апрель|май|июнь|июль|август|сентябрь|октябрь|ноябрь|декабрь)';
  const pats = [
    /\d{1,2}\s*[.\/-]\s*\d{1,2}\s*[.\/-]\s*\d{2,4}/,
    new RegExp('\\d{1,2}\\s*' + M, 'i'), new RegExp(M + '\\s*\\d{1,4}', 'i'),
    /\b20\d\d\b/, /\b\d{1,2}[:.]\d{2}\b/,
    /(saray|palace|palas|hall|restoran|restaurant|şadlıq|sadliq|zalı|\bzal\b|plaza|bakı|baku|sumqayıt|gəncə|küç|prospekt|prosp\.|ünvan|events|gallery|steak|manqal|meridian|hotel|otel|park\b|ресторан|зал|дворец|ул\.|баку|адрес|venue|address|street)/i
  ];
  pats.push(new RegExp('^' + M + '$', 'i'),
    /^(monday|tuesday|wednesday|thursday|friday|saturday|sunday|bazar ertəsi|çərşənbə axşamı|çərşənbə|cümə axşamı|cümə|şənbə|bazar|понедельник|вторник|среда|четверг|пятница|суббота|воскресенье)$/i);
  const hit = t => pats.some(p => p.test(t));
  function scan() {
    const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let n;
    while ((n = w.nextNode())) {
      const t = n.nodeValue.trim();
      if (!t || t.length > 160 || !hit(t)) continue;
      const el = n.parentElement;
      if (!el || el === document.body || el.dataset.dvBlur) continue;
      el.dataset.dvBlur = 1;
      el.style.setProperty('filter', 'blur(9px)', 'important');
    }
    // date parts split into separate elements (day number / month / weekday)
    document.querySelectorAll('[class]').forEach(e => {
      if (e.dataset.dvBlur || e === document.body) return;
      const c = (typeof e.className === 'string' ? e.className : '');
      if (/(^|[\s_-])(date|day|month|year|weekday|time|venue|place|address|adres|unvan|location|hall)([\s_-]|$)/i.test(c) && (e.innerText || '').trim().length < 80 && (e.innerText || '').trim()) {
        e.dataset.dvBlur = 1; e.style.setProperty('filter','blur(9px)','important');
      }
    });
    // venue photos labelled with the venue name
    document.querySelectorAll('[aria-label],img[alt]').forEach(e => {
      if (e.dataset.dvBlur) return;
      const t = e.getAttribute('aria-label') || e.getAttribute('alt') || '';
      if (t && t.length < 160 && hit(t)) { e.dataset.dvBlur = 1; e.style.setProperty('filter','blur(9px)','important'); }
    });
    // countdown boxes reveal the date indirectly: blur the smallest element holding all its units
    document.querySelectorAll('div,section,ul,p').forEach(e => {
      if (e.dataset.dvBlur) return;
      const t = (e.innerText || '').toLowerCase();
      if (t.length < 90 && /(gün|days?|дн)/.test(t) && /(saat|hours?|час)/.test(t) && /(san|sec|сек|dəq|min|мин)/.test(t)) {
        if (![...e.children].some(c => c.dataset.dvBlur)) { e.dataset.dvBlur = 1; e.style.setProperty('filter','blur(9px)','important'); }
      }
    });
    document.querySelectorAll('[class*="cal" i]:not([class*="cal-" i]), [class*="calendar" i], [id*="calendar" i], [class*="countdown" i], [id*="countdown" i], [class*="timer" i]').forEach(e => { if (!e.dataset.dvBlur && e.offsetHeight < 400) { e.dataset.dvBlur = 1; e.style.setProperty('filter','blur(9px)','important'); } });
    document.querySelectorAll('iframe[src*="map"], a[href*="maps"]').forEach(e => e.style.setProperty('filter','blur(9px)','important'));
    // DV_KEEP: sections Fuad allowed to show (e.g. venue) - unblur them, but dates/times inside stay blurred
    if (window.DV_KEEP) document.querySelectorAll(window.DV_KEEP).forEach(r => [r, ...r.querySelectorAll('*')].forEach(e => {
      if (!e.style.filter) return;
      const t = [...e.childNodes].filter(n => n.nodeType === 3).map(n => n.nodeValue).join(' ').trim();   // own text only
      if (pats.slice(0, 5).some(p => p.test(t))) return;
      e.style.removeProperty('filter');
    }));
  }
  const start = () => { scan(); new MutationObserver(scan).observe(document.body, {subtree:true, childList:true, characterData:true}); setInterval(scan, 300); };
  if (document.body) start(); else document.addEventListener('DOMContentLoaded', start);
})();
"""
