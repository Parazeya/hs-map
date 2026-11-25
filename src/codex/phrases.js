// Start-up messages are needed before the language data can load.
const phrases = {
  'Could not load the item catalogue.': {
    fi: 'Esineluettelon lataaminen epäonnistui.', pt: 'Não foi possível carregar o catálogo de itens.',
    ru: 'Не удалось загрузить каталог предметов.', zh: '无法加载物品目录。',
    ja: 'アイテム一覧を読み込めませんでした。', ko: '아이템 목록을 불러오지 못했습니다.',
    de: 'Der Gegenstandskatalog konnte nicht geladen werden.', fr: 'Impossible de charger le catalogue d’objets.',
    sp: 'No se pudo cargar el catálogo de objetos.', pl: 'Nie udało się wczytać katalogu przedmiotów.',
  },
  'Reading the item table…': {
    fi: 'Ladataan esineluetteloa…', pt: 'Carregando o catálogo de itens…', ru: 'Загружаем каталог предметов…',
    zh: '正在加载物品目录…', ja: 'アイテム一覧を読み込み中…', ko: '아이템 목록을 불러오는 중…',
    de: 'Gegenstandskatalog wird geladen…', fr: 'Chargement du catalogue d’objets…',
    sp: 'Cargando el catálogo de objetos…', pl: 'Wczytywanie katalogu przedmiotów…',
  },
  'Item details are unavailable.': {
    fi: 'Esineen tietoja ei ole saatavilla.', pt: 'Os detalhes do item não estão disponíveis.',
    ru: 'Сведения о предмете недоступны.', zh: '无法查看物品详情。',
    ja: 'アイテムの詳細を表示できません。', ko: '아이템 상세 정보를 확인할 수 없습니다.',
    de: 'Gegenstandsdetails sind nicht verfügbar.', fr: 'Les détails de l’objet sont indisponibles.',
    sp: 'Los datos del objeto no están disponibles.', pl: 'Szczegóły przedmiotu są niedostępne.',
  },
  'Results pages': {
    fi: 'Tulossivut', pt: 'Páginas de resultados', ru: 'Страницы результатов', zh: '结果分页',
    ja: '結果のページ', ko: '결과 페이지', de: 'Ergebnisseiten', fr: 'Pages de résultats',
    sp: 'Páginas de resultados', pl: 'Strony wyników',
  },
  Previous: {
    fi: 'Edellinen', pt: 'Anterior', ru: 'Назад', zh: '上一页', ja: '前へ', ko: '이전',
    de: 'Zurück', fr: 'Précédente', sp: 'Anterior', pl: 'Wstecz',
  },
  Next: {
    fi: 'Seuraava', pt: 'Próxima', ru: 'Далее', zh: '下一页', ja: '次へ', ko: '다음',
    de: 'Weiter', fr: 'Suivante', sp: 'Siguiente', pl: 'Dalej',
  },
  'Add to comparison': {
    fi: 'Lisää vertailuun', pt: 'Adicionar à comparação', ru: 'Добавить к сравнению', zh: '加入对比',
    ja: '比較に追加', ko: '비교에 추가', de: 'Zum Vergleich hinzufügen', fr: 'Ajouter à la comparaison',
    sp: 'Añadir a la comparación', pl: 'Dodaj do porównania',
  },
  'Remove from comparison': {
    fi: 'Poista vertailusta', pt: 'Remover da comparação', ru: 'Убрать из сравнения', zh: '移出对比',
    ja: '比較から外す', ko: '비교에서 제거', de: 'Aus Vergleich entfernen', fr: 'Retirer de la comparaison',
    sp: 'Quitar de la comparación', pl: 'Usuń z porównania',
  },
  'Update comparison': {
    fi: 'Päivitä vertailu', pt: 'Atualizar comparação', ru: 'Обновить вариант', zh: '更新对比',
    ja: '比較内容を更新', ko: '비교 업데이트', de: 'Vergleich aktualisieren', fr: 'Mettre à jour la comparaison',
    sp: 'Actualizar comparación', pl: 'Zaktualizuj porównanie',
  },
  'Comparison has two items': {
    fi: 'Vertailussa on jo kaksi esinettä', pt: 'Já há dois itens na comparação', ru: 'В сравнении уже два предмета',
    zh: '对比中已有两件物品', ja: '比較にはすでに2つのアイテムがあります', ko: '이미 두 아이템을 비교 중입니다',
    de: 'Bereits zwei Gegenstände im Vergleich', fr: 'La comparaison contient déjà deux objets',
    sp: 'Ya hay dos objetos en la comparación', pl: 'W porównaniu są już dwa przedmioty',
  },
  Compare: {
    fi: 'Vertaa', pt: 'Comparar', ru: 'Сравнить', zh: '对比', ja: '比較', ko: '비교',
    de: 'Vergleichen', fr: 'Comparer', sp: 'Comparar', pl: 'Porównaj',
  },
  'Item comparison': {
    fi: 'Esinevertailu', pt: 'Comparação de itens', ru: 'Сравнение предметов', zh: '物品对比',
    ja: 'アイテム比較', ko: '아이템 비교', de: 'Gegenstandsvergleich', fr: 'Comparaison d’objets',
    sp: 'Comparación de objetos', pl: 'Porównanie przedmiotów',
  },
  'Choose another item to compare.': {
    fi: 'Valitse toinen esine vertailuun.', pt: 'Escolha outro item para comparar.',
    ru: 'Выберите ещё один предмет для сравнения.', zh: '请选择另一件物品进行对比。',
    ja: '比較するアイテムをもう1つ選んでください。', ko: '비교할 아이템을 하나 더 선택하세요.',
    de: 'Wähle einen weiteren Gegenstand zum Vergleichen.', fr: 'Choisissez un autre objet à comparer.',
    sp: 'Elige otro objeto para comparar.', pl: 'Wybierz drugi przedmiot do porównania.',
  },
  Remove: {
    fi: 'Poista', pt: 'Remover', ru: 'Убрать', zh: '移除', ja: '外す', ko: '제거',
    de: 'Entfernen', fr: 'Retirer', sp: 'Quitar', pl: 'Usuń',
  },
  'Base drop odds': {
    fi: 'Pudotuksen perustodennäköisyys', pt: 'Chance base de obtenção', ru: 'Базовый шанс выпадения',
    zh: '基础掉落概率', ja: '基本ドロップ率', ko: '기본 드롭 확률', de: 'Basis-Dropchance',
    fr: 'Chance de butin de base', sp: 'Probabilidad base de obtención', pl: 'Podstawowa szansa na zdobycie',
  },
  'Zone drop odds': {
    fi: 'Pudotustodennäköisyys alueella', pt: 'Chance de obtenção na área', ru: 'Шанс выпадения в зоне',
    zh: '区域掉落概率', ja: 'エリア内ドロップ率', ko: '지역 내 드롭 확률', de: 'Dropchance im Gebiet',
    fr: 'Chance de butin dans la zone', sp: 'Probabilidad de obtención en la zona', pl: 'Szansa na zdobycie w strefie',
  },
  'Equal odds': {
    fi: 'Sama todennäköisyys', pt: 'Chances iguais', ru: 'Одинаковый шанс', zh: '概率相同',
    ja: '同じ確率', ko: '확률이 같음', de: 'Gleiche Chance', fr: 'Chances identiques',
    sp: 'Misma probabilidad', pl: 'Równa szansa',
  },
  'Unknown odds': {
    fi: 'Todennäköisyyttä ei tiedetä', pt: 'Chance desconhecida', ru: 'Шанс неизвестен', zh: '概率未知',
    ja: '確率不明', ko: '확률을 알 수 없음', de: 'Chance unbekannt', fr: 'Chance inconnue',
    sp: 'Probabilidad desconocida', pl: 'Nieznana szansa',
  },
  'More sources': {
    fi: 'Muut lähteet', pt: 'Outras fontes', ru: 'Другие источники', zh: '其他来源', ja: 'その他の入手先',
    ko: '다른 획득처', de: 'Weitere Quellen', fr: 'Autres sources', sp: 'Otras fuentes', pl: 'Inne źródła',
  },
};

export const codexPhrase = (lang, text) => phrases[text]?.[lang] ?? text;

const oddsFormats = {
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

export const dropOddsText = (lang, denominator) => (oddsFormats[lang] ?? oddsFormats.en)(denominator);
