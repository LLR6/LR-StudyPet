import unittest, tempfile, json
from pathlib import Path
from core import Store, FocusClock, day
class Tests(unittest.TestCase):
 def setUp(self):self.temp=tempfile.TemporaryDirectory();self.store=Store(Path(self.temp.name)/'db.sqlite')
 def tearDown(self):self.store.db.close();self.temp.cleanup()
 def test_pause_is_not_focus(self):
  n=[0];c=FocusClock(lambda:n[0]);c.start(1);n[0]=20;c.pause();n[0]=200;self.assertEqual(c.tick(),40);c.resume();n[0]=215;self.assertEqual(c.tick(),25)
 def test_focus_complete_and_no_negative(self):
  n=[0];c=FocusClock(lambda:n[0]);c.start(1);n[0]=100;self.assertEqual(c.tick(),0)
 def test_review_reschedule(self):
  self.store.review('q','a','408');r=self.store.rows('reviews')[0];self.store.grade(r['id'],2);r=self.store.rows('reviews')[0];self.assertEqual(r['interval'],4);self.assertGreater(r['due'],day())
 def test_undo_task_xp(self):
  self.store.task('t','408',25);i=self.store.rows('tasks')[0]['id'];self.store.done(i);self.assertEqual(self.store.xp(),10);self.store.done(i);self.assertEqual(self.store.xp(),0)
 def test_backup_roundtrip(self):
  self.store.task('PV','408',25);self.store.session('408',120,'next');self.store.review('P?','wait','408');self.store.journal('错因','信号量');p=Path(self.temp.name)/'b.json';self.store.export(p);self.store.restore(p);self.assertEqual(len(self.store.rows('sessions')),1);self.assertEqual(self.store.today_seconds(),120)
 def test_invalid_backup_preserves_data(self):
  self.store.task('keep','英语',10);p=Path(self.temp.name)/'b.json';self.store.export(p);d=json.loads(p.read_text());d['reviews']=[{'oops':1}];p.write_text(json.dumps(d));self.assertRaises(ValueError,self.store.restore,p);self.assertEqual(self.store.rows('tasks')[0]['title'],'keep')
 def test_small_task_low_energy(self):
  self.store.task('大任务','数学',50);self.store.task('小任务','英语',5);self.assertIn('小任务',self.store.recommend('低'))
if __name__=='__main__':unittest.main()
