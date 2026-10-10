import copy
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from registry import RegistryError, get_source, load_registry, validate_registry


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.data = load_registry()

    def test_all_atlas_rows_present(self):
        self.assertEqual(21, len(self.data['sources']))
        self.assertEqual(set(range(1, 22)), {s['atlas']['row'] for s in self.data['sources']})
        self.assertEqual(64, len(self.data['document']['sha256']))

    def test_no_platform_defaults_or_live_connectors(self):
        for source in self.data['sources']:
            self.assertFalse(source['data_access']['enabled'])
            self.assertFalse(source['data_access']['automated_access_authorized'])
            self.assertIsNone(source['platform_conditions']['buyer_premium']['calculation_default'])
            self.assertIsNone(source['platform_conditions']['vat']['calculation_default'])

    def test_justiz_contradiction_explicit(self):
        self.assertEqual('contradictory', get_source('justiz-auktion')['platform_conditions']['vat']['status'])

    def test_unknown_source(self):
        self.assertIsNone(get_source('not-a-platform'))

    def test_independent_loads(self):
        source = get_source('vebeg')
        source['name'] = 'changed'
        self.assertNotEqual('changed', get_source('vebeg')['name'])

    def test_reject_duplicate_source(self):
        self.data['sources'].append(copy.deepcopy(self.data['sources'][0]))
        with self.assertRaises(RegistryError):
            validate_registry(self.data)

    def test_reject_invalid_schema(self):
        for schema in (True, 2, '1', None):
            data = copy.deepcopy(self.data)
            data['schema_version'] = schema
            with self.assertRaises(RegistryError):
                validate_registry(data)

    def test_reject_implicit_api_permission(self):
        source = self.data['sources'][10]
        source['data_access'].update(enabled=True, automated_access_authorized=True, connector='api')
        with self.assertRaises(RegistryError):
            validate_registry(self.data)

    def test_reject_economic_defaults(self):
        for field in ('vat', 'buyer_premium'):
            data = copy.deepcopy(self.data)
            data['sources'][0]['platform_conditions'][field]['calculation_default'] = 0
            with self.assertRaises(RegistryError):
                validate_registry(data)

    def test_reject_unknown_status_and_evidence(self):
        for change in ('status', 'reference'):
            data = copy.deepcopy(self.data)
            if change == 'status':
                data['sources'][0]['evidence'][0]['status'] = 'approved'
            else:
                data['sources'][0]['platform_conditions']['buyer_premium']['evidence_ids'] = ['invented']
            with self.assertRaises(RegistryError):
                validate_registry(data)

    def test_reject_insecure_url_and_date(self):
        for field, value in (('official_website', 'https://secret:password@example.com'),
                             ('official_website', 'http://example.com'), ('updated_at', '2026-13-01')):
            data = copy.deepcopy(self.data)
            data['sources'][0][field] = value
            with self.assertRaises(RegistryError):
                validate_registry(data)

    def test_malformed_file_and_duplicate_properties(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'register.json'
            for text in ('broken', '{"schema_version":1,"schema_version":1}', '{"value":NaN}'):
                path.write_text(text)
                with self.assertRaises(RegistryError):
                    load_registry(path)

    def test_missing_file_controlled(self):
        with self.assertRaises(RegistryError):
            load_registry('/file/that/does/not/exist')

    def test_missing_required_data(self):
        del self.data['sources'][0]['data_access']
        with self.assertRaises(RegistryError):
            validate_registry(self.data)

    def test_bad_access_flag(self):
        self.data['sources'][0]['data_access']['enabled'] = 'false'
        with self.assertRaises(RegistryError):
            validate_registry(self.data)
