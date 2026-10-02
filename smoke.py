import json, tempfile, sys
from pathlib import Path

def run(main,app,output):
 from PySide6.QtCore import Qt
 main.task_title.setText('smoke-test');main.add_task();main.task_list.setCurrentRow(0);main.focus_task();assert main.clock.mode=='focus'
 main.clock.elapsed=61;main.pause_focus();assert main.clock.mode=='paused';main.pause_focus();assert main.clock.mode=='focus';main.end_focus();assert main.store.today_seconds()>=61
 main.clipboard_enabled.setChecked(True);app.clipboard().setText('first');app.processEvents();app.clipboard().setText('second');app.processEvents();assert main.clip_memory.prior()=='first';main.clip_clear();assert not main.clip_memory.prior()
 main.keyboard_enabled.setChecked(True);main.on_keys(2);assert main.key_count==2
 main.open_commands();assert main.command_dialog.isVisible();main.command_dialog.close()
 pages=[]
 for i in range(main.tabs.count()):
  main.tabs.setCurrentIndex(i);app.processEvents();pages.append(main.tabs.tabText(i))
 main.tabs.setCurrentIndex(0);app.processEvents();main.grab().save(str(Path(output)/'windows-preview.png'))
 result={'status':'passed','platform':sys.platform,'pages':pages,'key_activity_test':'simulated','clipboard':'real Qt clipboard roundtrip','startup':'covered separately by filesystem unit test','global_hotkey_registered':main.hotkey_registered}
 Path(output,'smoke-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 if sys.stdout is not None:print(json.dumps(result,ensure_ascii=True))
 return result
