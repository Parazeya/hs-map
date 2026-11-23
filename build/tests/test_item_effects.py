import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import encyclopedia as book
import item_effects as effects
from test_native_talent_grants import fixture
from test_item_aura_slots import statement, domain as aura_domain

def domain():
    proof=effects.certificate()
    rows={(s['start_rva'],s['end_rva']-s['start_rva']):bytes.fromhex(s['bytes_hex']) for s in proof['spans']}
    rows.update({(s['rva'],16):bytes.fromhex(s['bytes_hex']) for s in proof['numeric_boxes']})
    return effects.verify(effects.SOURCE,lambda at,size:rows.get((at,size),b''),effects.DATA_WIN),rows

class ItemEffectTests(unittest.TestCase):
    def setUp(self):
        rows,contract=fixture()
        self.native=book.native_talent_context(rows,contract,effects.SOURCE)
        self.native['aura_slots'],_=aura_domain()
        self.native['item_effects'],self.images=domain()
        self.said=lambda key:{'en':key,'ru':key}

    def test_rakhul_chance_and_level_have_distinct_native_operand_roles(self):
        stats=[statement(113,515,1),statement(114,[3,10],2),statement(115,[6,13],3)]
        old=copy.deepcopy(stats)
        grants=book.native_triggered(stats,self.said,self.native)
        self.assertEqual((grants[0]['talent_key'],grants[0]['levels'],grants[0]['chance']),('rakhulsCarnage',[3,10],[6,13]))
        self.assertEqual(grants[0]['trigger_key'],'when_attacking')
        self.assertEqual(grants[0]['source_stats'],old)
        self.assertEqual(stats,[])

    def test_all_seven_trigger_events_use_the_same_explicit_roles(self):
        for slot in effects.certificate()['settings']['trigger_slots']:
            n=slot['selector_stat_id']
            stats=[statement(n,11,1),statement(n+1,[5,15],2),statement(n+2,20,3)]
            grant=book.native_triggered(stats,self.said,self.native)[0]
            self.assertEqual((grant['levels'],grant['chance'],grant['trigger_key']),([5,15],[20,20],slot['event_key']))
            self.assertEqual(stats,[])

    def test_relic_ladders_keep_all_ranks_and_partial_chances_are_not_filled(self):
        ranks=[1,2,3,4,5,6,7,8,9,10]
        stats=[statement(116,11,1),statement(117,ranks,2),statement(118,[5,None],3)]
        grant=book.native_triggered(stats,self.said,self.native)[0]
        self.assertEqual(grant['level_values'],ranks)
        self.assertNotIn('chance',grant)
        self.assertEqual([s['id'] for s in stats],[118])

    def test_outer_socket_keys_never_join_or_hide_each_others_operands(self):
        stats=[]
        for n,(selector,chance) in enumerate(((57,25),(51,100))):
            for sid,value in ((113,11),(114,5+n),(115,chance)):
                row=statement(sid,value,100+n*10+sid)
                row['outer_selector']={'domain':'itemBaseSocketStatStruct.outer_key','observed':selector}
                stats.append(row)
        old=copy.deepcopy(stats)
        grants=book.native_granted_scoped(stats,{},self.said,self.native)
        self.assertEqual([g['chance'] for g in grants],[[25,25],[100,100]])
        self.assertEqual([g['outer_selector']['observed'] for g in grants],[57,51])
        self.assertEqual([s for g in grants for s in g['source_stats']],old)
        self.assertEqual(stats,[])

    def test_class_restrictions_and_weapon_parameters_keep_every_source_statement(self):
        stats=[statement(202,11,1),statement(203,[3,5],2),statement(204,1,3),
               statement(24,58,4),statement(447,30,5)]
        original=copy.deepcopy(stats)
        grants=book.native_granted(stats,{},self.said,self.native)
        mechanics=book.native_presentation(stats,grants,self.said,self.native)
        self.assertEqual(grants[0]['class_names']['en'],'viking')
        represented=[s for g in grants for s in g['source_stats']]+[s for m in mechanics for s in m['source_stats']]
        self.assertEqual(sorted(represented,key=lambda s:s['source']['rva']),original)
        self.assertEqual(stats,[])

    def test_random_special_skill_and_subskill_bonus_do_not_invent_a_fixed_talent(self):
        stats=[statement(444,1,1),statement(445,[20,30],2),statement(419,[2,433],3),statement(420,1,4)]
        grants=[]
        book.native_presentation(stats,grants,self.said,self.native)
        self.assertEqual([g['kind'] for g in grants],['subskills','skill'])
        self.assertTrue(all(g['random_skill'] and 'talent_id' not in g for g in grants))
        self.assertEqual(grants[-1]['levels'],[20,30])
        self.assertEqual(stats,[])

    def test_bone_spirit_capability_never_invents_a_healing_unit(self):
        stats=[statement(473,8,1)]
        grants=[]
        book.native_presentation(stats,grants,self.said,self.native)
        self.assertFalse(grants[0]['numeric_unit_certified'])
        self.assertEqual(grants[0]['raw_magnitude'],{'range':[8,8]})
        self.assertNotIn('unit',grants[0])
        self.assertEqual(stats,[])

    def test_a_conditional_class_selector_is_named_without_joining_another_store(self):
        row=statement(21,24,1)
        old=copy.deepcopy(row)
        stats=[row]
        book.native_presentation(stats,[],self.said,self.native)
        self.assertEqual(stats[0]['value_names']['en'],'prophet')
        self.assertEqual(stats[0]['source_stats'],[old])
        self.assertNotIn('unresolved',stats[0])

    def test_wrong_source_domain_or_changed_native_bytes_withholds_interpretation(self):
        self.assertIsNone(effects.verify('0'*64,lambda *_:b'',effects.DATA_WIN))
        self.assertIsNone(effects.verify(effects.SOURCE,lambda *_:b'','0'*64))
        with self.assertRaisesRegex(ValueError,'transport changed'):
            effects.verify(effects.SOURCE,lambda *_:b'',effects.DATA_WIN)
        native=copy.deepcopy(self.native)
        native['item_effects']['settings']['trigger_slots'][0]['level_stat_id']=115
        stats=[statement(113,515,1),statement(114,3,2),statement(115,6,3)]
        before=copy.deepcopy(stats)
        self.assertEqual(book.native_triggered(stats,self.said,native),[])
        self.assertEqual(stats,before)
