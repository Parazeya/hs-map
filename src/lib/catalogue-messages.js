const labels = {
  en: ['Could not load skills.', 'Loading skills…', 'Could not load bounties.', 'Loading bounties…', 'Could not load the selected language.'],
  fi: ['Taitoja ei voitu ladata.', 'Ladataan taitoja…', 'Palkkiotehtäviä ei voitu ladata.', 'Ladataan palkkiotehtäviä…', 'Valittua kieltä ei voitu ladata.'],
  pt: ['Não foi possível carregar as habilidades.', 'Carregando habilidades…', 'Não foi possível carregar as missões de recompensa.', 'Carregando missões de recompensa…', 'Não foi possível carregar o idioma selecionado.'],
  ru: ['Не удалось загрузить умения.', 'Загружаем умения…', 'Не удалось загрузить поручения.', 'Загружаем поручения…', 'Не удалось загрузить выбранный язык.'],
  zh: ['无法加载技能。', '正在加载技能…', '无法加载悬赏任务。', '正在加载悬赏任务…', '无法加载所选语言。'],
  ja: ['スキルを読み込めませんでした。', 'スキルを読み込み中…', '賞金クエストを読み込めませんでした。', '賞金クエストを読み込み中…', '選択した言語を読み込めませんでした。'],
  ko: ['스킬을 불러오지 못했습니다.', '스킬을 불러오는 중…', '현상금 퀘스트를 불러오지 못했습니다.', '현상금 퀘스트를 불러오는 중…', '선택한 언어를 불러오지 못했습니다.'],
  de: ['Fertigkeiten konnten nicht geladen werden.', 'Fertigkeiten werden geladen…', 'Kopfgeldaufträge konnten nicht geladen werden.', 'Kopfgeldaufträge werden geladen…', 'Die gewählte Sprache konnte nicht geladen werden.'],
  fr: ['Impossible de charger les compétences.', 'Chargement des compétences…', 'Impossible de charger les contrats.', 'Chargement des contrats…', 'Impossible de charger la langue sélectionnée.'],
  sp: ['No se pudieron cargar las habilidades.', 'Cargando habilidades…', 'No se pudieron cargar los encargos.', 'Cargando encargos…', 'No se pudo cargar el idioma seleccionado.'],
  pl: ['Nie udało się wczytać umiejętności.', 'Wczytywanie umiejętności…', 'Nie udało się wczytać zleceń.', 'Wczytywanie zleceń…', 'Nie udało się wczytać wybranego języka.'],
};

export function catalogueMessages(lang) {
  const [skillsError, skillsLoading, bountyError, bountyLoading, languageError] = labels[lang] ?? labels.en;
  return { skillsError, skillsLoading, bountyError, bountyLoading, languageError };
}
