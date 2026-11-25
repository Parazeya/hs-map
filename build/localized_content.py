"""Translations accompanying the current game text, keyed by stable record IDs."""

# The Japanese item table placed these names against other socketables. The
# eight original Soulgem labels can all be recovered from that same locale.
JAPANESE_ITEMS = {
    'socketable_gem_gurag': ("Gurag's Soulgem", 'グラーグのソウルジェム'),
    'socketable_gem_reaper': ("Death's Soulgem", '死のソウルジェム'),
    'socketable_gem_anubis': ("Anubis' Soulgem", 'アヌビスのソウルジェム'),
    'socketable_gem_damien': ("Damien's Soulgem", 'ダミアンのソウルジェム'),
    'socketable_gem_karp': ("Karp King's Soulgem", 'カープキングのソウルジェム'),
    'socketable_gem_satan': ("Satan's Soulgem", 'サタンのソウルジェム'),
    'socketable_gem_mevius': ("Mevius' Soulgem", 'メビウスのソウルジェム'),
    'socketable_gem_odin': ("Odin's Soulgem", 'オーディンのソウルジェム'),
    'socketable_gem_cthulhu': ("Cthulhu's Soulgem", 'クトゥルフのソウルジェム'),
    'socketable_gem_angelic': ('Angelic Gem', 'エンジェリックジェム'),
    'socketable_gem_chaos': ('Chaos Gem', 'カオスジェム'),
    'socketable_gem_elemental': ('Elemental Gem', 'エレメンタルジェム'),
    'socketable_gem_moonstone': ('Moonstone Gem', 'ムーンストーンジェム'),
    'socketable_jewel_aether': ('Aether Jewel', 'エーテルジュエル'),
    'socketable_jewel_agathetheum': ('Agathetheum Jewel', 'アガテウムジュエル'),
    'socketable_jewel_clean_cut': ('Clean Cut Jewel', 'クリーンカットジュエル'),
    'socketable_jewel_exan': ('Exan Jewel', 'エグザンジュエル'),
    'socketable_jewel_fieryzen': ('Fieryzen Jewel', 'ファイアリゼンジュエル'),
    'socketable_jewel_helmon': ('Helmon Jewel', 'ヘルモンジュエル'),
    'socketable_jewel_lapislazuli': ('Lapis-Lazuli Jewel', 'ラピスラズリジュエル'),
    'socketable_jewel_lyrcon': ('Lyrcon Jewel', 'ライコンジュエル'),
    'socketable_jewel_mariane': ('Mariane Jewel', 'マリアンヌジュエル'),
    'socketable_jewel_mythgonlion': ('Mythgonlion Jewel', 'ミスゴンライオンジュエル'),
    'socketable_jewel_omnipearl': ('Omnipearl Jewel', 'オムニパールジュエル'),
    'socketable_jewel_pearlescento': ('Pearlescento Jewel', 'パールレセントジュエル'),
    'socketable_jewel_random': ('Uncut Jewel', '未研磨のジュエル'),
    'socketable_jewel_tramal': ('Tramal Jewel', 'トラマルジュエル'),
    'socketable_jewel_volcon': ('Volcon Jewel', 'ボルコンジュエル'),
    'socketable_jewel_wilrden': ('Wilrden Jewel', 'ウィルデンジュエル'),
}

GEMS = {
    'amethyst': ('Amethyst', 'アメジスト'), 'diamond': ('Diamond', 'ダイヤモンド'),
    'emerald': ('Emerald', 'エメラルド'), 'ruby': ('Ruby', 'ルビー'),
    'sapphire': ('Sapphire', 'サファイア'), 'skull': ('Skull', '頭蓋骨'),
    'topaz': ('Topaz', 'トパーズ'),
}
GRADES = {
    '': ('', ''), 'chipped_': ('Chipped ', '欠けた'), 'flawed_': ('Flawed ', '欠陥のある'),
    'flawless_': ('Flawless ', '欠陥のない'), 'pristine_': ('Pristine ', '純粋な'),
    'perfect_': ('Perfect ', '完璧な'),
}
JAPANESE_ITEMS.update({
    f'socketable_{grade}{gem}': (grade_en + gem_en, grade_ja + gem_ja)
    for grade, (grade_en, grade_ja) in GRADES.items()
    for gem, (gem_en, gem_ja) in GEMS.items()
})


def correct_japanese_item_names(items, map_items):
    def correct(names, key):
        expected = JAPANESE_ITEMS.get(key)
        if expected and names and names.get('en') == expected[0]:
            names['ja'] = expected[1]

    for key, item in items.items():
        for record in [item, *(item.get('variants') or [])]:
            correct(record.get('names'), key)
            for mode in record.get('more', []):
                condition = mode.get('condition') or {}
                correct(condition.get('names'), condition.get('item_key'))
    for item in map_items.values():
        correct(item.get('names'), item.get('key'))


# Finnish is omitted from the source quest rows. Keep site translations next
# to the stable ID and use them only when the English source still matches.
FINNISH_BOUNTIES = {
    440: ('River Raider', 'Jokirosvo', 'Suorita Gjöll-joki.', ['Jörmungar kukistettu']),
    441: ('The Golden Heist', 'Kultainen ryöstö',
          'Etsi hohtava kivi ja käytä sitä löytääksesi Kultaisen soturin patsaan Gladsheimissa. Kerää patsas.',
          ['Patsas kerätty']),
    442: ('Naga Treasury', 'Nagojen aarrekammio',
          'Nouda Kultaisen käärmeen amuletti Nagan temppelistä.', ['Amuletti löydetty', 'Temppelistä paettu']),
    443: ('The Crown of Surtr', 'Surtrin kruunu', 'Poista Surtrin kruunu Muspelheimissa.', ['Kruunu poistettu']),
    444: ('Grim Skull', 'Synkkä pääkallo', 'Etsi mystinen pääkallo Niflhelissä.', ['Pääkallo kerätty']),
    445: ('WANTED: Xor', 'ETSINTÄKUULUTETTU: Xor',
          'Etsi Pulserin avulla Xor Tapahtumahorisontista ja kukista hänet.', ['Xor kukistettu']),
    446: ('Anita’s Amulet', 'Anitan amuletti', 'Etsi Anitan amuletti Karponian mereltä.', ['Amuletti löydetty']),
    447: ('Awful Abominations', 'Kauheat hirviöt', 'Suorita Abomination-tapahtumia.', ['Valtavat arkut avattu']),
    448: ('To The Tower!', 'Torniin!', 'Suorita Kaaoksen torni.', ['Kaaoksen torni suoritettu']),
    449: ('Njal Must Die!', 'Njalin on kuoltava!', 'Etsi ja kukista Njal Lumisilla vuorilla.',
          ['Njal kukistettu', 'Njalin pää']),
    450: ('Security Measures', 'Turvatoimet', 'Korjaa jokaisessa näytöksessä yksi majakka ja käynnistä järjestelmä Dhorn Farumissa.', [
        'Kurpitsapelto – majakka korjattu', 'Jäätikön Polku – majakka korjattu', 'Kuivat kukkulat – majakka korjattu',
        'Paholaisen aukko – majakka korjattu', 'Fuji vuori – majakka korjattu', 'Ylängön hautuumaa – majakka korjattu',
        'Vastakkainen Todellisuus – majakka korjattu', 'Turvajärjestelmä käynnistetty uudelleen',
    ]),
    451: ('Hellpiercer', 'Helvetin lävistäjä',
          'Kerää räjähteet Vanhasta kaivoskylästä, hanki sytytin tohtori Tinker Dinkiltä ja sabotoi höyryjuna.',
          ['Räjähteet kerätty', 'Sytytin hankittu', 'Räjähteet asetettu', 'Räjähteet laukaistu']),
    452: ('The False Prophet Defenestration', 'Väärä profeetta ulos ikkunasta',
          'Puhu maisteri Kujalalle ja suorita hänen antamansa tehtävä.',
          ['Tehtävän todellinen luonne selvisi', 'Luthor heitetty ulos katedraalin ikkunasta']),
}


def fill_finnish_bounties(quests):
    for quest in quests:
        row = FINNISH_BOUNTIES.get(quest['id'])
        if not row:
            continue
        expected, title, brief, goals = row
        if quest['name'].get('en') != expected or len(quest['goals']) != len(goals):
            continue
        quest['name'].setdefault('fi', title)
        quest['brief'].setdefault('fi', brief)
        for objective, text in zip(quest['goals'], goals):
            objective.setdefault('fi', text)
