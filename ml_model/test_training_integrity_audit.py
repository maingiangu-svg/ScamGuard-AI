"""Audit evidence must distinguish domain overlap, campaign proxies and truth."""
import unittest

from external_training import RegisteredDomains
from audit_training_integrity import audit_domain_hosts, check_sms_trace, exact_sms, overlap_records, reference_status, safe_training_plan, url_identity, url_quality_flags


class TrainingIntegrityAuditTests(unittest.TestCase):
    def test_registered_domain_respects_multilevel_private_and_exception_suffixes(self):
        domain = RegisteredDomains('com\ncom.vn\nco.uk\nblogspot.com\n*.ck\n!www.ck\n')
        self.assertEqual(domain('login.bank.com.vn'), 'bank.com.vn')
        self.assertEqual(domain('a.bank.co.uk'), 'bank.co.uk')
        self.assertEqual(domain('a.person.blogspot.com'), 'person.blogspot.com')
        self.assertEqual(domain('a.b.ck'), 'a.b.ck')
        self.assertEqual(domain('a.www.ck'), 'www.ck')

    def test_distinct_hostnames_do_not_hide_shared_registered_domain(self):
        rows = [{'case_id':'a','partition':'train','roots':['bank.com.vn']},
                {'case_id':'b','partition':'test','roots':['bank.com.vn']},
                {'case_id':'c','partition':'test','roots':['other.com']}]
        overlaps = overlap_records('url', rows, 'roots', 'registered_domain')
        self.assertEqual(len(overlaps), 1)
        self.assertEqual(overlaps[0]['key'], 'bank.com.vn')
        self.assertEqual(overlaps[0]['left_case_ids'], ['a'])
        self.assertEqual(overlaps[0]['right_case_ids'], ['b'])

    def test_empty_keys_do_not_create_false_campaign_groups(self):
        rows = [{'case_id':'a','partition':'train','template':''},
                {'case_id':'b','partition':'test','template':''}]
        self.assertEqual(overlap_records('sms', rows, 'template', 'template_proxy'), [])

    def test_independent_extractor_catches_bare_new_tld_and_defanging(self):
        domain = RegisteredDomains('link\ncc\nis\n')
        hosts, ambiguous = audit_domain_hosts('Track grubhub.app.link/sms or hxxps://bank[.]cc/Login. Smallie.is going to renew.', domain)
        self.assertIn('grubhub.app.link', hosts)
        self.assertIn('bank.cc', hosts)
        self.assertNotIn('smallie.is', hosts)
        self.assertIn('smallie.is', ambiguous)

    def test_source_disagreement_is_not_an_automatic_label_correction(self):
        result = reference_status(0, {1})
        self.assertEqual(result, 'source_scope_conflict_pending_review')
        self.assertEqual(reference_status(0, {0, 1}), 'reference_itself_conflicted')
        self.assertEqual(reference_status(0, {0}), 'agrees_with_published_reference')
        self.assertEqual(reference_status(0, set()), 'no_published_reference_match')

    def test_compound_escaped_urls_are_flagged_without_condemning_redirect_queries(self):
        self.assertIn('literal_escaped_line_separator', url_quality_flags(r'http://a.example/path\nother.example/'))
        self.assertEqual(url_quality_flags('http://a.example/?next=https://b.example/'), [])

    def test_url_identity_preserves_case_sensitive_paths_and_unifies_root_slash(self):
        self.assertEqual(url_identity('https://BANK.example/'), url_identity('http://bank.example'))
        self.assertNotEqual(url_identity('https://bank.example/F0i'), url_identity('https://bank.example/f0i'))
        self.assertNotEqual(url_identity('https://a.example/x'), url_identity('https://b.example/x'))

    def test_sms_exact_reference_join_does_not_mask_phone_numbers(self):
        self.assertEqual(exact_sms(' Hello\nWORLD '), exact_sms('hello world'))
        self.assertNotEqual(exact_sms('Call 12345678'), exact_sms('Call 87654321'))

    def test_legacy_source_record_is_recovered_only_from_a_traceable_case_id(self):
        row = {'source':'project_legacy_review','case_id':'OLD-745','raw_text':'hello','original_label':'0','label':0}
        tables = ([], [], [], {}, {}, {745:{'raw_text':'hello','original_label':'0','proposed_label':0}})
        self.assertEqual(check_sms_trace(row, tables), 'matches_recorded_source_and_review')
        self.assertEqual(check_sms_trace(dict(row, case_id='untraceable'), tables), 'unresolved_source_record')

    def test_plan_propagates_holdout_exclusion_without_promoting_heldout_rows(self):
        rows = [{'case_id':'a','partition':'train','roots':['a.com','b.com'],'template':'one'},
                {'case_id':'b','partition':'train','roots':['b.com'],'template':'two'},
                {'case_id':'t','partition':'test','roots':['a.com'],'template':'three'},
                {'case_id':'v','partition':'validation','roots':[],'template':'four'},
                {'case_id':'c','partition':'train','roots':['c.com'],'template':'four'},
                {'case_id':'d','partition':'train','roots':['d.com'],'template':'five'},
                {'case_id':'v2','partition':'validation','roots':['a.com'],'template':'six'}]
        plan = {r['case_id']:r for r in safe_training_plan(rows)}
        for case in ['a','b','c']:
            self.assertFalse(plan[case]['eligible_under_group_isolation'])
        self.assertTrue(plan['d']['eligible_under_group_isolation'])
        for case in ['t','v']:
            self.assertTrue(plan[case]['do_not_train'])
            self.assertFalse(plan[case]['eligible_under_group_isolation'])
        self.assertEqual(plan['v2']['recommended_partition'], 'quarantine')
        self.assertFalse(plan['v2']['eligible_for_validation'])
        self.assertEqual(plan['t']['recommended_partition'], 'test')
        self.assertEqual([r['partition'] for r in rows], ['train','train','test','validation','train','train','validation'])


if __name__ == '__main__':
    unittest.main()
