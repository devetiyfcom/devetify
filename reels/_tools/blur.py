BLUR_JS = r"""
(() => {
  const M = '(yanvar|fevral|mart|aprel|may|iyun|iyul|avqust|sentyabr|oktyabr|noyabr|dekabr|january|february|march|april|june|july|august|september|october|november|december|января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря|январь|февраль|март|апрель|май|июнь|июль|август|сентябрь|октябрь|ноябрь|декабрь)';
  const pats = [
    /\d{1,2}\s*[.\/-]\s*\d{1,2}\s*[.\/-]\s*\d{2,4}/,
    new RegExp('\\d{1,2}\\s*' + M, 'i'), new RegExp(M + '\\s*\\d{1,4}', 'i'),
    /\b20\d\d\b/, /\b\d{1,2}[:.]\d{2}\b/,
    /(saray|palace|hall|restoran|restaurant|şadlıq|sadliq|zalı|\bzal\b|plaza|bakı|baku|sumqayıt|gəncə|küç|prospekt|prosp\.|ünvan|events|gallery|steak|manqal|meridian|hotel|otel|park\b|ресторан|зал|дворец|ул\.|баку|адрес|venue|address|street)/i
  ];
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
    // countdown boxes reveal the date indirectly: blur the smallest element holding all its units
    document.querySelectorAll('div,section,ul,p').forEach(e => {
      if (e.dataset.dvBlur) return;
      const t = (e.innerText || '').toLowerCase();
      if (t.length < 90 && /(gün|days?|дн)/.test(t) && /(saat|hours?|час)/.test(t) && /(san|sec|сек|dəq|min|мин)/.test(t)) {
        if (![...e.children].some(c => c.dataset.dvBlur)) { e.dataset.dvBlur = 1; e.style.setProperty('filter','blur(9px)','important'); }
      }
    });
    document.querySelectorAll('iframe[src*="map"], a[href*="maps"]').forEach(e => e.style.setProperty('filter','blur(9px)','important'));
  }
  const start = () => { scan(); new MutationObserver(scan).observe(document.body, {subtree:true, childList:true, characterData:true}); setInterval(scan, 300); };
  if (document.body) start(); else document.addEventListener('DOMContentLoaded', start);
})();
"""
