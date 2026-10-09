import base64
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from PySide6.QtGui import QImage,QColor
from workshop import make_pack,install_pack,load_pack,export_pack,list_packs,validate_metadata
from keyboard_motion import TypingMotion

GIF=base64.b64decode('R0lGODlhIAAgAIEAAIq96QAAAAAAAAAAACH/C05FVFNDQVBFMi4wAwEAAAAh+QQACgAAACwAAAAAIAAgAAAINQABCBxIsKDBgwgTKlzIsKHDhxAjSpxIsaLFixgzatzIsaPHjyBDihxJsqTJkyhTqlzJUmRAACH5BAEKAAEALAAAAAAgACAAgc7q/wAAAAAAAAAAAAg1AAEIHEiwoMGDCBMqXMiwocOHECNKnEixosWLGDNq3Mixo8ePIEOKHEmypMmTKFOqXMlSZEAAOw==')
class WorkshopTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.png=self.root/'source.png';image=QImage(64,64,QImage.Format_ARGB32);image.fill(QColor('#abcdee'));assert image.save(str(self.png))
        self.gif=self.root/'source.gif';self.gif.write_bytes(GIF);self.library=self.root/'pets';self.pack=self.root/'pet.lrpet'
    def tearDown(self):self.temp.cleanup()
    def create(self):return make_pack(self.pack,'自定义宠物','测试作者','原创，仅个人使用',{'idle':self.png,'typing':self.gif},False)
    def test_roundtrip_and_animation_assets(self):
        self.create();ident,data=install_pack(self.pack,self.library);self.assertEqual(load_pack(self.library/ident)['states']['typing'],'typing.gif')
        target=self.root/'export.lrpet';export_pack(self.library/ident,target);ident2,data2=install_pack(target,self.library)
        self.assertEqual(data2['name'],'自定义宠物');self.assertEqual(len(list_packs(self.library)),2)
    def test_single_image_and_missing_state_fallback_contract(self):
        make_pack(self.pack,'宠物','作者','原创',{'idle':self.png});ident,data=install_pack(self.pack,self.library)
        self.assertTrue(data['keyboard_overlay']);self.assertEqual(set(data['states']),{'idle'})
    def test_malicious_paths_and_scripts_are_not_extracted(self):
        self.create()
        with zipfile.ZipFile(self.pack,'a') as pack:pack.writestr('../outside.py','print(1)')
        self.assertRaises(ValueError,install_pack,self.pack,self.library);self.assertFalse((self.root/'outside.py').exists());self.assertEqual(list_packs(self.library),[])
    def test_duplicate_manifest_rejected(self):
        self.create()
        with self.assertWarns(UserWarning):
            with zipfile.ZipFile(self.pack,'a') as pack:pack.writestr('pet.json','{}')
        self.assertRaises(ValueError,install_pack,self.pack,self.library)
    def test_large_image_and_missing_metadata_rejected(self):
        image=QImage(2049,1,QImage.Format_ARGB32);image.fill(QColor('red'));image.save(str(self.png))
        self.assertRaises(ValueError,self.create)
        self.assertRaises(ValueError,validate_metadata,{'schema':1,'name':'','author':'a','license':'a','states':{'idle':'idle.png'}})
    def test_old_pack_not_changed_on_invalid_import(self):
        self.create();ident,data=install_pack(self.pack,self.library)
        with zipfile.ZipFile(self.pack,'w') as pack:pack.writestr('pet.json','{"schema":2}')
        self.assertRaises(ValueError,install_pack,self.pack,self.library);self.assertEqual(load_pack(self.library/ident)['name'],'自定义宠物')

class MotionTests(unittest.TestCase):
    def setUp(self):self.time=[0];self.motion=TypingMotion(now=lambda:self.time[0])
    def test_press_idle_sleep_wake(self):
        self.motion.press();self.assertEqual(self.motion.state(),'typing');self.time[0]=1;self.assertEqual(self.motion.state(),'idle')
        self.time[0]=46;self.assertEqual(self.motion.state(),'sleep');self.motion.press();self.assertEqual(self.motion.state(),'typing')
    def test_focus_does_not_sleep_and_disabled_clears_feedback(self):
        self.motion.press();self.time[0]=100;self.assertEqual(self.motion.state(focused=True),'focus');self.assertEqual(self.motion.state(enabled=False),'idle')
    def test_alternating_taps_and_no_unbounded_queue(self):
        self.motion.press(3);self.assertEqual([s for s,t in self.motion.taps],[1,0,1]);self.time[0]=0.1;self.assertGreater(self.motion.pressure(1),0)
        self.time[0]=10;self.motion.press(1000);self.assertLessEqual(len(self.motion.taps),6)
    def test_lost_keyup_does_not_hold_forever(self):
        self.motion.press();self.motion.held=True;self.time[0]=2;self.assertEqual(self.motion.state(),'idle')
    def test_startup_without_keys_can_sleep(self):
        self.time[0]=46;self.assertEqual(self.motion.state(),'sleep')
