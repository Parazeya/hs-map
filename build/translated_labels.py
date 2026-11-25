"""Site controls and source names absent from the game vocabulary."""

LANGUAGES = ('fi', 'pt', 'ru', 'zh', 'ja', 'ko', 'de', 'fr', 'sp', 'pl')

TEXT = {
    'All variants': 'Kaikki vaihtoehdot|Todas as variantes|Все варианты|所有变体|すべての候補|모든 변형|Alle Varianten|Toutes les variantes|Todas las variantes|Wszystkie warianty',
    'Socketed item': 'Istutettu esine|Item encaixado|Вставленный камень|镶嵌物品|装着するアイテム|장착한 소켓 아이템|Eingesetzter Gegenstand|Objet serti|Objeto engarzado|Osadzony przedmiot',
    'Damage type': 'Vahinkotyyppi|Tipo de dano|Тип урона|伤害类型|ダメージタイプ|피해 유형|Schadensart|Type de dégâts|Tipo de daño|Typ obrażeń',
    'With': 'Kivi:|Com|Камень:|已镶嵌：|装着：|장착:|Mit|Avec|Con|Z:',
    'Bonuses per matching socket': 'Bonukset jokaisesta sopivasta kivestä|Bônus por gema correspondente|Бонусы за каждый подходящий камень|每个匹配镶嵌孔的加成|対応する装着アイテムごとのボーナス|일치하는 소켓마다 받는 보너스|Boni pro passendem Sockel|Bonus par gemme correspondante|Bonificaciones por gema coincidente|Premie za każdy pasujący klejnot',
    'Effects': 'Vaikutukset|Efeitos|Эффекты|效果|効果|효과|Effekte|Effets|Efectos|Efekty',
    'Possible effects': 'Mahdolliset vaikutukset|Efeitos possíveis|Возможные эффекты|可能的效果|効果の候補|가능한 효과|Mögliche Effekte|Effets possibles|Efectos posibles|Możliwe efekty',
    'Class only': 'Vain luokalle|Disponível apenas para|Только для класса|职业限定|クラス限定|직업 전용|Nur für Klasse|Réservé à la classe|Solo para la clase|Tylko dla klasy',
    'Sub Skills': 'Alitaidot|Habilidades secundárias|Поднавыки|子技能|サブスキル|하위 기술|Unterfertigkeiten|Compétences secondaires|Habilidades secundarias|Umiejętności podrzędne',
    'Random modifiers': 'Satunnaiset ominaisuudet|Modificadores aleatórios|Случайные свойства|随机词缀|ランダム修飾効果|무작위 속성|Zufällige Modifikatoren|Modificateurs aléatoires|Modificadores aleatorios|Losowe modyfikatory',
    'Triggered effects': 'Laukeavat vaikutukset|Efeitos ativados|Срабатывающие эффекты|触发效果|発動効果|발동 효과|Ausgelöste Effekte|Effets déclenchés|Efectos activados|Wyzwalane efekty',
    'chance to cast': 'mahdollisuus loitsia|de chance de lançar|шанс применить|几率施放|の確率で発動|확률로 시전|Chance zu wirken|de chances de lancer|de probabilidad de lanzar|szansy na rzucenie',
    'Auras': 'Aurat|Auras|Ауры|光环|オーラ|오라|Auren|Auras|Auras|Aury',
    'Random skill': 'Satunnainen taito|Habilidade aleatória|Случайное умение|随机技能|ランダムスキル|무작위 기술|Zufällige Fertigkeit|Compétence aléatoire|Habilidad aleatoria|Losowa umiejętność',
    'Holder Only': 'Vain kantajalle|Apenas para o portador|Только для владельца|仅对持有者生效|所持者のみ|소지자 전용|Nur für den Träger|Porteur uniquement|Solo para el portador|Tylko dla posiadacza',
    'Variant': 'Vaihtoehto|Variante|Вариант|变体|バリエーション|변형|Variante|Variante|Variante|Wariant',
    'Unidentified effect': 'Tunnistamaton vaikutus|Efeito não identificado|Неопознанный эффект|未识别效果|未特定の効果|미확인 효과|Unbekannter Effekt|Effet non identifié|Efecto no identificado|Niezidentyfikowany efekt',
    'Unidentified rune': 'Tunnistamaton riimu|Runa não identificada|Неопределённая руна|未识别符文|未特定のルーン|미확인 룬|Unbekannte Rune|Rune non identifiée|Runa no identificada|Niezidentyfikowana runa',
    'Zone references': 'Alueviittaukset|Áreas relacionadas|Связанные зоны|关联区域|関連エリア|관련 지역|Zugehörige Gebiete|Zones associées|Zonas relacionadas|Powiązane strefy',
    'Condition has not been identified.': 'Ehtoa ei tunneta.|A condição não foi identificada.|Условие пока не расшифровано.|尚未识别生效条件。|発動条件は不明です。|조건을 확인할 수 없습니다.|Die Bedingung ist unbekannt.|La condition reste inconnue.|No se ha identificado la condición.|Nie ustalono warunku.',
    'No drops listed.': 'Pudotuksia ei ole luettelossa.|Nenhum saque listado.|Добыча не указана.|没有已列出的掉落。|掲載されているドロップはありません。|등록된 드롭이 없습니다.|Keine Beute aufgeführt.|Aucun butin répertorié.|No hay botín listado.|Brak pozycji na liście łupów.',
    'seconds': 's|s|с|秒|秒|초|s|s|s|s',
    'No hero by that name.': 'Sankaria ei löytynyt.|Nenhum herói com esse nome.|Герой с таким именем не найден.|未找到该英雄。|該当するヒーローはいません。|해당 이름의 영웅이 없습니다.|Kein Held mit diesem Namen.|Aucun héros de ce nom.|No hay ningún héroe con ese nombre.|Nie ma bohatera o tej nazwie.',
    'No tag by that name.': 'Tunnistetta ei löytynyt.|Nenhuma etiqueta com esse nome.|Метка с таким названием не найдена.|未找到该标签。|該当するタグはありません。|해당 이름의 태그가 없습니다.|Kein Tag mit diesem Namen.|Aucun tag de ce nom.|No hay ninguna etiqueta con ese nombre.|Nie ma znacznika o tej nazwie.',
    'a tag…': 'Tunniste…|Uma etiqueta…|Метка…|标签…|タグ…|태그…|Ein Tag…|Un tag…|Una etiqueta…|Znacznik…',
    'Unit is unknown.': 'Yksikköä ei tunneta.|Unidade desconhecida.|Единица измерения неизвестна.|单位未知。|単位は不明です。|단위를 알 수 없습니다.|Die Einheit ist unbekannt.|L’unité est inconnue.|La unidad es desconocida.|Nieznana jednostka.',
    'Growth per level is unknown.': 'Tasonousun vaikutusta ei tunneta.|O aumento por nível é desconhecido.|Прирост за уровень неизвестен.|每级增幅未知。|レベルごとの上昇量は不明です。|레벨당 증가량을 알 수 없습니다.|Der Zuwachs je Stufe ist unbekannt.|La progression par niveau est inconnue.|Se desconoce el aumento por nivel.|Nieznany wzrost na poziom.',
    'Crystal Chest': 'Kristalliarkku|Baú de Cristal|Кристальный сундук|水晶宝箱|クリスタルチェスト|수정 상자|Kristalltruhe|Coffre de cristal|Cofre de cristal|Kryształowa skrzynia',
    'Dungeon Chest': 'Luolastoarkku|Baú da Masmorra|Сундук подземелья|地牢宝箱|ダンジョンチェスト|던전 상자|Verliestruhe|Coffre de donjon|Cofre de mazmorra|Skrzynia z lochu',
    'Ruby Chest': 'Rubiiniarkku|Baú de Rubi|Рубиновый сундук|红宝石宝箱|ルビーチェスト|루비 상자|Rubintruhe|Coffre de rubis|Cofre de rubí|Rubinowa skrzynia',
    'Gamba Machine': 'Pelipöytä|Máquina de apostas|Игровой автомат|赌博机|ギャンブルマシン|도박 기계|Glücksspielautomat|Machine à sous|Máquina de apuestas|Automat hazardowy',
}
LABELS = {key: dict(zip(LANGUAGES, values.split('|'), strict=True)) for key, values in TEXT.items()}


def fill_source_names(shelves, words):
    for key in ('Crystal Chest', 'Dungeon Chest', 'Ruby Chest', 'Gamba Machine', 'Boss Dungeons', 'Dungeons'):
        if key in shelves and key in words:
            names = shelves[key].setdefault('names', {'en': key})
            for lang, name in words[key].items():
                names.setdefault(lang, name)
