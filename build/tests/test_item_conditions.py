import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import encyclopedia as book
import item_conditions as conditions

def fixture():
    return json.loads((Path(__file__).with_name('fixtures')/'item-conditions-26297349.json').read_bytes())

def domain():
    proof=conditions.certificate()
    images={(s['start_rva'],s['end_rva']-s['start_rva']):bytes.fromhex(s['bytes_hex']) for s in proof['spans']}
    return conditions.verify(conditions.SOURCE,conditions.DATA_WIN,lambda at,size:images.get((at,size),b'')),images

class ItemConditionTests(unittest.TestCase):
    def setUp(self):
        self.data=fixture()
        self.domain,self.images=domain()
        self.said=lambda key:self.data['names'].get(key)
        self.catalogue=conditions.socket_catalogue(self.data['socket_items'],self.said,self.domain)

    def modes(self,key):
        row=next(i for i in self.data['items'] if i['metadata']['tkey']==key)
        return book.variants(row,conditions=self.domain,socket_items=self.catalogue,said=self.said)

    def test_azazel_has_nine_named_soulgem_outcomes_without_cross_contamination(self):
        modes=self.modes('rings_azazels_despair')
        self.assertEqual(len(modes),9)
        self.assertEqual([m['condition']['selector'] for m in modes],[70,71,72,73,74,75,76,77,137])
        self.assertEqual(modes[0]['condition']['names']['en'],"Gurag's Soulgem")
        self.assertEqual(modes[-1]['condition']['names']['en'],"Cthulhu's Soulgem")
        self.assertEqual([len(m['stats']) for m in modes],[6,6,6,5,5,5,5,5,5])
        for mode in modes:
            self.assertTrue(mode['condition']['resolved'])
            self.assertTrue(mode['condition']['per_socket'])
            self.assertTrue(all(s['outer_selector']==mode['outer_selector'] for s in mode['stats']))

    def test_signet_includes_physical_zero_and_all_six_descriptive_damage_variants(self):
        modes=self.modes('rings_signet_of_shadows')
        self.assertEqual([m['condition']['selector'] for m in modes],list(range(6)))
        self.assertEqual([m['condition']['names']['en'] for m in modes],['Physical','Arcane','Cold','Fire','Lightning','Poison'])
        self.assertTrue(all(len(m['stats'])==3 and m['condition']['selection']=='one_generated_variant' for m in modes))
        self.assertEqual(len({m['id'] for m in modes}),6)

    def test_all_six_current_modifier_items_cover_every_original_row_and_condition(self):
        total,groups=0,0
        for row in self.data['items']:
            old=copy.deepcopy(row)
            modes=book.variants(row,conditions=self.domain,socket_items=self.catalogue,said=self.said)
            native=[m for m in modes if m.get('condition')]
            self.assertTrue(all(m['condition']['resolved'] for m in native),row['metadata']['tkey'])
            total+=sum(len(m['stats']) for m in native)
            groups+=len(native)
            self.assertEqual(row,old)
        self.assertEqual((total,groups),(160,36))

    def test_pristine_diamond_and_both_dreadnought_socket_sets_are_retained(self):
        for key in ['armors_gem_kings_garb','w_melee_gem_kings_cleaver']:
            modes=self.modes(key)
            self.assertEqual(len(modes),7)
            self.assertIn('socketable_pristine_diamond',[m['condition']['item_key'] for m in modes])
        modes=self.modes('w_gun_dreadnought')
        self.assertEqual([m['condition']['names']['en'] for m in modes],['Pristine Sapphire','Pristine Ruby'])
        self.assertEqual([len(m['stats']) for m in modes],[16,16])

    def test_wraith_has_five_generated_elemental_variants_not_an_invented_physical_one(self):
        modes=self.modes('armors_wraiths_cloak')
        self.assertEqual([m['condition']['selector'] for m in modes],[1,2,3,4,5])
        self.assertEqual(sorted(s['id'] for s in modes[-1]['stats']),[82,149,151,227])

    def test_wrong_source_or_signature_keeps_groups_separate_without_guessing_names(self):
        row=next(i for i in self.data['items'] if i['metadata']['tkey']=='rings_signet_of_shadows')
        unsupported=book.variants(row,conditions=None,socket_items=self.catalogue,said=self.said)
        self.assertEqual(len(unsupported),6)
        self.assertTrue(all(not m['condition']['resolved'] for m in unsupported))
        changed=copy.deepcopy(row)
        changed['stats_channels']['damage_type']['stats'][0]['id']=999
        modes=book.variants(changed,conditions=self.domain,socket_items=self.catalogue,said=self.said)
        self.assertFalse(modes[0]['condition']['resolved'])
        self.assertEqual(sum(len(m['stats']) for m in modes),18)

    def test_reference_or_ambiguous_socket_identifiers_cannot_supply_a_name(self):
        row=next(r for r in self.data['socket_items'] if r['metadata']['tkey']=='socketable_gem_gurag')
        reference=copy.deepcopy(row)
        reference['provenance']['ID']['kind']='reference'
        self.assertEqual(conditions.socket_catalogue([reference],self.said,self.domain),{})
        alias=copy.deepcopy(row)
        alias['metadata']['tkey']='socketable_gem_cthulhu'
        self.assertEqual(conditions.socket_catalogue([row,alias],self.said,self.domain),{})

    def test_domain_or_typed_selector_changes_do_not_fall_back_to_ordinals(self):
        selector={'domain':conditions.DOMAINS['socket'],'argument_index':0,'observed':{'kind':'value','value':{'kind':'int','value':70}}}
        self.assertEqual(conditions.selector_value(selector,'socket'),70)
        self.assertIsNone(conditions.selector_value(selector,'damage_type'))
        for value in [True,-1,1.5,None]:
            changed=copy.deepcopy(selector)
            changed['observed']['value']['value']=value
            self.assertIsNone(conditions.selector_value(changed,'socket'))
        self.assertIsNone(conditions.verify('0'*64,conditions.DATA_WIN,lambda *_:b''))
        self.assertIsNone(conditions.verify(conditions.SOURCE,'0'*64,lambda *_:b''))
        with self.assertRaisesRegex(ValueError,'transport changed'):
            conditions.verify(conditions.SOURCE,conditions.DATA_WIN,lambda *_:b'')
