import csv
import datetime as dt
import tempfile
import unittest
from pathlib import Path
from core import Store
from study_io import read_cards, import_cards, export_cards, activity_days, weekly_report

class IOTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.store=Store(self.root/'db.sqlite3')
    def tearDown(self):self.store.db.close();self.temp.cleanup()
    def test_csv_roundtrip_multiline_unicode(self):
        self.store.review('a,题','第一行\n第二行','自定义');p=self.root/'cards.csv';export_cards(self.store,p)
        self.assertEqual(read_cards(p),[('a,题','第一行\n第二行','自定义')]);self.assertEqual(import_cards(self.store,read_cards(p)),0)
    def test_csv_validation_prevents_partial_import(self):
        p=self.root/'bad.csv';p.write_text('question,answer\nvalid,yes\ninvalid,\n',encoding='utf-8')
        self.assertRaises(ValueError,read_cards,p);self.assertEqual(self.store.rows('reviews'),[])
    def test_duplicate_import_preserves_schedule(self):
        cards=[('q','a','math')]*2;self.assertEqual(import_cards(self.store,cards),1)
        row=self.store.rows('reviews')[0];self.store.grade(row['id'],2)
        due=self.store.rows('reviews')[0]['due'];self.assertEqual(import_cards(self.store,cards),0)
        self.assertEqual(self.store.rows('reviews')[0]['due'],due)
    def test_week_aggregates_by_seconds_and_includes_all_subjects(self):
        self.store.session('科研',65,'');self.store.session('科研',65,'')
        self.store.journal('收获','一行\n二行')
        self.assertIn('科研: 2 分钟',weekly_report(self.store));self.assertIn('> 二行',weekly_report(self.store))
        self.assertEqual(activity_days(self.store)[-1][1],130)
    def test_empty_report_has_seven_days(self):
        today=dt.date(2026,10,9);self.assertEqual(activity_days(self.store,7,today)[0][0],'2026-10-03')
        self.assertIn('暂无专注记录',weekly_report(self.store,today))
