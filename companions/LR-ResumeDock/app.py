"""An offline interruption bookmark with a small always-on-top restart dock."""
import os
import sys
import time
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QApplication, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QLineEdit, QTextEdit, QListWidget, QListWidgetItem, QPushButton, QCheckBox,
    QMessageBox, QFileDialog)
from resume_store import DockStore

STYLE = '''QWidget{background:#f5faff;color:#234764;font-size:14px;font-family:"Microsoft YaHei","Noto Sans CJK SC";}
QLineEdit,QTextEdit,QListWidget{background:white;border:1px solid #c9e2f3;border-radius:8px;padding:8px;}
QPushButton{background:#d7edff;border:0;border-radius:8px;padding:10px;}QPushButton:hover{background:#b6ddfc;}
QListWidget::item{padding:10px;}'''

def button(text, fn):
    widget = QPushButton(text); widget.clicked.connect(fn); return widget

class RestartDock(QWidget):
    def __init__(self, main):
        super().__init__(); self.main = main
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setWindowTitle('ResumeDock · 下一小步'); self.resize(350,240)
        layout = QVBoxLayout(self)
        self.step = QLabel(''); self.step.setWordWrap(True); self.step.setTextFormat(Qt.PlainText)
        self.clock = QLabel('05:00'); self.clock.setAlignment(Qt.AlignCenter)
        self.clock.setStyleSheet('font-size:36px;color:#397cad')
        layout.addWidget(self.step); layout.addWidget(self.clock)
        row = QHBoxLayout(); row.addWidget(button('开始 / 暂停',main.toggle_timer)); row.addWidget(button('结束保存',main.end_timer)); layout.addLayout(row)
        layout.addWidget(button('返回书签',lambda:main.showNormal()))
        self.timer = QTimer(self); self.timer.timeout.connect(main.tick); self.timer.start(250)

class Main(QWidget):
    def __init__(self, path=None):
        super().__init__(); self.setWindowTitle('LR ResumeDock · 离开时留一句，回来接着做'); self.resize(930,650)
        data = Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'.local/share'))) / 'LR-ResumeDock'
        self.store = DockStore(path or data/'resume.sqlite3')
        self.ident = None; self.session_id = None; self.elapsed = 0; self.anchor = None
        self.dock = RestartDock(self)
        self.autosave = QTimer(self); self.autosave.setSingleShot(True); self.autosave.timeout.connect(self.save_auto)
        outer = QHBoxLayout(self); left = QVBoxLayout(); right = QVBoxLayout(); outer.addLayout(left,1); outer.addLayout(right,2)
        heading = QLabel('把“刚才做到哪”留给回来后的自己。'); heading.setWordWrap(True); left.addWidget(heading)
        self.archived = QCheckBox('查看已归档'); self.archived.toggled.connect(self.refresh); left.addWidget(self.archived)
        self.items = QListWidget(); self.items.currentItemChanged.connect(self.select); left.addWidget(self.items)
        left.addWidget(button('新建书签',self.new)); left.addWidget(button('归档 / 恢复',self.archive))
        left.addWidget(button('导出 Markdown',self.export))
        self.title = QLineEdit(); self.title.setPlaceholderText('项目 / 学习任务')
        self.context = QTextEdit(); self.context.setPlaceholderText('已做到哪？最后一个确定正确的结果是什么？')
        self.next_step = QTextEdit(); self.next_step.setPlaceholderText('回来后的第一步：具体到一个动作，例如“运行第二个失败测试”')
        self.resource = QLineEdit(); self.resource.setPlaceholderText('可选：本地文件路径或 https:// 资料地址')
        for text, widget in [('任务',self.title),('已做到这里',self.context),('回来只做这一小步',self.next_step),('资料入口',self.resource)]:
            right.addWidget(QLabel(text)); right.addWidget(widget)
        row = QHBoxLayout(); row.addWidget(button('保存书签',self.save)); row.addWidget(button('选择文件',self.choose_file)); row.addWidget(button('打开资料',self.open_resource)); right.addLayout(row)
        right.addWidget(button('打开 5 分钟续接浮窗',self.open_dock))
        self.status = QLabel('已有书签编辑后自动保存；新书签请先点保存。'); self.status.setWordWrap(True); right.addWidget(self.status)
        for widget in (self.title,self.context,self.next_step,self.resource): widget.textChanged.connect(self.schedule_save)
        self.refresh()
    def schedule_save(self):
        if self.ident is not None:self.autosave.start(500)
    def save_auto(self):
        try:self._save();self.status.setText('已自动保存到本机。')
        except ValueError as e:self.status.setText(str(e))
    def _save(self):
        self.ident = self.store.save(self.ident,self.title.text(),self.context.toPlainText(),self.next_step.toPlainText(),self.resource.text())
    def save(self):
        try:self.autosave.stop();self._save();self.refresh();self.status.setText('已保存，回来时从下一步开始。')
        except ValueError as e:QMessageBox.warning(self,'书签',str(e))
    def refresh(self):
        selected=self.ident;self.items.blockSignals(True);self.items.clear()
        for row in self.store.rows(self.archived.isChecked()):
            item=QListWidgetItem(row['title']);item.setData(Qt.UserRole,row);self.items.addItem(item)
            if row['id']==selected:self.items.setCurrentItem(item)
        self.items.blockSignals(False)
    def flush(self):
        if self.autosave.isActive() or (self.ident is None and any((self.title.text(),self.context.toPlainText(),self.next_step.toPlainText(),self.resource.text()))):
            self.autosave.stop()
            try:self._save()
            except ValueError:return False
        return True
    def select(self,current,previous):
        if not current:return
        if not self.flush():
            self.items.blockSignals(True);self.items.setCurrentItem(previous);self.items.blockSignals(False)
            self.status.setText('先补全任务名和下一步，或点击新建放弃当前编辑。');return
        ident=current.data(Qt.UserRole)['id'];row=dict(self.store.db.execute('SELECT * FROM bookmarks WHERE id=?',(ident,)).fetchone());self.ident=row['id']
        for widget,value in [(self.title,row['title']),(self.context,row['context']),(self.next_step,row['next_step']),(self.resource,row['resource'])]:
            widget.blockSignals(True)
            if isinstance(widget,QTextEdit):widget.setPlainText(value)
            else:widget.setText(value)
            widget.blockSignals(False)
        self.status.setText('编辑会自动保存到本机；当前浮窗保留打开时的下一步。')
    def new(self):
        if not self.flush() and QMessageBox.question(self,'未保存编辑','当前编辑不完整，放弃这些编辑？')!=QMessageBox.Yes:return
        self.ident=None;self.items.clearSelection()
        for widget in (self.title,self.context,self.next_step,self.resource):widget.clear()
        self.title.setFocus();self.status.setText('新建：填写任务名和下一步后点保存。')
    def archive(self):
        if self.ident is None:return
        if self.session_id==self.ident and (self.anchor is not None or self.elapsed>0):
            QMessageBox.information(self,'计时中','先结束当前计时再归档。');return
        if not self.flush():return
        self.store.archive(self.ident,not self.archived.isChecked());self.new();self.refresh()
    def choose_file(self):
        path,_=QFileDialog.getOpenFileName(self,'选择资料文件')
        if path:self.resource.setText(path)
    def open_resource(self):
        text=self.resource.text().strip()
        if text.startswith('https://'):QDesktopServices.openUrl(QUrl(text));return
        path=Path(text).expanduser()
        if text and path.exists():QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.resolve())))
        else:QMessageBox.information(self,'资料','填写有效的本地路径或 HTTPS 地址。')
    def open_dock(self):
        if self.anchor is not None or self.elapsed>0:
            self.dock.show();return
        try:self._save();self.refresh()
        except ValueError as e:QMessageBox.warning(self,'书签',str(e));return
        self.session_id=self.ident;self.dock.step.setText(self.title.text()+'\n\n下一步：'+self.next_step.toPlainText());self.dock.show()
    def toggle_timer(self):
        if self.session_id is None:return
        if self.anchor is None:self.anchor=time.monotonic()
        else:self.elapsed+=time.monotonic()-self.anchor;self.anchor=None
        self.tick()
    def tick(self):
        elapsed=self.elapsed+(time.monotonic()-self.anchor if self.anchor is not None else 0)
        remaining=max(0,300-int(elapsed));self.dock.clock.setText(f'{remaining//60:02d}:{remaining%60:02d}')
        if elapsed>=300:
            self.elapsed=300;self.anchor=None;self.end_timer();self.status.setText('完成了 5 分钟续接。接下来由你决定。')
    def end_timer(self):
        if self.anchor is not None:self.elapsed+=time.monotonic()-self.anchor
        self.anchor=None
        if self.session_id is not None:self.store.record(self.session_id,min(self.elapsed,300))
        self.elapsed=0;self.session_id=None;self.dock.hide();self.dock.clock.setText('05:00')
    def export(self):
        if not self.flush():return
        path,_=QFileDialog.getSaveFileName(self,'导出书签','ResumeDock.md','Markdown (*.md)')
        if path:
            try:Path(path).write_text(self.store.report(),encoding='utf-8');self.status.setText('已导出。分享前检查书签内容。')
            except OSError as e:QMessageBox.warning(self,'导出失败',str(e))
    def closeEvent(self,event):
        if not self.flush():
            event.ignore();QMessageBox.warning(self,'未保存','补全任务名和下一步后再退出。');return
        self.end_timer();self.dock.close();self.store.db.close();event.accept()

if __name__=='__main__':
    app=QApplication(sys.argv);app.setStyleSheet(STYLE)
    if '--smoke-test' in sys.argv:
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            main=Main(Path(folder)/'dock.sqlite3');main.show();main.title.setText('文档写作');main.context.setPlainText('第一张图已完成，下一段解释实验结果。');main.next_step.setPlainText('补完第一张图的说明');main.save();main.open_dock();main.toggle_timer();main.elapsed=60;main.end_timer();app.processEvents();main.grab().save('preview.png');assert len(main.store.rows())==1;main.close()
        print('ResumeDock GUI smoke passed')
    else:
        main=Main();main.show();sys.exit(app.exec())
