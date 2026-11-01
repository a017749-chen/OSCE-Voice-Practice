"""Offline tests of the publicly distributed case validator and exporter."""
from pathlib import Path
import copy
import importlib.util
import json
import tempfile
import unittest
import zipfile

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / '.agents/skills/osce-practice-coordinator/scripts/package_case.py'
spec = importlib.util.spec_from_file_location('osce_packer', SCRIPT)
packer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packer)
rules = yaml.safe_load((ROOT / 'rules.practice.yaml').read_text(encoding='utf-8'))
cases = {name: json.loads((ROOT / 'examples' / name / 'case.json').read_text(encoding='utf-8'))
         for name in ('HX-001', 'COM-001', 'EXP-001')}


class PublicPackageTests(unittest.TestCase):
    def test_all_examples_pass_practice_rules(self):
        self.assertEqual(
            {case['station_type'] for case in cases.values()},
            {'history', 'communication', 'explanation'},
        )
        for case in cases.values():
            packer.validate_case(case, rules)

    def test_cases_are_fictional_and_scores_match(self):
        for case in cases.values():
            self.assertTrue(case['fictional'])
            self.assertEqual(case['rubric']['max_score'], 2 * len(case['rubric']['items']))

    def test_wrong_total_is_rejected(self):
        case = copy.deepcopy(cases['HX-001'])
        case['rubric']['max_score'] = 29
        with self.assertRaises(ValueError):
            packer.validate_case(case, rules)

    def test_missing_fact_is_rejected(self):
        case = copy.deepcopy(cases['HX-001'])
        case['rubric']['items'][0]['fact_ids'] = ['MISSING']
        with self.assertRaises(ValueError):
            packer.validate_case(case, rules)

    def test_duplicate_fact_is_rejected(self):
        case = copy.deepcopy(cases['HX-001'])
        case['facts'][1]['id'] = case['facts'][0]['id']
        with self.assertRaises(ValueError):
            packer.validate_case(case, rules)

    def test_unmarked_prompt_cap_is_rejected(self):
        case = copy.deepcopy(cases['COM-001'])
        next(i for i in case['rubric']['items'] if i['id'] == 'C07')['sp_prompted'] = False
        with self.assertRaises(ValueError):
            packer.validate_case(case, rules)

    def test_missing_teachback_is_rejected(self):
        for name in ('COM-001', 'EXP-001'):
            case = copy.deepcopy(cases[name])
            case['sp']['dialogue'] = [d for d in case['sp']['dialogue'] if 'Teach-back' not in d['frame']]
            with self.assertRaises(ValueError):
                packer.validate_case(case, rules)

    def test_non_history_rejects_lqqopera_marker(self):
        for name in ('COM-001', 'EXP-001'):
            case = copy.deepcopy(cases[name])
            case['rubric']['items'][1]['lqqopera'] = True
            with self.assertRaises(ValueError):
                packer.validate_case(case, rules)

    def test_committed_exports_stay_synced_with_case_json(self):
        for name in cases:
            source = ROOT / 'examples' / name / 'case.json'
            with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
                output = Path(tmp) / 'output'
                packer.export_case(source, ROOT / 'rules.practice.yaml', output)
                for exported, committed in (
                    ('考生指引.md', 'candidate.md'),
                    ('語音演練包.txt', 'voice-packet.txt'),
                    ('教案內容.yaml', 'lesson.yaml'),
                ):
                    self.assertEqual(
                        (output / exported).read_text(encoding='utf-8'),
                        (ROOT / 'examples' / name / committed).read_text(encoding='utf-8'),
                        msg=f'{name}/{committed} is out of sync with case.json',
                    )

    def test_export_embeds_the_case_and_refuses_to_overwrite(self):
        source = ROOT / 'examples/HX-001/case.json'
        before = source.read_bytes()
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            output = Path(tmp) / 'output'
            packer.export_case(source, ROOT / 'rules.practice.yaml', output)
            packet = (output / '語音演練包.txt').read_text(encoding='utf-8')
            payload = packet.split('【病例資料 JSON 僅依規則使用，結束前不要完整朗讀】\n', 1)[1]
            self.assertEqual(json.loads(payload), cases['HX-001'])
            with self.assertRaises(FileExistsError):
                packer.export_case(source, ROOT / 'rules.practice.yaml', output)
        self.assertEqual(source.read_bytes(), before)

    def test_public_word_is_valid_and_has_no_company_metadata(self):
        for case in cases:
            with zipfile.ZipFile(ROOT / 'examples' / case / 'lesson.docx') as word:
                self.assertIsNone(word.testzip())
                core = word.read('docProps/core.xml').decode('utf-8')
                app = word.read('docProps/app.xml').decode('utf-8')
                self.assertNotIn('lastModifiedBy', core)
                self.assertNotIn('Company', app)


if __name__ == '__main__':
    unittest.main()
