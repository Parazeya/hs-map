import json
import sys
import unittest
from pathlib import Path

BUILD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BUILD))

import catalogue_sources
import localized_content
import translated_labels


class CatalogueSourcesTests(unittest.TestCase):
    def test_map_identity_and_destinations_match_the_current_catalogue(self):
        data = BUILD.parent / 'public' / 'data'
        world = json.loads((data / 'map.json').read_text(encoding='utf-8'))
        codex = json.loads((data / 'codex.json').read_text(encoding='utf-8'))
        for alias, key in {
            'shrunken head': 'charms_shrunken_head',
            'angel': 'w_gun_angel',
            "death's scythe": 'w_melee_deaths_scythe',
        }.items():
            row = world['items'][alias]
            self.assertEqual(row['key'], key)
            self.assertEqual(row['record_id'], codex['items'][key]['record_id'])
        self.assertIn('Act_04_05', codex['items']['gloves_frostbitten_necrosis']['map_sources']['rooms'])
        self.assertIn('Dungeon Chest', codex['items']['amulets_signet_of_kadosh']['map_sources']['shelves'])
        self.assertNotIn('map_sources', codex['items']['keys_ancient_key'])
        ak47 = codex['items']['w_gun_ak47']
        self.assertNotIn('chase', ak47)
        self.assertEqual(ak47['map_sources']['room_odds']['Act_07_05'], {'rate': 167360, 'reference': True})
        rugal = codex['items']['belts_rugals_sash_of_undertaking']
        self.assertEqual(rugal['map_sources']['room_odds']['Act_04_03'], {'rate': 155817})
        before = json.dumps([world, codex], sort_keys=True)
        catalogue_sources.attach(world['items'], world['nodes'], world['bosses'], world['places'], codex)
        self.assertEqual(json.dumps([world, codex], sort_keys=True), before)

    def test_ambiguous_names_do_not_attach_to_either_canonical_record(self):
        items = {'sample': {'rarity': 'Satanic'}}
        codex = {'items': {
            'first': {'record_id': 'a', 'names': {'en': 'Sample'}, 'rarity': 'Satanic'},
            'second': {'record_id': 'b', 'names': {'en': 'Sample'}, 'rarity': 'Satanic'},
        }}
        catalogue_sources.attach(items, [{'room': 'example', 'drops': ['sample']}], {}, {}, codex)
        self.assertEqual(items, {'sample': {'rarity': 'Satanic'}})
        self.assertTrue(all('map_sources' not in row for row in codex['items'].values()))

    def test_room_odds_require_a_drop_row_with_its_own_chance(self):
        items = {'sample': {'rarity': 'Satanic', 'rate': 500, 'chase': 100, 'zones': ['code-only']}}
        nodes = [
            {'room': 'current', 'drops': ['sample']},
            {'room': 'old', 'drops': ['sample'], 'reference_drops': ['sample'],
             'reference_drop_odds': {'sample': 125}},
            {'room': 'old-without-rate', 'drops': ['sample'], 'reference_drops': ['sample']},
            {'room': 'boss-only', 'drops': [], 'boss': 'Boss'},
            {'room': 'unlisted', 'drops': [], 'code': 'code-only'},
        ]
        shelves = {
            'Boss': {'drops': [{'item': 'sample'}]},
            'Chest': {'kind': 'source', 'drops': [{'item': 'sample'}]},
        }
        codex = {'items': {'first': {'record_id': 'a', 'names': {'en': 'Sample'}, 'rarity': 'Satanic'}}}
        catalogue_sources.attach(items, nodes, shelves, {}, codex)
        self.assertEqual(codex['items']['first']['map_sources'], {
            'rooms': ['current', 'old', 'old-without-rate', 'boss-only', 'unlisted'],
            'room_odds': {'current': {'rate': 100}, 'old': {'rate': 125, 'reference': True}},
            'shelves': ['Chest'],
        })

    def test_socket_options_use_the_canonical_japanese_gem_name(self):
        data = BUILD.parent / 'public' / 'data'
        english = json.loads((data / 'codex.json').read_text(encoding='utf-8'))['items']
        japanese = json.loads((data / 'codex.ja.json').read_text(encoding='utf-8'))['items']
        for index, option in enumerate(english['rings_azazels_despair']['more']):
            condition = option['condition']
            key = condition['item_key']
            en, ja = localized_content.JAPANESE_ITEMS[key]
            self.assertEqual(condition['names']['en'], en)
            self.assertEqual(japanese[key]['names'], ja)
            self.assertEqual(japanese['rings_azazels_despair']['more'][str(index)]['condition']['names'], ja)

    def test_site_labels_and_finnish_bounties_ship_in_the_locale_bundle(self):
        data = BUILD.parent / 'public' / 'data'
        finnish = json.loads((data / 'bounty.fi.json').read_text(encoding='utf-8'))
        self.assertEqual(len(finnish['quests']), 13)
        self.assertEqual(sum(len(quest['goals']) for quest in finnish['quests'].values()), 26)
        self.assertTrue(all({'name', 'brief', 'goals'} <= quest.keys() for quest in finnish['quests'].values()))
        for locale in translated_labels.LANGUAGES:
            codex = json.loads((data / f'codex.{locale}.json').read_text(encoding='utf-8'))
            for label in translated_labels.LABELS:
                self.assertTrue(codex['words'].get(label), (locale, label))


if __name__ == '__main__':
    unittest.main()
