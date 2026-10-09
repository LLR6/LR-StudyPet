import json, tempfile, sys
from pathlib import Path

def run(main,app,output):
 from PySide6.QtCore import Qt
 main.task_title.setText('smoke-test');main.add_task();main.task_list.setCurrentRow(0);main.focus_task();assert main.clock.mode=='focus'
 main.clock.elapsed=61;main.pause_focus();assert main.clock.mode=='paused';main.pause_focus();assert main.clock.mode=='focus';main.end_focus();assert main.store.today_seconds()>=61
 main.clipboard_enabled.setChecked(True);app.clipboard().setText('first');app.processEvents();app.clipboard().setText('second');app.processEvents();assert main.clip_memory.prior()=='first';main.clip_clear();assert not main.clip_memory.prior()
 main.keyboard_enabled.setChecked(True);main.on_keys(2);assert main.key_count==2
 main.open_commands();assert main.command_dialog.isVisible();main.command_dialog.close()
 main.store.set('custom_subjects',['科研','写作']);main.update_subjects();assert main.subject.findText('科研')>=0
 main.minutes.setValue(25);main.restart_small();assert main.clock.duration==300;main.end_focus()
 from study_io import import_cards,export_cards,read_cards,weekly_report
 assert import_cards(main.store,[('多行问题','第一行\n第二行','科研')])==1
 with tempfile.TemporaryDirectory() as folder:
  csv=Path(folder)/'cards.csv';export_cards(main.store,csv);assert read_cards(csv)[0][1]=='第一行\n第二行'
 assert '学习周报' in weekly_report(main.store)
 main.refresh();assert len(main.activity_cells)==28
 pages=[]
 for i in range(main.tabs.count()):
  main.tabs.setCurrentIndex(i);app.processEvents();pages.append(main.tabs.tabText(i))
 main.tabs.setCurrentIndex(0);app.processEvents();main.grab().save(str(Path(output)/'windows-preview.png'))
 result={'status':'passed','platform':sys.platform,'pages':pages,'key_activity_test':'simulated','clipboard':'real Qt clipboard roundtrip','startup':'covered separately by filesystem unit test','global_hotkey_registered':main.hotkey_registered}
 Path(output,'smoke-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 if sys.stdout is not None:print(json.dumps(result,ensure_ascii=True))
 return result
