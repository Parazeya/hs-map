const formats = {
  en: n => `1 in ${n}`,
  fi: n => `1 / ${n}`,
  pt: n => `1 em ${n}`,
  ru: n => `1 из ${n}`,
  zh: n => `1 / ${n}`,
  ja: n => `${n}分の1`,
  ko: n => `${n}분의 1`,
  de: n => `1 zu ${n}`,
  fr: n => `1 sur ${n}`,
  sp: n => `1 de cada ${n}`,
  pl: n => `1 na ${n}`,
};

export const formatDropOdds = (lang, denominator) => (formats[lang] ?? formats.en)(denominator);
