import tempfile, unittest, sys
from pathlib import Path
from unittest.mock import patch
from desktop_tools import ClipboardMemory, desktop_advice, suggest_commands, configure_startup
class DesktopTests(unittest.TestCase):
 def test_previous_expires_after_60_seconds(self):
  n=[0];m=ClipboardMemory(now=lambda:n[0]);m.observe('a');n[0]=1;m.observe('b');self.assertEqual(m.prior(),'a');n[0]=60;self.assertEqual(m.prior(),'a');n[0]=61;self.assertEqual(m.prior(),'')
 def test_expired_current_is_not_remembered_again(self):
  n=[0];m=ClipboardMemory(now=lambda:n[0]);m.observe('a');n[0]=61;m.observe('b');self.assertEqual(m.prior(),'')
 def test_duplicate_does_not_extend_ttl(self):
  n=[0];m=ClipboardMemory(now=lambda:n[0]);m.observe('a');n[0]=1;m.observe('b');n[0]=50;m.observe('b');n[0]=61;self.assertEqual(m.prior(),'')
 def test_clear(self):
  m=ClipboardMemory();m.observe('a');m.observe('b');m.clear();self.assertFalse(m.prior());self.assertIsNone(m.current)
 def test_clipboard_size_bound(self):
  m=ClipboardMemory();m.observe('x'*10001);self.assertIsNone(m.current)
 def test_desktop_analysis_never_modifies_files(self):
  with tempfile.TemporaryDirectory() as d:
   for n in ['a.pdf','b.pdf','c.pdf','photo.png']:Path(d,n).write_text('x')
   before={p.name:p.read_bytes() for p in Path(d).iterdir()};s=desktop_advice(d);self.assertIn('文档',s);self.assertEqual(before,{p.name:p.read_bytes() for p in Path(d).iterdir()})
 def test_commands_match_chinese_and_prefix(self):
  self.assertTrue(suggest_commands('查看端口'));self.assertTrue(suggest_commands('git'));self.assertFalse(suggest_commands('this-does-not-exist'));self.assertTrue(all(r[0]=='Docker' for r in suggest_commands('', 'Docker')))
 def test_startup_quotes_and_disable(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)/'space folder';root.mkdir();(root/'bootstrap.py').write_text('');exe=root/'python.exe';exe.touch();file=Path(d)/'startup.vbs'
   with patch('desktop_tools.sys.platform','win32'),patch('desktop_tools.startup_file',return_value=file):
    configure_startup(True,root,exe);self.assertIn('""',file.read_text(encoding='utf-16'));self.assertIn('--tray',file.read_text(encoding='utf-16'));configure_startup(False,root,exe);self.assertFalse(file.exists())
if __name__=='__main__':unittest.main()
