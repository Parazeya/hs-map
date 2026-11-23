import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import encyclopedia as book
import item_grant_slots as slots
from test_item_aura_slots import domain, statement
from test_native_talent_grants import fixture


class AllItemGrantTests(unittest.TestCase):
    def setUp(self):
        rows, contract = fixture()
        self.native = book.native_talent_context(rows, contract, slots.SOURCE)
        self.native['aura_slots'], _ = domain()
        self.said = lambda key: {'en': key}

    def test_all_seven_skill_slots_resolve_independently_and_preserve_source(self):
        stats = [statement(stat, value, 100 + n) for n, (stat, value) in enumerate(
            (pair for selector in (202, 205, 208, 211, 214, 217, 462)
             for pair in ((selector, 11), (selector + 1, [2, 5]))))]
        original = copy.deepcopy(stats)
        grants = book.native_skill_granted(stats, self.said, self.native)
        self.assertEqual([g['talent_id'] for g in grants], [11] * 7)
        self.assertEqual([g['levels'] for g in grants], [[2, 5]] * 7)
        self.assertEqual([s for g in grants for s in g['source_stats']], original)
        self.assertEqual(stats, [])

    def test_holder_aura_and_skill_do_not_consume_each_others_operands(self):
        stats = [statement(315, 151, 1), statement(316, [5, 10], 2),
                 statement(202, 11, 3), statement(203, [2, 4], 4)]
        auras = book.native_aura_granted(stats, self.said, self.native)
        skills = book.native_skill_granted(stats, self.said, self.native)
        self.assertEqual((auras[0]['kind'], auras[0]['holder_only'], auras[0]['levels']), ('aura', True, [5, 10]))
        self.assertEqual((skills[0]['kind'], skills[0]['talent_id'], skills[0]['levels']), ('skill', 11, [2, 4]))
        self.assertEqual(stats, [])

    def test_rank_ladder_and_random_selector_keep_their_distinct_shapes(self):
        ladder = [0, 1, 2, 2, 3, 5, 8, 13, 21, 34]
        stats = [statement(202, 11, 1), statement(203, ladder, 2),
                 statement(205, [2, 433], 3), statement(206, 3, 4)]
        grants = book.native_skill_granted(stats, self.said, self.native)
        self.assertEqual(grants[0]['level_values'], ladder)
        self.assertIsNone(grants[0]['levels'])
        self.assertTrue(grants[1]['random_skill'])
        self.assertEqual(grants[1]['skill_selector_range'], [2, 433])
        self.assertNotIn('talent_id', grants[1])
        self.assertEqual(grants[1]['levels'], [3, 3])
        self.assertEqual(stats, [])

    def test_duplicates_holes_and_changed_contracts_do_not_invent_levels(self):
        for mode in ('duplicate_selector', 'duplicate_level', 'hole', 'changed_contract'):
            stats = [statement(205, 11, 1), statement(206, [2, None] if mode == 'hole' else [2, 5], 2)]
            native = copy.deepcopy(self.native)
            if mode == 'duplicate_selector':
                stats.append(copy.deepcopy(stats[0]))
            elif mode == 'duplicate_level':
                stats.append(copy.deepcopy(stats[1]))
            elif mode == 'changed_contract':
                native['aura_slots']['skill_slots'][1]['level_stat_id'] = 203
            before = copy.deepcopy(stats)
            grants = book.native_skill_granted(stats, self.said, native)
            if mode in ('duplicate_selector', 'changed_contract'):
                self.assertEqual(grants, [])
                self.assertEqual(stats, before)
            else:
                self.assertIsNone(grants[0]['levels'])
                self.assertEqual(stats, before[1:])

    def test_conditional_storage_is_resolved_separately_from_the_base_record(self):
        base = [statement(315, 151, 1), statement(316, [5, 10], 2)]
        conditional = [statement(315, 490, 3), statement(316, [15, 20], 4),
                       statement(211, 11, 5), statement(212, [3, 4], 6)]
        base_grants = book.native_granted(base, {}, self.said, self.native)
        mode_grants = book.native_granted(conditional, {}, self.said, self.native)
        self.assertEqual([g['talent_id'] for g in base_grants], [151])
        self.assertEqual([g['talent_id'] for g in mode_grants], [490, 11])
        self.assertEqual([g['levels'] for g in mode_grants], [[15, 20], [3, 4]])
        self.assertEqual((base, conditional), ([], []))
