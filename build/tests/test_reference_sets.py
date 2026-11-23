import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import reference_sets


class ReferenceSetTests(unittest.TestCase):
    def test_published_membership_is_unique_and_complete(self):
        data = reference_sets.catalogue()
        self.assertEqual(len(data['sets']), 69)
        self.assertEqual(len(data['memberships']), 253)
        self.assertFalse(data['reference']['verified_for_game_build'])
        self.assertEqual(sum(bool(kit.get('bonuses')) for kit in data['sets'].values()), 65)

    def test_exact_current_key_restores_membership_and_bonus_without_changing_stats(self):
        data = reference_sets.catalogue()
        key = 'charms_abominations_brain'
        item = {'record_id': 'brain', 'type': 'Charm', 'rarity': 'Satanic Set',
                'stats': [{'id': 44, 'min': 7}], 'grants': [{'talent_id': 515}]}
        before = copy.deepcopy(item)
        items, kits = {key: item}, {}
        report = reference_sets.merge(items, kits, data)
        name = data['memberships'][key]['set']
        self.assertEqual(item['set'], name)
        self.assertEqual(item['stats'], before['stats'])
        self.assertEqual(item['grants'], before['grants'])
        self.assertEqual(kits[name]['bonuses'], data['sets'][name]['bonuses'])
        self.assertEqual(kits[name]['of'], [key])
        self.assertEqual(report['restored_records'], 1)
        self.assertFalse(item['reference_set']['verified_for_game_build'])

    def test_ordinary_sibling_and_conflicting_native_membership_are_not_overwritten(self):
        data = reference_sets.catalogue()
        key = 'charms_abominations_brain'
        normal = {'record_id': 'ordinary', 'type': 'Charm', 'rarity': 'Common'}
        current = {'record_id': 'current', 'type': 'Charm', 'rarity': 'Satanic Set', 'set': 'Current set'}
        wrong_type = {'record_id': 'wrong', 'type': 'Helmet', 'rarity': 'Satanic Set'}
        native_kit = {'of': [key], 'bonuses': [{'pieces': 2, 'lines': [{'says': 'Current bonus'}]}]}
        normal['variants'] = [current, wrong_type]
        items, kits = {key: normal}, {'Current set': native_kit}
        before = copy.deepcopy((items, kits))
        report = reference_sets.merge(items, kits, data)
        self.assertEqual((items, kits), before)
        self.assertEqual(report['restored_records'], 0)

    def test_unknown_rarity_stays_unknown_and_current_names_are_used(self):
        data = reference_sets.catalogue()
        key = 'w_flask_doctors_potion'
        item = {'record_id': 'potion', 'type': data['memberships'][key]['type']}
        name = data['memberships'][key]['set']
        names = {name: {'en': name, 'ru': 'Набор доктора'}}
        items, kits = {key: item}, {}
        reference_sets.merge(items, kits, data, names)
        self.assertNotIn('rarity', item)
        self.assertEqual(kits[name]['names'], names[name])
        self.assertEqual(item['set'], name)


if __name__ == '__main__':
    unittest.main()
