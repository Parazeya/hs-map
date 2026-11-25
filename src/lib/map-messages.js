// Startup errors also need labels when map.json and its translations are unavailable.
const labels = {
  en: ['Could not load the map.', 'Try again', 'Loading the map…', 'Drop locations', 'No items found.', 'Close', 'Show more'],
  fi: ['Kartan lataaminen epäonnistui.', 'Yritä uudelleen', 'Ladataan karttaa…', 'Pudotuspaikat', 'Esineitä ei löytynyt.', 'Sulje', 'Näytä lisää'],
  pt: ['Não foi possível carregar o mapa.', 'Tentar novamente', 'Carregando o mapa…', 'Locais de obtenção', 'Nenhum item encontrado.', 'Fechar', 'Mostrar mais'],
  ru: ['Не удалось загрузить карту.', 'Повторить', 'Загрузка карты…', 'Где выпадает', 'Предметы не найдены.', 'Закрыть', 'Показать ещё'],
  zh: ['无法加载地图。', '重试', '正在加载地图…', '掉落地点', '未找到物品。', '关闭', '显示更多'],
  ja: ['マップを読み込めませんでした。', '再試行', 'マップを読み込み中…', 'ドロップ場所', 'アイテムが見つかりません。', '閉じる', 'さらに表示'],
  ko: ['지도를 불러오지 못했습니다.', '다시 시도', '지도를 불러오는 중…', '드롭 위치', '아이템을 찾을 수 없습니다.', '닫기', '더 보기'],
  de: ['Die Karte konnte nicht geladen werden.', 'Erneut versuchen', 'Karte wird geladen…', 'Fundorte', 'Keine Gegenstände gefunden.', 'Schließen', 'Mehr anzeigen'],
  fr: ['Impossible de charger la carte.', 'Réessayer', 'Chargement de la carte…', 'Lieux d’obtention', 'Aucun objet trouvé.', 'Fermer', 'Afficher plus'],
  sp: ['No se pudo cargar el mapa.', 'Reintentar', 'Cargando el mapa…', 'Dónde encontrarlo', 'No se encontraron objetos.', 'Cerrar', 'Mostrar más'],
  pl: ['Nie udało się wczytać mapy.', 'Spróbuj ponownie', 'Wczytywanie mapy…', 'Miejsca zdobycia', 'Nie znaleziono przedmiotów.', 'Zamknij', 'Pokaż więcej'],
};

export function mapMessages(lang) {
  const [unavailable, retry, loading, sources, emptyItems, close, showMore] = labels[lang] ?? labels.en;
  return { unavailable, retry, loading, sources, emptyItems, close, showMore };
}
