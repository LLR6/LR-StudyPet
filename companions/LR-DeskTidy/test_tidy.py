import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tidy import preview,apply,undo,latest_journal,move_no_clobber

class TidyTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def write(self,name,content='hello'):
        path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(content);return path
    def test_preview_does_not_move_or_delete_duplicates(self):
        self.write('a.pdf');self.write('b.pdf');self.write('app.exe')
        plan=preview(self.root);self.assertEqual(len(plan['items']),2);self.assertTrue(plan['items'][0]['same_content'])
        self.assertTrue((self.root/'a.pdf').exists());self.assertFalse((self.root/'Documents').exists())
    def test_move_and_undo_roundtrip(self):
        self.write('a.pdf');journal=apply(preview(self.root));self.assertFalse((self.root/'a.pdf').exists())
        self.assertEqual(latest_journal(self.root),journal);self.assertIn('已恢复',undo(journal)[0]);self.assertEqual((self.root/'a.pdf').read_text(),'hello');self.assertIsNone(latest_journal(self.root))
    def test_collision_and_changed_target_are_preserved(self):
        self.write('a.pdf');self.write('Documents/a.pdf','old');plan=preview(self.root)
        self.assertEqual(plan['items'][0]['destination'],'Documents/a (1).pdf')
        journal=apply(plan);self.write('a.pdf','new')
        self.assertIn('跳过',undo(journal)[0]);self.assertEqual((self.root/'a.pdf').read_text(),'new');self.assertEqual((self.root/'Documents/a.pdf').read_text(),'old')
    def test_changed_file_stops_before_any_move(self):
        self.write('a.pdf');self.write('b.pdf');plan=preview(self.root);self.write('b.pdf','changed')
        self.assertRaises(ValueError,apply,plan);self.assertTrue((self.root/'a.pdf').exists())
    def test_modified_destination_not_moved_back(self):
        self.write('a.pdf');journal=apply(preview(self.root));self.write('Documents/a.pdf','changed')
        self.assertIn('已修改',undo(journal)[0]);self.assertFalse((self.root/'a.pdf').exists())
    def test_partial_failure_has_recoverable_journal(self):
        self.write('a.pdf');self.write('b.pdf');real=move_no_clobber;calls=[]
        def stop(source,destination):
            calls.append(source)
            if len(calls)==2:raise OSError('simulated failure')
            real(source,destination)
        with patch('tidy.move_no_clobber',stop):self.assertRaises(RuntimeError,apply,preview(self.root))
        journal=latest_journal(self.root);undo(journal)
        self.assertTrue((self.root/'a.pdf').exists());self.assertTrue((self.root/'b.pdf').exists())
    def test_path_escape_and_symlink_rejected(self):
        self.write('a.pdf');plan=preview(self.root);plan['items'][0]['destination']='../outside.pdf'
        self.assertRaises(ValueError,apply,plan)
        try:(self.root/'Documents').symlink_to(self.root,target_is_directory=True)
        except OSError:self.skipTest('symlink privilege unavailable')
        self.assertRaises(ValueError,apply,preview(self.root))
    def test_no_clobber(self):
        a=self.write('a.pdf','a');b=self.write('b.pdf','b');self.assertRaises(FileExistsError,move_no_clobber,a,b)
        self.assertEqual(a.read_text(),'a');self.assertEqual(b.read_text(),'b')
    def test_pending_move_after_crash_can_undo(self):
        self.write('a.pdf');journal=apply(preview(self.root));data=json.loads(journal.read_text());data['operations'][0]['status']='pending';journal.write_text(json.dumps(data))
        undo(journal);self.assertTrue((self.root/'a.pdf').exists())
