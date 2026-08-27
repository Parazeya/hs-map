/**
 * The words this site writes itself, in the eleven languages the game ships.
 *
 * Everything the game names — items, bosses, places, item types, rarities — is
 * taken from its own translation files at build time and arrives in the data.
 * These are the rest: the labels and sentences the pages add around them, which
 * exist nowhere in the game and so are written here.
 *
 * Keyed by the English, so a component reads as English and a language the
 * dictionary has nothing for falls back to it rather than showing a key.
 *
 * The stat lines are absent for a different reason: the game does name them,
 * under keys of its own that no identifier in the snapshot matches, so they are
 * joined on meaning at build time and arrive in the data — see words.Words.stats.
 * 212 of the 322 are the game's own words, which is nine in ten of the lines
 * anyone actually meets. The rest keep this project's reading of the identifier
 * rather than a guess at eleven translations of it.
 */

const SAY = {
  // ── the map's controls ────────────────────────────────────────────────────
  'Fit': {
    fi: 'Sovita', pt: 'Ajustar', ru: 'Вписать', zh: '适应', ja: '全体表示',
    ko: '맞춤', de: 'Einpassen', fr: 'Ajuster', sp: 'Ajustar', pl: 'Dopasuj',
  },
  'Zone names': {
    fi: 'Alueiden nimet', pt: 'Nomes das zonas', ru: 'Названия зон', zh: '区域名称',
    ja: 'ゾーン名', ko: '지역 이름', de: 'Zonennamen', fr: 'Noms des zones',
    sp: 'Nombres de zonas', pl: 'Nazwy stref',
  },
  'Item names': {
    fi: 'Esineiden nimet', pt: 'Nomes dos itens', ru: 'Названия предметов',
    zh: '物品名称', ja: 'アイテム名', ko: '아이템 이름', de: 'Gegenstandsnamen',
    fr: 'Noms des objets', sp: 'Nombres de objetos', pl: 'Nazwy przedmiotów',
  },
  'every item in the game': {
    fi: 'pelin kaikki esineet', pt: 'todos os itens do jogo',
    ru: 'все предметы игры', zh: '游戏中的所有物品', ja: 'ゲーム内の全アイテム',
    ko: '게임의 모든 아이템', de: 'jeder Gegenstand im Spiel',
    fr: 'tous les objets du jeu', sp: 'todos los objetos del juego',
    pl: 'wszystkie przedmioty w grze',
  },
  'the world map': {
    fi: 'maailmankartta', pt: 'o mapa do mundo', ru: 'карта мира', zh: '世界地图',
    ja: 'ワールドマップ', ko: '월드 맵', de: 'die Weltkarte',
    fr: 'la carte du monde', sp: 'el mapa del mundo', pl: 'mapa świata',
  },

  // ── searching ─────────────────────────────────────────────────────────────
  'Find an item…': {
    fi: 'Etsi esine…', pt: 'Procurar um item…', ru: 'Найти предмет…',
    zh: '查找物品…', ja: 'アイテムを検索…', ko: '아이템 찾기…',
    de: 'Gegenstand suchen…', fr: 'Chercher un objet…', sp: 'Buscar un objeto…',
    pl: 'Znajdź przedmiot…',
  },
  'Find an item, or what it does…': {
    fi: 'Etsi esine tai sen vaikutus…', pt: 'Procurar um item ou o que ele faz…',
    ru: 'Найти предмет или его свойство…', zh: '查找物品或其效果…',
    ja: 'アイテムや効果を検索…', ko: '아이템 또는 효과 찾기…',
    de: 'Gegenstand oder Wirkung suchen…', fr: 'Chercher un objet ou un effet…',
    sp: 'Buscar un objeto o su efecto…', pl: 'Znajdź przedmiot lub jego efekt…',
  },
  'a stat…': {
    fi: 'ominaisuus…', pt: 'um atributo…', ru: 'характеристика…', zh: '属性…',
    ja: 'ステータス…', ko: '능력치…', de: 'Wert…', fr: 'une stat…',
    sp: 'un atributo…', pl: 'cecha…',
  },
  'all': {
    fi: 'kaikki', pt: 'todos', ru: 'все', zh: '全部', ja: 'すべて', ko: '전체',
    de: 'alle', fr: 'tous', sp: 'todos', pl: 'wszystkie',
  },
  'clear': {
    fi: 'tyhjennä', pt: 'limpar', ru: 'сбросить', zh: '清除', ja: 'クリア',
    ko: '초기화', de: 'zurücksetzen', fr: 'effacer', sp: 'limpiar', pl: 'wyczyść',
  },
  'items': {
    fi: 'esinettä', pt: 'itens', ru: 'предметов', zh: '件物品', ja: '件',
    ko: '개', de: 'Gegenstände', fr: 'objets', sp: 'objetos', pl: 'przedmiotów',
  },
  'item': {
    fi: 'esine', pt: 'item', ru: 'предмет', zh: '件物品', ja: '件', ko: '개',
    de: 'Gegenstand', fr: 'objet', sp: 'objeto', pl: 'przedmiot',
  },
  'showing': {
    fi: 'näytetään', pt: 'a mostrar', ru: 'показано', zh: '显示', ja: '表示',
    ko: '표시', de: 'gezeigt', fr: 'affichés', sp: 'mostrados', pl: 'pokazano',
  },
  'and': {
    fi: 'ja', pt: 'e', ru: 'и ещё', zh: '还有', ja: 'ほか', ko: '외',
    de: 'und', fr: 'et', sp: 'y', pl: 'i',
  },
  'more': {
    fi: 'lisää', pt: 'mais', ru: '', zh: '项', ja: '件', ko: '개',
    de: 'weitere', fr: 'de plus', sp: 'más', pl: 'więcej',
  },
  'Narrow it down.': {
    fi: 'Rajaa hakua.', pt: 'Refine a busca.', ru: 'Уточните запрос.',
    zh: '请缩小范围。', ja: '条件を絞ってください。', ko: '조건을 좁혀 보세요.',
    de: 'Grenze die Suche ein.', fr: 'Affinez la recherche.',
    sp: 'Acota la búsqueda.', pl: 'Zawęź wyszukiwanie.',
  },

  // ── what a marker or a shelf entry says ───────────────────────────────────
  'zone': {
    fi: 'alue', pt: 'zona', ru: 'зона', zh: '区域', ja: 'ゾーン', ko: '지역',
    de: 'Zone', fr: 'zone', sp: 'zona', pl: 'strefa',
  },
  'boss dungeon': {
    fi: 'pomoluola', pt: 'masmorra do chefe', ru: 'логово босса',
    zh: '首领地城', ja: 'ボスダンジョン', ko: '보스 던전', de: 'Bossverlies',
    fr: 'donjon du boss', sp: 'mazmorra del jefe', pl: 'loch bossa',
  },
  'town': {
    fi: 'kaupunki', pt: 'cidade', ru: 'город', zh: '城镇', ja: '街', ko: '마을',
    de: 'Stadt', fr: 'ville', sp: 'ciudad', pl: 'miasto',
  },
  'act': {
    fi: 'näytös', pt: 'ato', ru: 'акт', zh: '章', ja: '章', ko: '막',
    de: 'Akt', fr: 'acte', sp: 'acto', pl: 'akt',
  },
  'boss': {
    fi: 'pomo', pt: 'chefe', ru: 'босс', zh: '首领', ja: 'ボス', ko: '보스',
    de: 'Boss', fr: 'boss', sp: 'jefe', pl: 'boss',
  },
  'not a boss': {
    fi: 'ei pomo', pt: 'não é um chefe', ru: 'не босс', zh: '非首领',
    ja: 'ボスではない', ko: '보스 아님', de: 'kein Boss', fr: 'pas un boss',
    sp: 'no es un jefe', pl: 'nie boss',
  },
  'only gives these up on Inferno': {
    fi: 'antaa nämä vain Inferno-vaikeudella',
    pt: 'só larga estes no Inferno', ru: 'отдаёт это только на Inferno',
    zh: '仅在炼狱难度掉落', ja: 'インフェルノでのみ落とす',
    ko: '인페르노에서만 드랍', de: 'gibt diese nur auf Inferno her',
    fr: 'ne les lâche qu’en Inferno', sp: 'solo los suelta en Inferno',
    pl: 'oddaje je tylko na Inferno',
  },
  'Inferno Difficulty': {
    fi: 'Inferno-vaikeus', pt: 'dificuldade Inferno', ru: 'сложность Inferno',
    zh: '炼狱难度', ja: 'インフェルノ難易度', ko: '인페르노 난이도',
    de: 'Inferno-Schwierigkeit', fr: 'difficulté Inferno',
    sp: 'dificultad Inferno', pl: 'poziom Inferno',
  },
  'Inferno Only': {
    fi: 'vain Inferno', pt: 'só Inferno', ru: 'только Inferno', zh: '仅炼狱',
    ja: 'インフェルノのみ', ko: '인페르노 전용', de: 'nur Inferno',
    fr: 'Inferno seulement', sp: 'solo Inferno', pl: 'tylko Inferno',
  },
  'Inferno': {
    fi: 'Inferno', pt: 'Inferno', ru: 'Inferno', zh: '炼狱', ja: 'インフェルノ',
    ko: '인페르노', de: 'Inferno', fr: 'Inferno', sp: 'Inferno', pl: 'Inferno',
  },

  'only on Inferno': {
    fi: 'vain Infernolla', pt: 'só no Inferno', ru: 'только на Inferno',
    zh: '仅炼狱', ja: 'インフェルノのみ', ko: '인페르노 전용',
    de: 'nur auf Inferno', fr: 'seulement en Inferno', sp: 'solo en Inferno',
    pl: 'tylko na Inferno',
  },
  'anywhere': {
    fi: 'kaikkialla', pt: 'em qualquer lugar', ru: 'где угодно', zh: '任意地点',
    ja: 'どこでも', ko: '어디서나', de: 'überall', fr: 'partout',
    sp: 'en cualquier lugar', pl: 'wszędzie',
  },
  'in its own zone': {
    fi: 'omalla alueellaan', pt: 'na sua própria zona', ru: 'в своей зоне',
    zh: '在其区域内', ja: '該当ゾーン内', ko: '해당 지역에서',
    de: 'in seiner Zone', fr: 'dans sa zone', sp: 'en su zona',
    pl: 'w swojej strefie',
  },
  'Inferno only': {
    fi: 'vain Infernolla', pt: 'só no Inferno', ru: 'только Inferno',
    zh: '仅炼狱', ja: 'インフェルノのみ', ko: '인페르노 전용',
    de: 'nur Inferno', fr: 'Inferno seulement', sp: 'solo Inferno',
    pl: 'tylko Inferno',
  },
  'on the map': {
    fi: 'kartalla', pt: 'no mapa', ru: 'на карте', zh: '地图上',
    ja: 'マップ上', ko: '지도에서', de: 'auf der Karte', fr: 'sur la carte',
    sp: 'en el mapa', pl: 'na mapie',
  },
  'Zone': {
    fi: 'Alue', pt: 'Zona', ru: 'зона', zh: '区域', ja: 'ゾーン', ko: '지역',
    de: 'Zone', fr: 'zone', sp: 'zona', pl: 'strefa',
  },
  'Overworld': {
    fi: 'ylämaailma', pt: 'mundo exterior', ru: 'внешний мир', zh: '主世界',
    ja: 'オーバーワールド', ko: '오버월드', de: 'Oberwelt', fr: 'monde',
    sp: 'mundo exterior', pl: 'świat zewnętrzny',
  },
  'Dungeon': {
    fi: 'luola', pt: 'masmorra', ru: 'подземелье', zh: '地城', ja: 'ダンジョン',
    ko: '던전', de: 'Verlies', fr: 'donjon', sp: 'mazmorra', pl: 'loch',
  },
  'Dungeons': {
    fi: 'luolat', pt: 'masmorras', ru: 'подземелья', zh: '地城', ja: 'ダンジョン',
    ko: '던전', de: 'Verliese', fr: 'donjons', sp: 'mazmorras', pl: 'lochy',
  },
  'Boss Dungeon': {
    fi: 'pomoluola', pt: 'masmorra do chefe', ru: 'логово босса',
    zh: '首领地城', ja: 'ボスダンジョン', ko: '보스 던전', de: 'Bossverlies',
    fr: 'donjon du boss', sp: 'mazmorra del jefe', pl: 'loch bossa',
  },
  'Boss Dungeons': {
    fi: 'pomoluolat', pt: 'masmorras dos chefes', ru: 'логова боссов',
    zh: '首领地城', ja: 'ボスダンジョン', ko: '보스 던전', de: 'Bossverliese',
    fr: 'donjons des boss', sp: 'mazmorras de jefes', pl: 'lochy bossów',
  },
  'Act': {
    fi: 'Näytös', pt: 'Ato', ru: 'акт', zh: '章', ja: '章', ko: '막',
    de: 'Akt', fr: 'Acte', sp: 'Acto', pl: 'Akt',
  },

  'drops from': {
    fi: 'pudottaa', pt: 'largado por', ru: 'выпадает с', zh: '掉落自',
    ja: 'ドロップ元', ko: '드랍처', de: 'fällt von', fr: 'lâché par',
    sp: 'lo suelta', pl: 'wypada z',
  },
  'the odds are for standing in this zone': {
    fi: 'todennäköisyydet koskevat tällä alueella oleskelua',
    pt: 'as probabilidades são para estar nesta zona',
    ru: 'шансы указаны для нахождения в этой зоне',
    zh: '概率针对处于该区域时', ja: '確率はこのゾーンにいる場合のもの',
    ko: '확률은 이 지역에 있을 때 기준', de: 'die Chancen gelten für diese Zone',
    fr: 'les chances valent pour cette zone',
    sp: 'las probabilidades son para estar en esta zona',
    pl: 'szanse dotyczą przebywania w tej strefie',
  },
  'the odds while standing in a zone it drops in': {
    fi: 'todennäköisyys alueella, jossa se putoaa',
    pt: 'a probabilidade numa zona onde ele cai',
    ru: 'шанс при нахождении в зоне, где он падает',
    zh: '处于其掉落区域时的概率',
    ja: 'ドロップするゾーンにいる場合の確率',
    ko: '드랍되는 지역에 있을 때의 확률',
    de: 'die Chance in einer Zone, in der er fällt',
    fr: 'la chance dans une zone où il tombe',
    sp: 'la probabilidad en una zona donde cae',
    pl: 'szansa w strefie, w której wypada',
  },
  'Let it go': {
    fi: 'Vapauta', pt: 'Soltar', ru: 'Открепить', zh: '取消固定',
    ja: '固定を解除', ko: '고정 해제', de: 'Loslassen', fr: 'Relâcher',
    sp: 'Soltar', pl: 'Odepnij',
  },

  // ── when there is nothing to show ─────────────────────────────────────────
  'Nothing drops in a town.': {
    fi: 'Kaupungissa ei putoa mitään.', pt: 'Nada cai numa cidade.',
    ru: 'В городе ничего не выпадает.', zh: '城镇中没有掉落。',
    ja: '街では何も落ちません。', ko: '마을에서는 아무것도 드랍되지 않습니다.',
    de: 'In einer Stadt fällt nichts.', fr: 'Rien ne tombe en ville.',
    sp: 'En una ciudad no cae nada.', pl: 'W mieście nic nie wypada.',
  },
  'The tables tie nothing to this zone.': {
    fi: 'Taulukot eivät liitä tähän alueeseen mitään.',
    pt: 'As tabelas não ligam nada a esta zona.',
    ru: 'Таблицы ничего не связывают с этой зоной.',
    zh: '掉落表中没有与该区域相关的物品。',
    ja: 'このゾーンに結び付くものはありません。',
    ko: '이 지역과 연결된 것이 없습니다.',
    de: 'Die Tabellen verbinden nichts mit dieser Zone.',
    fr: 'Les tables n’associent rien à cette zone.',
    sp: 'Las tablas no vinculan nada a esta zona.',
    pl: 'Tabele nie wiążą nic z tą strefą.',
  },
  'Nothing else drops here.': {
    fi: 'Täältä ei putoa muuta.', pt: 'Mais nada cai aqui.',
    ru: 'Больше здесь ничего не выпадает.', zh: '这里没有其他掉落。',
    ja: 'ほかに落ちるものはありません。', ko: '여기서 다른 것은 드랍되지 않습니다.',
    de: 'Sonst fällt hier nichts.', fr: 'Rien d’autre ne tombe ici.',
    sp: 'Aquí no cae nada más.', pl: 'Nic więcej tu nie wypada.',
  },
  'Nothing is tied to this.': {
    fi: 'Tähän ei ole liitetty mitään.', pt: 'Nada está ligado a isto.',
    ru: 'С этим ничего не связано.', zh: '没有与之相关的物品。',
    ja: 'これに結び付くものはありません。', ko: '이것과 연결된 것이 없습니다.',
    de: 'Damit ist nichts verbunden.', fr: 'Rien n’y est associé.',
    sp: 'No hay nada vinculado a esto.', pl: 'Nic nie jest z tym powiązane.',
  },
  'Nothing by that name.': {
    fi: 'Ei tuon nimistä.', pt: 'Nada com esse nome.',
    ru: 'Ничего с таким названием.', zh: '没有该名称的物品。',
    ja: 'その名前のものはありません。', ko: '그런 이름은 없습니다.',
    de: 'Nichts mit diesem Namen.', fr: 'Rien de ce nom.',
    sp: 'Nada con ese nombre.', pl: 'Nic o tej nazwie.',
  },
  'No stat by that name.': {
    fi: 'Ei tuon nimistä ominaisuutta.', pt: 'Nenhum atributo com esse nome.',
    ru: 'Нет характеристики с таким названием.', zh: '没有该名称的属性。',
    ja: 'その名前のステータスはありません。', ko: '그런 이름의 능력치는 없습니다.',
    de: 'Kein Wert mit diesem Namen.', fr: 'Aucune stat de ce nom.',
    sp: 'Ningún atributo con ese nombre.', pl: 'Brak cechy o tej nazwie.',
  },
  'Nothing by that name, and nothing that does that.': {
    fi: 'Ei tuon nimistä eikä sellaista vaikutusta.',
    pt: 'Nada com esse nome, e nada que faça isso.',
    ru: 'Ничего с таким названием и ничего с таким свойством.',
    zh: '没有该名称的物品，也没有该效果的物品。',
    ja: 'その名前のものも、その効果を持つものもありません。',
    ko: '그런 이름도, 그런 효과도 없습니다.',
    de: 'Nichts mit diesem Namen und nichts, was das tut.',
    fr: 'Rien de ce nom, et rien qui fasse cela.',
    sp: 'Nada con ese nombre, y nada que haga eso.',
    pl: 'Nic o tej nazwie i nic, co to robi.',
  },
  'Pick something on the left.': {
    fi: 'Valitse jokin vasemmalta.', pt: 'Escolha algo à esquerda.',
    ru: 'Выберите что-нибудь слева.', zh: '请从左侧选择。',
    ja: '左から選んでください。', ko: '왼쪽에서 선택하세요.',
    de: 'Wähle links etwas aus.', fr: 'Choisissez quelque chose à gauche.',
    sp: 'Elige algo a la izquierda.', pl: 'Wybierz coś po lewej.',
  },
  'Reading the item table…': {
    fi: 'Luetaan esinetaulukkoa…', pt: 'A ler a tabela de itens…',
    ru: 'Читаем таблицу предметов…', zh: '正在读取物品表…',
    ja: 'アイテム表を読み込み中…', ko: '아이템 표를 읽는 중…',
    de: 'Gegenstandstabelle wird gelesen…', fr: 'Lecture de la table des objets…',
    sp: 'Leyendo la tabla de objetos…', pl: 'Wczytywanie tabeli przedmiotów…',
  },

  // ── the codex's headings ──────────────────────────────────────────────────
  'Stats': {
    fi: 'Ominaisuudet', pt: 'Atributos', ru: 'Характеристики', zh: '属性',
    ja: 'ステータス', ko: '능력치', de: 'Werte', fr: 'Stats', sp: 'Atributos',
    pl: 'Cechy',
  },
  'Lore': {
    fi: 'Tarina', pt: 'História', ru: 'Описание', zh: '背景', ja: '背景',
    ko: '설정', de: 'Hintergrund', fr: 'Histoire', sp: 'Historia', pl: 'Historia',
  },
  'Drop location': {
    fi: 'Mistä putoaa', pt: 'Onde cai', ru: 'Откуда выпадает', zh: '掉落地点',
    ja: 'ドロップ場所', ko: '드랍 위치', de: 'Fundort', fr: 'Lieu de chute',
    sp: 'Dónde cae', pl: 'Skąd wypada',
  },
  'Drop rate': {
    fi: 'Pudotustodennäköisyys', pt: 'Taxa de queda', ru: 'Шанс выпадения',
    zh: '掉落概率', ja: 'ドロップ率', ko: '드랍 확률', de: 'Fallchance',
    fr: 'Taux de chute', sp: 'Probabilidad', pl: 'Szansa wypadnięcia',
  },
  'In its zone': {
    fi: 'Omalla alueellaan', pt: 'Na sua zona', ru: 'В своей зоне',
    zh: '在其区域内', ja: '該当ゾーン内', ko: '해당 지역에서',
    de: 'In seiner Zone', fr: 'Dans sa zone', sp: 'En su zona',
    pl: 'W swojej strefie',
  },
  'Space': {
    fi: 'Tila', pt: 'Espaço', ru: 'Размер', zh: '占格', ja: 'サイズ',
    ko: '크기', de: 'Platz', fr: 'Place', sp: 'Espacio', pl: 'Miejsce',
  },
  'Made in': {
    fi: 'Tehdään', pt: 'Feito em', ru: 'Основа', zh: '制作于', ja: '作成先',
    ko: '제작 대상', de: 'Hergestellt in', fr: 'Fabriqué dans', sp: 'Se crea en',
    pl: 'Tworzone w',
  },
  'Weapons': {
    fi: 'Aseet', pt: 'Armas', ru: 'Оружие', zh: '武器', ja: '武器',
    ko: '무기', de: 'Waffen', fr: 'Armes', sp: 'Armas', pl: 'Bronie',
  },
  'Runes, in this order': {
    fi: 'Riimut, tässä järjestyksessä', pt: 'Runas, nesta ordem',
    ru: 'Руны, в этом порядке', zh: '符文，按此顺序',
    ja: 'ルーン（この順番）', ko: '룬, 이 순서대로',
    de: 'Runen, in dieser Reihenfolge', fr: 'Runes, dans cet ordre',
    sp: 'Runas, en este orden', pl: 'Runy, w tej kolejności',
  },
  'Stats, as it comes': {
    fi: 'Ominaisuudet sellaisenaan', pt: 'Atributos, como vem',
    ru: 'Характеристики, как есть', zh: '属性（基础）',
    ja: 'ステータス（標準）', ko: '능력치 (기본)', de: 'Werte, wie es kommt',
    fr: 'Stats, telles quelles', sp: 'Atributos, tal cual',
    pl: 'Cechy, jak jest',
  },

  // ── the stat variants the build labels ────────────────────────────────────
  'two-handed': {
    fi: 'kaksikätisenä', pt: 'de duas mãos', ru: 'в двуручном', zh: '双手武器',
    ja: '両手武器', ko: '양손 무기', de: 'zweihändig', fr: 'à deux mains',
    sp: 'a dos manos', pl: 'w broni dwuręcznej',
  },
  'in armour': {
    fi: 'panssarissa', pt: 'em armadura', ru: 'в доспехе', zh: '护甲上',
    ja: '防具', ko: '방어구', de: 'in Rüstung', fr: 'dans une armure',
    sp: 'en armadura', pl: 'w zbroi',
  },
  'per socket': {
    fi: 'per kolo', pt: 'por encaixe', ru: 'за гнездо', zh: '每个插槽',
    ja: 'ソケットごと', ko: '소켓당', de: 'pro Fassung', fr: 'par châsse',
    sp: 'por ranura', pl: 'na gniazdo',
  },
  'by damage type': {
    fi: 'vahinkotyypeittäin', pt: 'por tipo de dano', ru: 'по типу урона',
    zh: '按伤害类型', ja: 'ダメージ種別ごと', ko: '피해 유형별',
    de: 'nach Schadensart', fr: 'par type de dégâts',
    sp: 'por tipo de daño', pl: 'wg typu obrażeń',
  },
  'random': {
    fi: 'satunnainen', pt: 'aleatório', ru: 'случайные', zh: '随机',
    ja: 'ランダム', ko: '무작위', de: 'zufällig', fr: 'aléatoire',
    sp: 'aleatorio', pl: 'losowe',
  },
  'with a': {
    fi: 'kun kolossa on', pt: 'com um', ru: 'с камнем', zh: '镶嵌',
    ja: '装着時：', ko: '장착 시:', de: 'mit einem', fr: 'avec un',
    sp: 'con un', pl: 'z kamieniem',
  },

  // ── when it will not load ─────────────────────────────────────────────────
  'The map data would not load.': {
    fi: 'Kartan tietoja ei saatu ladattua.', pt: 'Não foi possível carregar o mapa.',
    ru: 'Данные карты не загрузились.', zh: '地图数据加载失败。',
    ja: 'マップデータを読み込めませんでした。', ko: '지도 데이터를 불러오지 못했습니다.',
    de: 'Die Kartendaten konnten nicht geladen werden.',
    fr: 'Les données de la carte n’ont pas pu être chargées.',
    sp: 'No se pudieron cargar los datos del mapa.',
    pl: 'Nie udało się wczytać danych mapy.',
  },
  'The item table would not load': {
    fi: 'Esinetaulukkoa ei saatu ladattua', pt: 'Não foi possível carregar a tabela de itens',
    ru: 'Таблица предметов не загрузилась', zh: '物品表加载失败',
    ja: 'アイテム表を読み込めませんでした', ko: '아이템 표를 불러오지 못했습니다',
    de: 'Die Gegenstandstabelle konnte nicht geladen werden',
    fr: 'La table des objets n’a pas pu être chargée',
    sp: 'No se pudo cargar la tabla de objetos',
    pl: 'Nie udało się wczytać tabeli przedmiotów',
  },
};

/**
 * One word or sentence in the reader's language.
 *
 * `words` is the game's own vocabulary, carried in the data — a rarity, a slot,
 * "Level" — and it wins, because it is what the game itself prints. Anything it
 * does not cover falls to the dictionary above, and anything neither has stays
 * in English, which is a plain answer rather than a missing one.
 */
/**
 * A drop place in the reader's language.
 *
 * Most are names — a boss, a zone, a chest — and the data carries what the game
 * calls them. Sixty of the hundred and twenty are not names at all but phrases
 * the drop tables compose: "Act I Zone 1-2", "Act V & VIII Dungeons". Those are
 * taken apart and put back together from words that are translated, which is
 * the only honest way to read them in another language.
 *
 * The difficulty in brackets stays as it is: "(Inferno Difficulty)" is the
 * tables' own note, not something the game gives a name to.
 */
export function places(lang, words, named) {
  const t = talk(lang, words);
  return (place) => {
    if (!place) return place;
    const hard = /\s*(\((?:Inferno[^)]*)\))\s*$/i.exec(place);
    const bare = hard ? place.slice(0, hard.index).trim() : place;

    // the whole string first, because the build names some of them bracket and
    // all — "Uber Reaper (Inferno Difficulty)" is a key it knows — and only
    // then the fight on its own
    // the bracket is the tables' own note about difficulty, not a name the game
    // gives, so it is translated here rather than looked up
    const note = hard
      ? ` (${t(hard[1].slice(1, -1).replace(/\b\w/g, (c) => c.toUpperCase()))})`
      : '';

    const whole = named?.(place);
    if (whole) return whole.includes('(') ? whole : whole + note;
    const said = named?.(bare);
    if (said) return said + note;

    // "Act <roman> <what><rest>", the shape the tables build
    const m = /^Act ([IVX]+(?:\s*&\s*[IVX]+)*)\s+(Boss Dungeons?|Dungeons?|Overworld|Zone)\b(.*)$/i
      .exec(bare);
    if (m) {
      const what = m[2].replace(/\b\w/g, (c) => c.toUpperCase());
      const out = `${t('Act')} ${m[1]} ${t(what)}${m[3]}`.replace(/\s+/g, ' ').trim();
      return out + (hard ? ` ${hard[1]}` : '');
    }
    return place;
  };
}

export function talk(lang, words) {
  return (text) => {
    if (!text || lang === 'en') return text;
    return words?.[text]?.[lang] ?? SAY[text]?.[lang] ?? text;
  };
}
