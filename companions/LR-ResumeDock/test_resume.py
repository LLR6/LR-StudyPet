import tempfile
import unittest
from pathlib import Path
from resume_store import DockStore
class ResumeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'db.sqlite3';self.store=DockStore(self.path)
    def tearDown(self):self.store.db.close();self.temp.cleanup()
    def test_save_update_persist(self):
        ident=self.store.save(None,'写作','图1完成','补图2')
        self.store.save(ident,'写作','图2完成','补图3');other=DockStore(self.path)
        self.assertEqual(other.rows()[0]['next_step'],'补图3');other.db.close()
    def test_archive_restore_keeps_history(self):
        ident=self.store.save(None,'学习','','写第一步');self.store.record(ident,90);self.store.archive(ident)
        self.assertEqual(self.store.rows(),[]);self.store.archive(ident,False)
        self.assertIn('1 分钟',self.store.report())
    def test_invalid_update_keeps_original(self):
        ident=self.store.save(None,'学习','','写第一步')
        self.assertRaises(ValueError,self.store.save,ident,'学习','','')
        self.assertEqual(self.store.rows()[0]['next_step'],'写第一步')
