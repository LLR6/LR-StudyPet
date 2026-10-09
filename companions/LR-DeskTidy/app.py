import sys
import copy
from pathlib import Path
from PySide6.QtCore import QThread, Signal, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QApplication,QWidget,QVBoxLayout,QHBoxLayout,QLabel,
    QLineEdit,QPushButton,QFileDialog,QTableWidget,QTableWidgetItem,QTextEdit,QMessageBox)
from tidy import preview,apply,undo,latest_journal

STYLE='''QWidget{background:#f5faff;color:#234764;font-size:14px;font-family:"Microsoft YaHei","Noto Sans CJK SC";}
QLineEdit,QTextEdit,QTableWidget{background:white;border:1px solid #c9e2f3;border-radius:8px;padding:8px;}
QPushButton{background:#d7edff;border:0;border-radius:8px;padding:10px;}QPushButton:hover{background:#b6ddfc;}'''
class Worker(QThread):
    result=Signal(object);error=Signal(str)
    def __init__(self,fn):super().__init__();self.fn=fn
    def run(self):
        try:self.result.emit(self.fn())
        except Exception as e:self.error.emit(str(e))

def button(text,fn):
    b=QPushButton(text);b.clicked.connect(fn);return b

class Main(QWidget):
    def __init__(self):
        super().__init__();self.setWindowTitle('LR DeskTidy · 先看计划，再整理，可撤销');self.resize(1000,700)
        self.plan=None;self.worker=None
        v=QVBoxLayout(self);title=QLabel('桌面太乱？先看每个文件会去哪。');title.setStyleSheet('font-size:25px;font-weight:bold');v.addWidget(title)
        v.addWidget(QLabel('只处理一层文档、图片、压缩包和媒体文件；不删除重复内容，不处理快捷方式或程序。'))
        row=QHBoxLayout();self.root=QLineEdit(str(Path.home()/'Desktop'));row.addWidget(self.root);self.choose_btn=button('选择目录',self.choose);row.addWidget(self.choose_btn);v.addLayout(row)
        row=QHBoxLayout();self.scan_btn=button('① 生成预览',self.scan);self.apply_btn=button('② 整理勾选文件',self.organize);self.undo_btn=button('撤销最近一次',self.revert)
        for b in (self.scan_btn,self.apply_btn,self.undo_btn):row.addWidget(b)
        row.addWidget(button('打开目录',self.open_folder));v.addLayout(row)
        self.table=QTableWidget(0,4);self.table.setHorizontalHeaderLabels(['整理','原文件','目标位置','内容重复提示']);self.table.horizontalHeader().setStretchLastSection(True);self.table.setColumnWidth(1,300);self.table.setColumnWidth(2,350);v.addWidget(self.table)
        self.output=QTextEdit();self.output.setReadOnly(True);self.output.setMaximumHeight(160);v.addWidget(self.output)
        self.output.setPlainText('选择目录并生成预览。单文件上限 128 MB；一次最多 500 文件。历史保存在所选目录的 .lr-desktidy 中。')
        self.apply_btn.setEnabled(False)
    def choose(self):
        root=QFileDialog.getExistingDirectory(self,'选择要整理的目录',self.root.text())
        if root:self.root.setText(root);self.plan=None;self.table.setRowCount(0);self.apply_btn.setEnabled(False)
    def busy(self,value):
        for widget in (self.scan_btn,self.undo_btn,self.choose_btn,self.root,self.table):widget.setEnabled(not value)
        self.apply_btn.setEnabled(not value and self.plan is not None)
    def run_job(self,fn,result):
        if self.worker and self.worker.isRunning():return
        self.busy(True);self.output.setPlainText('正在处理… 大文件校验需要一点时间。')
        self.worker=Worker(fn);self.worker.result.connect(result);self.worker.error.connect(lambda text:self.output.setPlainText(text));self.worker.finished.connect(lambda:self.busy(False));self.worker.start()
    def scan(self):
        root=self.root.text();self.plan=None;self.table.setRowCount(0)
        self.run_job(lambda:preview(root),self.show_plan)
    def show_plan(self,plan):
        self.plan=plan;self.table.setRowCount(len(plan['items']))
        for i,row in enumerate(plan['items']):
            check=QTableWidgetItem();check.setFlags(Qt.ItemIsEnabled|Qt.ItemIsUserCheckable);check.setCheckState(Qt.Checked);self.table.setItem(i,0,check)
            for j,text in enumerate([row['source'],row['destination'],'内容相同，均保留' if row['same_content'] else ''],1):
                item=QTableWidgetItem(text);item.setFlags(Qt.ItemIsEnabled|Qt.ItemIsSelectable);self.table.setItem(i,j,item)
        self.output.setPlainText(f'可整理 {len(plan["items"])} 个文件。取消不想整理的勾选。\n'+'\n'.join(plan['skipped']))
    def organize(self):
        if not self.plan:return
        if str(Path(self.root.text()).resolve())!=self.plan['root']:
            self.output.setPlainText('目录已变化，请重新生成预览。');return
        selected=copy.deepcopy(self.plan);selected['items']=[r for i,r in enumerate(self.plan['items']) if self.table.item(i,0).checkState()==Qt.Checked]
        if not selected['items']:return
        if QMessageBox.question(self,'确认计划',f'把 {len(selected["items"])} 个文件移动到当前目录的分类文件夹？\n保留移动历史，已有目标文件不会覆盖。')!=QMessageBox.Yes:return
        self.plan=None;self.run_job(lambda:apply(selected),lambda journal:self.output.setPlainText('整理完成。可撤销最近一次。\n历史：'+str(journal)))
    def revert(self):
        root=self.root.text()
        if QMessageBox.question(self,'撤销','恢复最近一次尚未撤销的整理？原位置已占用或文件已修改的项目将跳过。')!=QMessageBox.Yes:return
        def job():
            journal=latest_journal(root)
            return undo(journal) if journal else ['没有可撤销的记录。']
        self.plan=None;self.run_job(job,lambda result:self.output.setPlainText('\n'.join(result) or '已检查历史。'))
    def open_folder(self):
        path=Path(self.root.text())
        if path.is_dir():QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.resolve())))
    def closeEvent(self,event):
        if self.worker and self.worker.isRunning():event.ignore();self.output.append('任务正在进行，完成后再退出。')
        else:event.accept()

if __name__=='__main__':
    app=QApplication(sys.argv);app.setStyleSheet(STYLE);main=Main();main.show()
    if '--smoke-test' in sys.argv:
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            Path(folder,'demo.pdf').write_text('demo');Path(folder,'image.png').write_bytes(b'demo image')
            main.root.setText(folder);plan=preview(folder);main.show_plan(plan);app.processEvents();main.grab().save('preview.png');assert main.table.rowCount()==2
            journal=apply(plan);assert len(undo(journal))==2;main.close()
        print('DeskTidy GUI smoke passed')
    else:sys.exit(app.exec())
