"""Repairs must remove leakage without inventing labels or moving test into train."""
import copy
import unittest

from repair_training_data import repair_rows, require_isolation


def row(case, partition='train', roots=(), label=0, **extra):
    return dict(case_id=case, cohort='processed_sms', partition=partition,
                roots=list(roots), template=case, model_input=case, source_group='',
                label=label, label_provenance='ai_semantic_review',
                reference_status='no_published_reference_match',
                source_trace='matches_recorded_source_and_review', **extra)


class RepairTrainingDataTests(unittest.TestCase):
    def test_private_hosting_tenants_also_respect_icann_owner_domain(self):
        a = row('tenant-a', roots=['a.blogspot.com'])
        b = row('tenant-b', 'test', ['b.blogspot.com'])
        a['icann_roots'] = b['icann_roots'] = ['blogspot.com']
        result, _ = repair_rows([a, b])
        self.assertEqual([r['partition'] for r in result], ['quarantine', 'test'])

    def test_transitive_domain_bridge_is_removed_from_train_across_branches(self):
        rows = [row('a', roots=['one.com', 'two.com']), row('b', roots=['two.com']),
                row('test', 'test', ['one.com']), row('safe', roots=['other.com'])]
        rows[0]['cohort'] = 'bundle_url'
        rows[0]['url'] = 'https://one.com/?next=https://two.com/'
        before = copy.deepcopy(rows)
        result, proof = repair_rows(rows)
        indexed = {r['case_id']: r for r in result}
        self.assertEqual(indexed['a']['partition'], 'quarantine')
        self.assertEqual(indexed['b']['partition'], 'quarantine')
        self.assertEqual(indexed['safe']['partition'], 'train')
        self.assertEqual(indexed['test']['partition'], 'test')
        self.assertEqual(rows, before)
        self.assertEqual(proof['cross_partition_keys'], [])
        self.assertFalse(proof['campaign_independence_proven'])

    def test_validation_touching_test_is_quarantined_and_never_promoted(self):
        rows = [row('v', 'validation', ['app.link']), row('t', 'test', ['app.link'])]
        result, _ = repair_rows(rows)
        self.assertEqual([r['partition'] for r in result], ['quarantine', 'test'])
        self.assertTrue(all(r['do_not_train'] for r in result))

    def test_reference_conflict_is_quarantined_without_automatic_relabel(self):
        item = row('conflict', label=0)
        item['reference_status'] = 'source_scope_conflict_pending_review'
        result, _ = repair_rows([item, row('weak')])
        self.assertEqual(result[0]['partition'], 'quarantine')
        self.assertEqual(result[0]['label'], 0)
        self.assertIn('reference_label_conflict', result[0]['repair_reasons'])
        self.assertEqual(result[1]['partition'], 'train')
        self.assertFalse(result[1]['expert_verified_by_repair'])

    def test_exact_content_conflicts_quarantine_both_labels_but_root_mixed_labels_are_valid(self):
        a, b = row('a'), row('b', label=1)
        b['model_input'] = a['model_input']
        c, d = row('c', roots=['shared.com']), row('d', roots=['shared.com'], label=1)
        result, _ = repair_rows([a, b, c, d])
        self.assertEqual([r['partition'] for r in result], ['quarantine', 'quarantine', 'train', 'train'])

    def test_known_campaign_and_similarity_edges_are_kept_in_one_role(self):
        a, b = row('a'), row('b', 'test')
        a['campaign_id'], b['campaign_id'] = 'real-campaign', 'real-campaign'
        c, d = row('c'), row('d', 'validation')
        result, proof = repair_rows([a, b, c, d], [(2, 3)])
        self.assertEqual([r['partition'] for r in result], ['quarantine', 'test', 'quarantine', 'validation'])
        self.assertEqual(proof['cross_partition_similarity_edges'], 0)

    def test_quarantined_holdout_still_reserves_its_entire_group(self):
        t = row('bad-test', 'test', ['reserved.com'])
        t['url_quality_flags'] = ['literal_escaped_line_separator']
        result, _ = repair_rows([row('train', roots=['reserved.com']), t])
        self.assertEqual([r['partition'] for r in result], ['quarantine', 'quarantine'])

    def test_gate_rejects_reintroduced_leakage_and_missing_campaign_evidence(self):
        rows = [row('a', roots=['same.com']), row('t', 'test', ['same.com'])]
        with self.assertRaisesRegex(ValueError, 'isolation'):
            require_isolation(rows)
        cleaned, proof = repair_rows(rows)
        require_isolation(cleaned)
        self.assertFalse(proof['all_labels_expert_verified'])
        with self.assertRaisesRegex(ValueError, 'campaign'):
            require_isolation(cleaned, require_campaigns=True)
        with self.assertRaisesRegex(ValueError, 'expert'):
            require_isolation(cleaned, require_expert=True)

    def test_invalid_labels_and_missing_evidence_fail_closed(self):
        for bad in [row('null', label=None), row('bool', label=True), row('unknown', label=2)]:
            with self.subTest(case=bad['case_id']), self.assertRaises(ValueError):
                repair_rows([bad])
        missing = row('missing')
        del missing['source_trace']
        with self.assertRaises(ValueError):
            repair_rows([missing])


if __name__ == '__main__':
    unittest.main()
