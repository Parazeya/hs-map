import { speak } from './lang.js';

const preferenceKey = 'hs-map.lang';

export function preferredUiLanguage(supported = null) {
  let saved;
  try { saved = localStorage.getItem(preferenceKey); } catch { /* storage can be disabled */ }
  const browser = (navigator.language || 'en').slice(0, 2).toLowerCase();
  const choices = [saved, browser].filter(Boolean).map(lang => lang === 'es' ? 'sp' : lang);
  return choices.find(lang => !supported || supported.includes(lang)) ?? 'en';
}

export function catalogueLanguage(scope, onChange = () => {}) {
  let current = $state('en');
  let pending = $state(null);
  let failure = $state(null);
  let request = 0;

  async function pick(data, next, remember = true) {
    if (!data?.langs.includes(next)) return;
    const token = ++request;
    pending = next;
    failure = null;
    try {
      if (next !== current && next !== 'en') await speak(data, scope, next);
      if (token !== request) return;
      if (current !== next) onChange();
      current = next;
      document.documentElement.lang = next === 'sp' ? 'es' : next;
      if (remember) {
        try { localStorage.setItem(preferenceKey, next); } catch { /* the choice works for this visit */ }
      }
    } catch {
      if (token === request) failure = next;
    } finally {
      if (token === request) pending = null;
    }
  }

  function prepare(data) {
    return pick(data, preferredUiLanguage(data.langs), false);
  }

  return {
    get current() { return current; },
    get pending() { return pending; },
    get failure() { return failure; },
    pick,
    prepare,
    dismiss() { failure = null; },
  };
}
