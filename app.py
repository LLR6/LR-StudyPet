import os, sys, math, random, json, datetime, urllib.request, wave, struct
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QPoint, QUrl, QDate, QDateTime, QEvent
from PySide6.QtGui import QPainter, QColor, QPixmap, QIcon, QAction, QFont, QDesktopServices
from PySide6.QtWidgets import *

from core import Store, FocusClock, day
from study_io import read_cards, import_cards, export_cards, activity_days, weekly_report
from desktop_tools import ClipboardMemory, KeyboardActivity, desktop_path, desktop_advice, suggest_commands, configure_startup, startup_file

ROOT=Path(__file__).resolve().parent
DATA=Path(os.environ.get('LOCALAPPDATA', str(Path.home()/'.local/share')))/'LR-StudyPet'
def error_hook(kind,value,tb):
    import traceback
    DATA.mkdir(parents=True,exist_ok=True)
    with (DATA/'startup.log').open('a',encoding='utf-8') as f:traceback.print_exception(kind,value,tb,file=f)
    if sys.platform=='win32' and '--smoke-test' not in sys.argv:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None,'星梨发生错误。日志：'+str(DATA/'startup.log')+'\n'+str(value),'LR StudyPet',0x10)
    else:sys.__excepthook__(kind,value,tb)
sys.excepthook=error_hook
SUBJECTS=['数学','英语','政治','408','其他']
STYLE='''
QWidget {font-family:"Microsoft YaHei", "Noto Sans CJK SC", sans-serif; font-size:14px; color:#304b68;}
QMainWindow,QDialog {background:#f5faff;} QTabWidget::pane{border:0;background:#fff;border-radius:16px;}
QTabBar::tab{padding:12px 15px;background:#edf5fc;margin:3px;border-radius:9px;}
QTabBar::tab:selected{background:#d4eaff;color:#285d90;}
QPushButton{background:#e3f1ff;border:0;border-radius:10px;padding:10px 14px;}
QPushButton:hover{background:#cde7ff;} QPushButton:disabled{color:#aaa;background:#f0f0f0;}
QLineEdit,QTextEdit,QSpinBox,QComboBox,QListWidget{background:white;border:1px solid #d9e9f5;border-radius:9px;padding:8px;}
QListWidget::item{padding:9px;border-bottom:1px solid #eff6fc;} QLabel#title{font-size:25px;font-weight:700;}
QLabel#clock{font-size:62px;font-weight:700;color:#478fc9;} QProgressBar{border:0;background:#eaf3fa;border-radius:6px;height:10px;}
QProgressBar::chunk{background:#7fb8e5;border-radius:6px;}
'''

def button(text,fn):
    b=QPushButton(text);b.clicked.connect(fn);return b

def label(text,big=False):
    w=QLabel(text);w.setWordWrap(True)
    if big:w.setObjectName('title')
    return w

def page():
    w=QWidget();v=QVBoxLayout(w);v.setContentsMargins(24,22,24,22);v.setSpacing(12);return w,v

class AIWorker(QThread):
    answer=Signal(str)
    def __init__(self,text,config):super().__init__();self.text=text;self.config=config
    def run(self):
        try:
            base=self.config['base'].rstrip('/');key=os.environ.get('LR_PET_API_KEY','')
            if not key:raise ValueError('请先在电脑设置 LR_PET_API_KEY 环境变量，再重启桌宠。')
            body={'model':self.config['model'],'messages':[{'role':'system','content':'你是星梨，一个温柔但务实的学习伙伴。用中文简洁回答。解题先给小提示，鼓励用户自己尝试；不知道就说不知道。不要声称看到了用户屏幕。'},{'role':'user','content':self.text}]}
            req=urllib.request.Request(base+'/chat/completions',data=json.dumps(body).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
            with urllib.request.urlopen(req,timeout=45) as r:data=json.load(r)
            self.answer.emit(data['choices'][0]['message']['content'])
        except Exception as e:self.answer.emit('连接未完成：'+str(e)[:220])

class Pet(QWidget):
    def __init__(self,control):
        super().__init__();self.control=control;self.frame=0;self.phase=0;self.drag=None;self.typing_until=0;self.sparkles=[];self.hop_until=0
        self.setWindowFlags(Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint|Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground);self.setFixedSize(230,310)
        self.sprite=QPixmap(str(ROOT/'assets/pet.png'))
        self.timer=QTimer(self);self.timer.timeout.connect(self.animate);self.timer.start(33)
        pos=control.store.get('pet_position',None)
        g=QApplication.primaryScreen().availableGeometry()
        self.move(QPoint(*pos) if pos else QPoint(g.right()-250,g.bottom()-330));self.clamp()
        self.message='我是星梨，今天一起学一点吧。';self.message_until=0
    def clamp(self):
        screens=QApplication.screens()
        center=self.frameGeometry().center()
        screen=QApplication.screenAt(center)
        if screen is None:
            screen=min(screens,key=lambda s:(s.availableGeometry().center()-center).manhattanLength())
        g=screen.availableGeometry();self.move(max(g.left(),min(self.x(),g.right()-self.width()+1)),max(g.top(),min(self.y(),g.bottom()-self.height()+1)))
    def say(self,text):self.message=text;self.message_until=self.control.ticks+15;self.update()
    def animate(self):
        self.phase+=.09
        self.sparkles=[(x,y-.9,life-1) for x,y,life in self.sparkles if life>0]
        if self.control.ticks>self.message_until and self.message_until:
            self.message='我在这里，陪你做下一小步。';self.message_until=0
        self.update()
    def typing(self):
        self.typing_until=self.phase+1.8
        if random.random()<.25:self.sparkles.append((random.randint(85,155),220,22))
    def paintEvent(self,e):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);p.scale(self.width()/230,self.height()/310)
        p.setPen(Qt.NoPen);p.setBrush(QColor(255,253,255,242));p.drawRoundedRect(8,6,214,68,15,15)
        p.setPen(QColor('#3e6485'));p.setFont(QFont('Microsoft YaHei',10));p.drawText(20,12,190,54,Qt.AlignCenter|Qt.TextWordWrap,self.message)
        y=78+int(math.sin(self.phase)*3)
        if self.phase<self.hop_until:y-=int(abs(math.sin(self.phase*4))*12)
        if not self.sprite.isNull():
            cw=self.sprite.width()//2;ch=self.sprite.height()//2;cell=self.sprite.copy((self.frame%2)*cw,(self.frame//2)*ch,cw,ch)
            p.drawPixmap(10,y,210,210,cell)
        else:
            p.setBrush(QColor('#cbbaf0'));p.drawEllipse(65,y+25,100,110);p.setBrush(QColor('#ffeadf'));p.drawEllipse(75,y+45,80,70)
            p.setBrush(QColor('#eee3ff'));p.drawRoundedRect(75,y+112,80,60,20,20);p.setPen(QColor('#7959a9'));p.drawText(98,y+80,'• ᴗ •')
        if self.phase<self.typing_until:
            p.setPen(QColor('#8fbedf'));p.setBrush(QColor('#e6f4ff'));p.drawRoundedRect(65,233,100,29,6,6)
            for k in range(8):p.drawRoundedRect(73+k*11,243,7,8,2,2)
            p.setBrush(QColor('#b8def9'));p.drawEllipse(87,225+int(math.sin(self.phase*7)*3),21,14);p.drawEllipse(127,225-int(math.sin(self.phase*7)*3),21,14)
        for sx,sy,life in self.sparkles:
            p.setPen(QColor(86,165,227,min(255,life*11)));p.drawText(int(sx),int(sy),'✦')
        p.setPen(QColor('#508cb8'));p.drawText(15,286,200,20,Qt.AlignCenter,'星梨 · 双击打开学习空间')
    def mousePressEvent(self,e):
        if e.button()==Qt.LeftButton:self.drag=e.globalPosition().toPoint()-self.pos()
        if e.button()==Qt.RightButton:
            menu=QMenu(self);menu.addAction('打开学习空间',self.control.reveal);menu.addAction('摸摸头',self.pat);menu.addAction('一起伸个懒腰',self.stretch);menu.addAction('命令助手',self.control.open_commands);menu.addAction('安静 / 恢复提醒',self.control.quiet_toggle);menu.addAction('隐藏桌宠（托盘可恢复）',self.hide);menu.addAction('退出',self.control.quit_app);menu.exec(e.globalPosition().toPoint())
    def mouseMoveEvent(self,e):
        if self.drag is not None:self.move(e.globalPosition().toPoint()-self.drag)
    def mouseReleaseEvent(self,e):
        self.drag=None;self.clamp();self.control.store.set('pet_position',[self.x(),self.y()])
    def mouseDoubleClickEvent(self,e):self.control.reveal()
    def pat(self):
        self.frame=2;self.hop_until=self.phase+3;self.sparkles.extend((random.randint(65,165),random.randint(150,230),30) for _ in range(8));self.say(random.choice(['摸摸头收到啦，做完这一小段再玩。','我陪着你，慢一点也没关系。','把任务缩小一点，就更容易开始啦。']));QTimer.singleShot(3000,self.restore_frame)
    def stretch(self):
        self.hop_until=self.phase+4;self.say("一起活动一下肩膀，再做下一步吧。");self.sparkles.extend((random.randint(65,165),200,30) for _ in range(5))
    def restore_frame(self):self.frame=1 if self.control.clock.mode=='focus' else 3 if self.control.clock.mode=='break' else 0

class Main(QMainWindow):
    def __init__(self):
        super().__init__();DATA.mkdir(parents=True,exist_ok=True);self.store=Store(DATA/'study.sqlite3');self.clock=FocusClock();self.ticks=0;self.worker=None;self.clip_memory=ClipboardMemory();self.keyboard=KeyboardActivity();self.key_count=0;self.hotkey_registered=False;self.quiet=self.store.get('quiet',False);self.sound=None
        self.setWindowTitle('LR StudyPet · 星梨学习空间');self.resize(980,720);self.setMinimumSize(800,620);self.setWindowTitle("LR StudyPet · 星梨 v0.3.0")
        root=QWidget();self.setCentralWidget(root);layout=QVBoxLayout(root);layout.setContentsMargins(24,18,24,18)
        head=QHBoxLayout();head.addWidget(label('星梨的学习空间',True));head.addStretch();head.addWidget(button('桌宠',lambda:self.pet.show()));layout.addLayout(head)
        self.status=label('');layout.addWidget(self.status);self.tabs=QTabWidget();layout.addWidget(self.tabs)
        self.focus_ui();self.task_ui();self.review_ui();self.rescue_ui();self.journal_ui();self.stats_ui();self.chat_ui();self.plan_ui();self.toolbox_ui();self.settings_ui()
        self.pet=Pet(self);self.apply_pet_size(self.pet_scale.value());self.pet.show();self.tray=QSystemTrayIcon(self)
        self.update_subjects()
        QApplication.instance().screenRemoved.connect(lambda screen:QTimer.singleShot(0,self.pet.clamp))
        icon=QPixmap(64,64);icon.fill(QColor('#85bce6'));self.tray.setIcon(QIcon(icon));self.setWindowIcon(QIcon(icon))
        menu=QMenu();menu.addAction('学习空间',self.reveal);menu.addAction('显示桌宠',self.pet.show);menu.addAction('安静 / 恢复提醒',self.quiet_toggle);menu.addAction('退出',self.quit_app);self.tray.setContextMenu(menu);self.tray.activated.connect(lambda reason:self.reveal() if reason==QSystemTrayIcon.DoubleClick else None);self.tray.show()
        self.timer=QTimer(self);self.timer.timeout.connect(self.tick);self.timer.start(1000);self.refresh()
        QApplication.instance().clipboard().dataChanged.connect(self.clipboard_changed)
        self.activity_timer=QTimer(self);self.activity_timer.timeout.connect(self.activity_tick);self.activity_timer.start(50)
        self.expiry_timer=QTimer(self);self.expiry_timer.timeout.connect(self.clipboard_display);self.expiry_timer.start(250)
        QApplication.instance().installEventFilter(self)
        if sys.platform=='win32':self.register_command_hotkey()
        recover=self.store.get('recovery',None)
        if recover:
            self.resume_note.setText('上次专注未正常结束：'+recover.get('subject','')+'。'+recover.get('note',''))
            if recover.get('seconds',0)>0:
                if QMessageBox.question(self,'恢复记录',f"上次未结束的专注已记录 {recover['seconds']//60} 分钟。保存这段时间？")==QMessageBox.Yes:self.store.session(recover['subject'],recover['seconds'],'异常退出恢复；'+recover.get('note',''))
            self.store.set('recovery',None);self.refresh()
    def add_tab(self,w,name):self.tabs.addTab(w,name)
    def reveal(self):self.showNormal();self.raise_();self.activateWindow()
    def quiet_toggle(self):self.quiet=not self.quiet;self.store.set('quiet',self.quiet);self.refresh();self.pet.say('安静模式已开启。' if self.quiet else '提醒已恢复。')
    def notify(self,text):
        if not self.quiet:self.pet.say(text);self.tray.showMessage('星梨',text,QSystemTrayIcon.Information,6000)
    def focus_ui(self):
        w,v=page();v.addWidget(label('先做一小段，不用一次学完。',True));self.clock_text=QLabel('25:00');self.clock_text.setObjectName('clock');self.clock_text.setAlignment(Qt.AlignCenter);v.addWidget(self.clock_text)
        self.progress=QProgressBar();self.progress.setRange(0,100);v.addWidget(self.progress)
        row=QHBoxLayout();self.subject=QComboBox();self.subject.addItems(SUBJECTS);self.minutes=QSpinBox();self.minutes.setRange(1,240);self.minutes.setValue(25);self.break_minutes=QSpinBox();self.break_minutes.setRange(1,60);self.break_minutes.setValue(5)
        for x in (label('科目'),self.subject,label('专注分钟'),self.minutes,label('休息分钟'),self.break_minutes):row.addWidget(x)
        v.addLayout(row);row=QHBoxLayout()
        self.start_btn=button('开始专注',self.start_focus);self.pause_btn=button('暂停 / 继续',self.pause_focus);self.end_btn=button('结束并保存',self.end_focus)
        for b in (self.start_btn,self.pause_btn,self.end_btn):row.addWidget(b)
        v.addLayout(row)
        self.resume_note=QLineEdit();self.resume_note.setPlaceholderText('中断书签：做到哪了？下次第一步做什么？');self.resume_note.setText(self.store.get('bookmark',''));self.resume_note.textChanged.connect(lambda text:self.store.set('bookmark',text));v.addWidget(self.resume_note)
        v.addWidget(button('回来先做 5 分钟',self.restart_small))
        row=QHBoxLayout();self.energy=QComboBox();self.energy.addItems(['中','低','高']);row.addWidget(label('当前精力'));row.addWidget(self.energy);row.addWidget(button('帮我选下一步',lambda:self.next_text.setText(self.store.recommend(self.energy.currentText()))));v.addLayout(row);self.next_text=label('低精力选小任务；正常时优先今天投入较少的科目。');v.addWidget(self.next_text);v.addStretch();self.add_tab(w,'专注')
    def start_focus(self):
        if self.clock.mode!='idle':return
        self.session_subject=self.subject.currentText();self.clock.start(self.minutes.value());self.subject.setEnabled(False);self.minutes.setEnabled(False);self.pet.frame=1;self.notify('我也开始读书啦。这段时间，只做眼前这一件事。');self.refresh()
    def restart_small(self):
        if self.clock.mode!='idle':return
        self.minutes.setValue(5);self.start_focus()
    def pause_focus(self):
        if self.clock.mode=='paused':self.clock.resume();self.pet.restore_frame()
        elif self.clock.mode in ('focus','break'):self.clock.pause();self.pet.frame=0;self.notify('给下一步留一句书签，回来就不用重新找思路。')
        self.refresh()
    def end_focus(self):
        self.clock.tick();mode=self.clock.previous if self.clock.mode=='paused' else self.clock.mode
        if mode=='focus':self.store.session(self.session_subject,min(self.clock.elapsed,self.clock.duration),self.resume_note.text())
        self.clock.reset();self.store.set('recovery',None);self.subject.setEnabled(True);self.minutes.setEnabled(True);self.pet.frame=0;self.refresh()
    def task_ui(self):
        w,v=page();v.addWidget(label('把目标变成今天能完成的小动作',True));self.task_title=QLineEdit();self.task_title.setPlaceholderText('例如：做完两道 PV 题，并写出信号量初值');v.addWidget(self.task_title)
        row=QHBoxLayout();self.task_subject=QComboBox();self.task_subject.addItems(SUBJECTS);self.task_minutes=QSpinBox();self.task_minutes.setRange(1,240);self.task_minutes.setValue(25)
        row.addWidget(self.task_subject);row.addWidget(self.task_minutes);row.addWidget(button('添加任务',self.add_task));v.addLayout(row);self.task_list=QListWidget();v.addWidget(self.task_list)
        row=QHBoxLayout();row.addWidget(button('完成 / 撤销完成',self.toggle_task));row.addWidget(button('用这项任务开始专注',self.focus_task));v.addLayout(row);self.add_tab(w,'任务')
    def add_task(self):
        try:self.store.task(self.task_title.text(),self.task_subject.currentText(),self.task_minutes.value());self.task_title.clear();self.refresh()
        except ValueError as e:QMessageBox.warning(self,'任务',str(e))
    def toggle_task(self):
        item=self.task_list.currentItem()
        if item:self.store.done(item.data(Qt.UserRole)['id']);self.pet.pat();self.refresh()
    def focus_task(self):
        item=self.task_list.currentItem()
        if not item:return
        if self.clock.mode!='idle':QMessageBox.information(self,'专注中','先结束当前专注，再切换任务。');return
        t=item.data(Qt.UserRole);self.subject.setCurrentText(t['subject']);self.minutes.setValue(t['minutes']);self.resume_note.setText(t['title']);self.tabs.setCurrentIndex(0);self.start_focus()
    def review_ui(self):
        w,v=page();v.addWidget(label('闭卷先回忆，再看答案',True));self.review_subject=QComboBox();self.review_subject.addItems(SUBJECTS);v.addWidget(self.review_subject);self.question=QLineEdit();self.question.setPlaceholderText('问题 / 易错点');self.answer=QTextEdit();self.answer.setPlaceholderText('你的答案、方法或纠错说明');self.answer.setMaximumHeight(90);v.addWidget(self.question);v.addWidget(self.answer);v.addWidget(button('加入复习卡',self.add_review));self.review_list=QListWidget();v.addWidget(self.review_list);self.review_answer=label('选一张卡，先在心里或纸上回答。');v.addWidget(self.review_answer)
        row=QHBoxLayout();row.addWidget(button('显示答案',self.show_answer))
        for text,grade in [('没记住 · 明天再练',0),('费力想起',1),('轻松掌握',2)]:row.addWidget(button(text,lambda checked=False,g=grade:self.grade(g)))
        v.addLayout(row);self.add_tab(w,'复习')
        row=QHBoxLayout();row.addWidget(button('导入 CSV 卡片',self.import_review_csv));row.addWidget(button('导出 CSV 卡片',self.export_review_csv));v.addLayout(row)
    def import_review_csv(self):
        path,_=QFileDialog.getOpenFileName(self,'导入复习卡','','CSV (*.csv)')
        if not path:return
        try:
            cards=read_cards(path,self.review_subject.currentText())
            if QMessageBox.question(self,'导入预览',f'已检查 {len(cards)} 张卡片。导入后保留原有进度，完全相同的卡片跳过。继续？')!=QMessageBox.Yes:return
            count=import_cards(self.store,cards);self.update_subjects();self.refresh();QMessageBox.information(self,'导入完成',f'新增 {count} 张卡片。')
        except Exception as e:QMessageBox.warning(self,'导入失败',str(e))
    def export_review_csv(self):
        path,_=QFileDialog.getSaveFileName(self,'导出复习卡','StudyPet-cards.csv','CSV (*.csv)')
        if path:
            try:export_cards(self.store,path);QMessageBox.information(self,'导出完成','CSV 包含问题、答案和科目；复习进度请用 JSON 备份。')
            except Exception as e:QMessageBox.warning(self,'导出失败',str(e))
    def add_review(self):
        try:self.store.review(self.question.text(),self.answer.toPlainText(),self.review_subject.currentText());self.question.clear();self.answer.clear();self.refresh()
        except ValueError as e:QMessageBox.warning(self,'复习卡',str(e))
    def show_answer(self):
        item=self.review_list.currentItem()
        if item:self.review_answer.setText(item.data(Qt.UserRole)['answer'])
    def grade(self,g):
        item=self.review_list.currentItem()
        if item:self.store.grade(item.data(Qt.UserRole)['id'],g);self.review_answer.setText('已安排下一次复习。');self.refresh()
    def rescue_ui(self):
        w,v=page();v.addWidget(label('卡题救援：先找到卡住的那一步',True));self.stuck=QTextEdit();self.stuck.setPlaceholderText('写下题目、已经试过的方法，以及具体卡在哪里。');v.addWidget(self.stuck)
        self.stuck_type=QComboBox();self.stuck_type.addItems(['看不懂题意','不知道选什么方法','方法知道但算不出','总在同一处出错','学不下去']);v.addWidget(self.stuck_type);v.addWidget(button('生成三步自救单',self.rescue));self.rescue_text=QTextEdit();self.rescue_text.setReadOnly(True);v.addWidget(self.rescue_text);v.addWidget(button('存入卡点记录',lambda:self.save_journal('卡题',self.stuck.toPlainText()+'\n'+self.rescue_text.toPlainText())));self.add_tab(w,'卡题救援')
    def rescue(self):
        plans=[['圈出已知量、要求的量，把题意改写成一句话。','画图或举一个最简单的数值例子。','只写第一步，不要求现在算到最后。'],['找题目中的识别信号：结构、条件、关键词。','列出两个候选方法，各写使用条件。','先试能利用最多已知条件的那个方法，限时 5 分钟。'],['把最后一个正确步骤单独抄出来。','每行只做一种变形，检查符号、范围和单位。','用简单值或代回原式检查，再继续。'],['写下这次错误发生的具体一步。','写一条执行前能检查的规则。','把同类问题做成复习卡，明天闭卷再试。'],['把任务缩成 5 分钟就能完成的一个动作。','先休息 2 分钟，离开屏幕活动一下。','回来只做缩小后的动作，完成后再决定是否继续。']]
        self.rescue_text.setPlainText('\n\n'.join(f'{i+1}. {s}' for i,s in enumerate(plans[self.stuck_type.currentIndex()]))+'\n\n这是离线引导，不是对题目的自动解答。需要解题提示，可把题目发到「聊天」。')
    def journal_ui(self):
        w,v=page();v.addWidget(label('把一天留下来，不只留下时长',True));self.journal_text=QTextEdit();self.journal_text.setPlaceholderText('今天学会了什么？哪里容易错？明天第一步做什么？');v.addWidget(self.journal_text);row=QHBoxLayout()
        for k in ['收获','错因','明日第一步']:row.addWidget(button('记录'+k,lambda checked=False,kind=k:self.save_journal(kind,self.journal_text.toPlainText())))
        v.addLayout(row);self.journal_list=QListWidget();v.addWidget(self.journal_list);self.add_tab(w,'手记')
    def save_journal(self,k,t):
        if not t.strip():return
        self.store.journal(k,t);self.journal_text.clear();self.refresh();self.notify('记下了。未来的你会感谢这句提示。')
    def stats_ui(self):
        w,v=page();v.addWidget(label('成长来自你真正完成的学习',True));self.stats_text=label('');v.addWidget(self.stats_text)
        v.addWidget(label('最近 28 天 · 颜色按每天计时分钟加深（悬停查看）'))
        grid=QGridLayout();self.activity_cells=[]
        for i in range(28):
            cell=QLabel('');cell.setAlignment(Qt.AlignCenter);cell.setMinimumHeight(28);grid.addWidget(cell,i//7,i%7);self.activity_cells.append(cell)
        v.addLayout(grid);self.week_list=QListWidget();v.addWidget(self.week_list)
        row=QHBoxLayout();row.addWidget(button('刷新统计',self.refresh));row.addWidget(button('导出本周 Markdown 周报',self.export_week));v.addLayout(row)
        v.addWidget(label('时长只统计主动开始的专注；不监控窗口、屏幕或键盘。完成任务可撤销，经验也会随之调整。'));self.add_tab(w,'成长')
    def export_week(self):
        path,_=QFileDialog.getSaveFileName(self,'导出学习周报','StudyPet-week-'+day()+'.md','Markdown (*.md)')
        if path:
            try:Path(path).write_text(weekly_report(self.store),encoding='utf-8');QMessageBox.information(self,'周报','已导出。周报包含手记，分享前检查个人内容。')
            except Exception as e:QMessageBox.warning(self,'导出失败',str(e))
    def chat_ui(self):
        w,v=page();v.addWidget(label('问星梨 · 可选 AI',True));self.chat_log=QTextEdit();self.chat_log.setReadOnly(True);v.addWidget(self.chat_log);self.chat_input=QLineEdit();self.chat_input.setPlaceholderText('未连接 AI 时，支持：下一步 / 休息 / 鼓励 / 复习');self.chat_input.returnPressed.connect(self.chat);v.addWidget(self.chat_input);self.send_btn=button('发送',self.chat);v.addWidget(self.send_btn);v.addWidget(label('联网 AI 只收到你在此输入的消息。任务、手记和屏幕不会自动发送。对话仅在本次打开期间显示。'));self.add_tab(w,'聊天')
    def chat(self):
        text=self.chat_input.text().strip()
        if not text:return
        self.chat_input.clear();self.chat_log.append('你：'+text.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;'))
        config=self.store.get('ai',{})
        if config.get('enabled'):
            if self.worker and self.worker.isRunning():return
            self.send_btn.setEnabled(False);self.chat_input.setEnabled(False);self.worker=AIWorker(text,config);self.worker.answer.connect(self.chat_answer);self.worker.start()
        else:
            if '下一步' in text:reply=self.store.recommend(self.energy.currentText())
            elif '复习' in text:reply='先打开复习页，选一张到期卡。先闭卷回答，再看答案。'
            elif '休息' in text:reply='起身走两分钟，看看远处。回来时按书签继续。'
            elif '鼓励' in text:reply='不会做的地方就是下一步的起点。先把卡点说清楚，再做一个小动作。'
            else:reply='现在是离线陪伴模式。我可以帮你选下一步、提醒休息和复习；自由问答需要在设置中连接 AI。'
            self.chat_answer(reply)
    def chat_answer(self,text):self.chat_log.append('星梨：'+text.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;'));self.send_btn.setEnabled(True);self.chat_input.setEnabled(True);self.pet.say(text[:65])
    def plan_ui(self):
        w,v=page();v.addWidget(label('用计划照顾未来的自己',True));row=QHBoxLayout();self.goal=QSpinBox();self.goal.setRange(5,720);self.goal.setValue(self.store.get('daily_goal',120));row.addWidget(label('每日专注目标 / 分钟'));row.addWidget(self.goal);v.addLayout(row);self.goal.valueChanged.connect(lambda n:self.store.set('daily_goal',n));self.goal_progress=QProgressBar();v.addWidget(self.goal_progress)
        row=QHBoxLayout();self.target_name=QLineEdit(self.store.get('target_name','我的目标'));self.target_date=QDateEdit();self.target_date.setCalendarPopup(True);self.target_date.setDisplayFormat('yyyy-MM-dd');self.target_date.setDate(QDate.fromString(self.store.get('target_date',day()),'yyyy-MM-dd'));row.addWidget(self.target_name);row.addWidget(self.target_date);row.addWidget(button('保存目标日期',self.save_target));v.addLayout(row);self.countdown=label('');v.addWidget(self.countdown)
        v.addWidget(label('本机定时提醒：需要桌宠正在运行。',True));self.alarm_text=QLineEdit();self.alarm_text.setPlaceholderText('例如：复习昨天的错题');self.alarm_time=QDateTimeEdit(QDateTime.currentDateTime().addSecs(3600));self.alarm_time.setCalendarPopup(True);self.alarm_time.setDisplayFormat('yyyy-MM-dd HH:mm');v.addWidget(self.alarm_text);row=QHBoxLayout();row.addWidget(self.alarm_time);row.addWidget(button('添加提醒',self.add_alarm));v.addLayout(row);self.alarm_list=QListWidget();v.addWidget(self.alarm_list);v.addWidget(button('删除所选提醒',self.remove_alarm));self.add_tab(w,'计划')
    def save_target(self):
        self.store.set('target_name',self.target_name.text().strip() or '我的目标');self.store.set('target_date',self.target_date.date().toString('yyyy-MM-dd'));self.refresh()
    def add_alarm(self):
        if not self.alarm_text.text().strip():return
        if self.alarm_time.dateTime()<=QDateTime.currentDateTime():QMessageBox.warning(self,'提醒','请选择未来的时间。');return
        alarms=self.store.get('alarms',[]);alarms.append({'text':self.alarm_text.text().strip(),'at':self.alarm_time.dateTime().toSecsSinceEpoch(),'done':False});self.store.set('alarms',alarms);self.alarm_text.clear();self.refresh()
    def remove_alarm(self):
        i=self.alarm_list.currentItem()
        if i:
            alarms=self.store.get('alarms',[]);alarms.pop(i.data(Qt.UserRole));self.store.set('alarms',alarms);self.refresh()
    def toolbox_ui(self):
        w,v=page();v.addWidget(label('陪你打字，也照顾你的桌面',True));row=QHBoxLayout();self.keyboard_enabled=QCheckBox('键盘联动（仅按键活动，不记录文字）');self.keyboard_enabled.setChecked(self.store.get('keyboard_enabled',False));self.keyboard_enabled.toggled.connect(self.keyboard_toggle);row.addWidget(self.keyboard_enabled);self.typing_count=label('本次按键活动：0');row.addWidget(self.typing_count);v.addLayout(row)
        self.clipboard_enabled=QCheckBox('剪贴板上一条：仅在内存保留 60 秒');self.clipboard_enabled.setChecked(False);self.clipboard_enabled.toggled.connect(self.clipboard_toggle);v.addWidget(self.clipboard_enabled);self.clip_status=label('未启用剪贴板记忆');v.addWidget(self.clip_status)
        self.clip_preview=QTextEdit();self.clip_preview.setReadOnly(True);self.clip_preview.setMaximumHeight(75);v.addWidget(self.clip_preview);row=QHBoxLayout();row.addWidget(button('恢复上一条到剪贴板',self.clip_restore));row.addWidget(button('立即清空记忆',self.clip_clear));v.addLayout(row)
        row=QHBoxLayout();self.desktop_input=QLineEdit(str(desktop_path()));row.addWidget(self.desktop_input);row.addWidget(button('选择桌面目录',self.choose_desktop));row.addWidget(button('生成整理建议',self.scan_desktop));v.addLayout(row);self.desktop_output=QTextEdit();self.desktop_output.setReadOnly(True);v.addWidget(self.desktop_output)
        row=QHBoxLayout();row.addWidget(button('打开所选目录',self.open_desktop));row.addWidget(button('命令助手 · Ctrl+Alt+Space',self.open_commands));row.addWidget(button('互动：伸懒腰',lambda:self.pet.stretch()));v.addLayout(row)
        v.addWidget(label('键盘联动需手动开启；剪贴板不会写入磁盘或发送给 AI。整理功能只给建议。命令助手只读取你在助手框里输入的内容。'));self.add_tab(w,'桌面助手')
    def keyboard_toggle(self,x):self.store.set('keyboard_enabled',x);self.keyboard.clear()
    def activity_tick(self):
        if not self.keyboard_enabled.isChecked():return
        count=self.keyboard.poll()
        if count:self.on_keys(count)
    def eventFilter(self,obj,event):
        if sys.platform!='win32' and event.type()==QEvent.KeyPress and self.keyboard_enabled.isChecked():self.on_keys(1)
        return False
    def on_keys(self,count):
        self.key_count+=count;self.pet.typing();self.typing_count.setText(f'本次按键活动：{self.key_count}');self.pet.frame=1 if self.clock.mode!='break' else 3
    def apply_pet_size(self,n):
        if hasattr(self,'pet'):self.pet.setFixedSize(int(230*n/100),int(310*n/100));self.pet.clamp()
        self.store.set('pet_scale',n)
    def clipboard_toggle(self,x):
        self.clip_memory.clear()
        if x:self.clip_memory.observe(QApplication.instance().clipboard().text())
        self.clipboard_display()
    def clipboard_changed(self):
        if self.clipboard_enabled.isChecked():self.clip_memory.observe(QApplication.instance().clipboard().text())
        self.clipboard_display()
    def clipboard_display(self):
        self.clip_memory.expire()
        if not self.clipboard_enabled.isChecked():self.clip_status.setText('未启用剪贴板记忆');self.clip_preview.clear();return
        prior=self.clip_memory.prior();self.clip_status.setText(f'上一条还保留 {self.clip_memory.remaining()} 秒' if prior else '暂无上一条；复制两条短文本即可体验。60 秒后记忆清除。')
        if self.clip_preview.toPlainText()!=prior:self.clip_preview.setPlainText(prior)
    def clip_clear(self):self.clip_memory.clear();self.clipboard_display()
    def clip_restore(self):
        prior=self.clip_memory.prior()
        if prior:QApplication.instance().clipboard().setText(prior);self.pet.say('上一条已恢复，直接粘贴就好。')
    def choose_desktop(self):
        path=QFileDialog.getExistingDirectory(self,'选择要查看的桌面目录',self.desktop_input.text())
        if path:self.desktop_input.setText(path)
    def scan_desktop(self):
        try:self.desktop_output.setPlainText(desktop_advice(self.desktop_input.text()))
        except Exception as e:QMessageBox.warning(self,'整理建议',str(e))
    def open_desktop(self):
        p=Path(self.desktop_input.text())
        if p.is_dir():QDesktopServices.openUrl(QUrl.fromLocalFile(str(p.resolve())))
    def open_commands(self):
        dialog=QDialog(self);dialog.setWindowTitle('星梨命令助手 · 只推荐，不执行');dialog.resize(750,520);v=QVBoxLayout(dialog);v.addWidget(label('输入命令前缀或中文需求，选择后复制。'))
        row=QHBoxLayout();category=QComboBox();category.addItems(['全部','Git','Python','Docker','Windows','Linux','网络']);query=QLineEdit();query.setPlaceholderText('例如 git / 查看端口 / 查看日志');row.addWidget(category);row.addWidget(query);v.addLayout(row);items=QListWidget();v.addWidget(items);detail=label('带 <占位符> 的命令需替换后使用。');v.addWidget(detail)
        def update():
            items.clear()
            for r in suggest_commands(query.text(),category.currentText()):
                item=QListWidgetItem(r[1]+'  ·  '+r[2]);item.setData(Qt.UserRole,r);items.addItem(item)
        def explain():
            item=items.currentItem()
            if item:detail.setText(item.data(Qt.UserRole)[3])
        def copy():
            item=items.currentItem()
            if item:QApplication.instance().clipboard().setText(item.data(Qt.UserRole)[2]);detail.setText('已复制。确认参数与当前环境后自行运行。')
        query.textChanged.connect(update);category.currentTextChanged.connect(update);items.itemSelectionChanged.connect(explain);v.addWidget(button('复制所选命令',copy));update();dialog.show();query.setFocus();self.command_dialog=dialog
    def register_command_hotkey(self):
        try:
            import ctypes,ctypes.wintypes
            ctypes.windll.user32.RegisterHotKey.argtypes=[ctypes.wintypes.HWND,ctypes.c_int,ctypes.wintypes.UINT,ctypes.wintypes.UINT]
            self.hotkey_registered=bool(ctypes.windll.user32.RegisterHotKey(int(self.winId()),707,0x4000|0x0002|0x0001,0x20))
        except Exception:self.hotkey_registered=False
    def nativeEvent(self,event_type,message):
        if sys.platform=='win32':
            import ctypes.wintypes
            msg=ctypes.wintypes.MSG.from_address(int(message))
            if msg.message==0x0312 and msg.wParam==707:self.open_commands();return True,0
        return False,0
    def startup_toggle(self,x):
        try:configure_startup(x,ROOT)
        except Exception as e:
            self.autostart.blockSignals(True);self.autostart.setChecked(startup_file().exists() if sys.platform=='win32' else False);self.autostart.blockSignals(False);QMessageBox.warning(self,'开机自启动',str(e))
    def settings_ui(self):
        w,v=page();v.addWidget(label('按你的节奏来',True));self.autostart=QCheckBox('登录 Windows 后自动启动星梨');self.autostart.setChecked(startup_file().exists() if sys.platform=='win32' else False);self.autostart.setEnabled(sys.platform=='win32');self.autostart.toggled.connect(self.startup_toggle);v.addWidget(self.autostart);row=QHBoxLayout();row.addWidget(label('桌宠大小 / %'));self.pet_scale=QSpinBox();self.pet_scale.setRange(70,180);self.pet_scale.setValue(self.store.get('pet_scale',100));self.pet_scale.valueChanged.connect(self.apply_pet_size);row.addWidget(self.pet_scale);v.addLayout(row);self.ai_enabled=QCheckBox('启用联网 AI 聊天');cfg=self.store.get('ai',{});self.ai_enabled.setChecked(cfg.get('enabled',False));v.addWidget(self.ai_enabled);self.ai_base=QLineEdit(cfg.get('base','https://api.openai.com/v1'));self.ai_model=QLineEdit(cfg.get('model',''));self.ai_model.setPlaceholderText('填写服务商提供的模型名称');v.addWidget(label('兼容接口地址（以 /v1 结尾）'));v.addWidget(self.ai_base);v.addWidget(label('模型名称'));v.addWidget(self.ai_model);v.addWidget(button('保存 AI 配置',self.save_ai));v.addWidget(label('密钥从电脑环境变量 LR_PET_API_KEY 读取，不存入备份。启用在线服务可能产生服务商费用。'))
        row=QHBoxLayout();row.addWidget(button('导出学习备份',self.export));row.addWidget(button('恢复学习备份',self.restore));row.addWidget(button('安静 / 恢复提醒',self.quiet_toggle));v.addLayout(row)
        row=QHBoxLayout();self.subject_names=QLineEdit('，'.join(self.store.get('custom_subjects',SUBJECTS)));row.addWidget(self.subject_names);row.addWidget(button('保存科目',self.save_subjects));v.addLayout(row)
        v.addWidget(label('用中文或英文逗号分隔科目；最多 20 个。已有记录的科目继续保留。'))
        self.health=QCheckBox('每 50 分钟轻声提醒活动和喝水');self.health.setChecked(self.store.get('health',True));self.health.toggled.connect(lambda x:self.store.set('health',x));v.addWidget(self.health)
        row=QHBoxLayout();row.addWidget(button('雨声开 / 关',self.noise));row.addWidget(button('两分钟离屏休息',self.short_break));v.addLayout(row)
        v.addWidget(label('数据保存在本机用户目录。关闭学习窗口后桌宠继续运行；从桌宠右键或托盘菜单退出。右键桌宠可以摸头、切换安静模式和退出。'));v.addStretch();scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QFrame.NoFrame);scroll.setWidget(w);self.add_tab(scroll,'设置')
    def update_subjects(self):
        names=list(dict.fromkeys(self.store.get('custom_subjects',SUBJECTS)+[r['subject'] for t in ('tasks','reviews','sessions') for r in self.store.rows(t) if r['subject']]))
        self.subjects=names
        for combo in (self.subject,self.task_subject,self.review_subject):
            current=combo.currentText();combo.clear();combo.addItems(names)
            if current in names:combo.setCurrentText(current)
    def save_subjects(self):
        names=list(dict.fromkeys(n.strip() for n in self.subject_names.text().replace('，',',').split(',') if n.strip()))
        if not names or len(names)>20 or any(len(n)>80 for n in names):QMessageBox.warning(self,'科目','请填写 1～20 个科目，每个最多 80 字。');return
        if self.clock.mode!='idle':QMessageBox.information(self,'科目','请先结束当前计时再修改科目。');return
        self.store.set('custom_subjects',names);self.update_subjects();self.refresh()
    def save_ai(self):
        base=self.ai_base.text().strip();model=self.ai_model.text().strip()
        if self.ai_enabled.isChecked() and (not base.startswith('https://') or not model):QMessageBox.warning(self,'AI 配置','请填写 HTTPS 接口地址和模型名称。');return
        self.store.set('ai',{'enabled':self.ai_enabled.isChecked(),'base':base,'model':model});QMessageBox.information(self,'AI 配置','配置已保存。密钥通过 LR_PET_API_KEY 环境变量读取。')
    def export(self):
        path,_=QFileDialog.getSaveFileName(self,'导出备份','StudyPet-backup.json','JSON (*.json)')
        if path:self.store.export(path);QMessageBox.information(self,'备份','导出成功。备份包含任务、专注、复习卡和手记，不包含密钥。')
    def restore(self):
        path,_=QFileDialog.getOpenFileName(self,'恢复备份','','JSON (*.json)')
        if not path:return
        if self.clock.mode!='idle':QMessageBox.warning(self,'恢复','请先结束专注。');return
        if QMessageBox.question(self,'恢复备份','将替换当前学习记录。恢复前会自动备份现有数据。继续？')!=QMessageBox.Yes:return
        try:
            self.store.export(DATA/('before-restore-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.json'));self.store.restore(path);self.update_subjects();self.refresh()
        except Exception as e:QMessageBox.warning(self,'恢复失败',str(e))
    def noise(self):
        if sys.platform!='win32':
            QMessageBox.information(self,'声音','雨声功能仅在 Windows 版启用。');return
        if self.sound:
            import winsound
            winsound.PlaySound(None,0);self.sound=False;return
        try:
            path=DATA/'rain.wav'
            if not path.exists():
                rng=random.Random(43);prev=0;buff=bytearray()
                for i in range(22050*6):prev=.55*prev+.45*rng.uniform(-1,1);buff.extend(struct.pack('<h',int(prev*9000)))
                with wave.open(str(path),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(22050);f.writeframes(buff)
            import winsound
            winsound.PlaySound(str(path),winsound.SND_FILENAME|winsound.SND_ASYNC|winsound.SND_LOOP);self.sound=True
        except Exception as e:QMessageBox.warning(self,'声音',str(e))
    def short_break(self):
        if self.clock.mode!='idle':QMessageBox.information(self,'休息','请暂停或结束当前专注，再开始单独休息。');return
        self.clock.start(2,'break');self.pet.frame=3;self.notify('休息两分钟。起身活动，看看远处。');self.refresh()
    def refresh(self):
        xp=self.store.xp();self.status.setText(f"今天专注 {self.store.today_seconds()//60} 分钟  ·  Lv.{1+xp//120}  ·  经验 {xp}  ·  {'安静模式' if self.quiet else '温柔提醒'}")
        self.start_btn.setEnabled(self.clock.mode=='idle');self.pause_btn.setEnabled(self.clock.mode!='idle');self.end_btn.setEnabled(self.clock.mode!='idle')
        self.task_list.clear()
        for t in self.store.rows('tasks'):
            i=QListWidgetItem(f"{'✓' if t['done'] else '○'}  {t['title']}  ·  {t['subject']} / {t['minutes']} 分钟");i.setData(Qt.UserRole,t);self.task_list.addItem(i)
        self.review_list.clear()
        for r in self.store.rows('reviews'):
            if r['due']<=day():
                i=QListWidgetItem(r['subject']+' · '+r['question']);i.setData(Qt.UserRole,r);self.review_list.addItem(i)
        self.journal_list.clear()
        for r in self.store.rows('journal')[:100]:self.journal_list.addItem(r['date']+' / '+r['kind']+'\n'+r['text'])
        self.stats_text.setText(f"等级 {1+xp//120} · 共专注 {sum(s['seconds'] for s in self.store.rows('sessions'))//60} 分钟\n完成任务 {sum(t['done'] for t in self.store.rows('tasks'))} 项 · 待复习 {self.review_list.count()} 张")
        for cell,(date,seconds) in zip(self.activity_cells,activity_days(self.store)):
            color='#edf4fa' if seconds==0 else '#cee6fa' if seconds<1800 else '#93c6ee' if seconds<5400 else '#4d96cc'
            cell.setText(date[5:]);cell.setToolTip(f'{date}: {seconds//60} 分钟');cell.setStyleSheet(f'background:{color};border-radius:5px;color:#173c5d;padding:2px')
        self.goal_progress.setRange(0,self.goal.value());self.goal_progress.setValue(self.store.today_seconds()//60);self.goal_progress.setFormat('%v / %m 分钟')
        target=datetime.date.fromisoformat(self.store.get('target_date',day()));delta=(target-datetime.date.today()).days;self.countdown.setText(self.store.get('target_name','我的目标')+f' · 距离目标日期 {delta} 天')
        self.alarm_list.clear()
        for index,a in enumerate(self.store.get('alarms',[])):
            item=QListWidgetItem(('✓ 已提醒' if a['done'] else '○ 待提醒')+' · '+datetime.datetime.fromtimestamp(a['at']).strftime('%m-%d %H:%M')+' · '+a['text']);item.setData(Qt.UserRole,index);self.alarm_list.addItem(item)
        self.week_list.clear()
        for d in [datetime.date.today()-datetime.timedelta(days=i) for i in range(7)]:
            parts=[f"{s} {sum(r['seconds'] for r in self.store.rows('sessions') if r['date']==d.isoformat() and r['subject']==s)//60} 分" for s in getattr(self,'subjects',SUBJECTS)];self.week_list.addItem(d.isoformat()+'  '+ ' · '.join(parts))
    def tick(self):
        self.ticks+=1
        alarms=self.store.get('alarms',[]);changed=False
        for a in alarms:
            if not a['done'] and a['at']<=int(datetime.datetime.now().timestamp()):
                a['done']=True;changed=True;self.notify(a['text'])
        if changed:self.store.set('alarms',alarms);self.refresh()
        remaining=self.clock.tick();total=self.clock.duration
        if self.clock.mode!='idle':
            seconds=int(math.ceil(remaining));self.clock_text.setText(f'{seconds//60:02d}:{seconds%60:02d}');self.progress.setValue(int(min(100,self.clock.elapsed/max(total,1)*100)))
        else:self.clock_text.setText(f'{self.minutes.value():02d}:00');self.progress.setValue(0)
        if self.clock.mode=='focus':
            if self.ticks%5==0:self.store.set('recovery',{'subject':self.session_subject,'seconds':int(min(self.clock.elapsed,total)),'note':self.resume_note.text()})
            if remaining<=0:
                self.store.session(self.session_subject,total,self.resume_note.text());self.store.set('recovery',None);self.clock.start(self.break_minutes.value(),'break');self.pet.frame=2;self.notify('这一段完成了！把收获写一句，然后休息一下。');self.refresh();QTimer.singleShot(3000,self.pet.restore_frame)
        elif self.clock.mode=='break' and remaining<=0:
            self.clock.reset();self.subject.setEnabled(True);self.minutes.setEnabled(True);self.pet.frame=0;self.notify('休息结束。看看中断书签，再决定下一段。');self.refresh()
        if self.ticks%3000==0 and self.health.isChecked():self.notify('活动一下肩颈，喝口水，再回来继续。')
        if self.ticks%60==0:self.refresh()
    def closeEvent(self,e):
        if QSystemTrayIcon.isSystemTrayAvailable():e.ignore();self.hide();self.notify('学习空间已收起，我还在桌面陪你。')
        else:e.ignore();self.quit_app()
    def quit_app(self):
        if self.worker and self.worker.isRunning():QMessageBox.information(self,'正在连接','AI 请求仍在进行，结束后再退出，最长等待约 45 秒。');return
        self.end_focus();self.clip_memory.clear();self.keyboard.clear()
        if self.hotkey_registered:
            import ctypes,ctypes.wintypes
            ctypes.windll.user32.UnregisterHotKey.argtypes=[ctypes.wintypes.HWND,ctypes.c_int]
            ctypes.windll.user32.UnregisterHotKey(int(self.winId()),707)
        self.tray.hide();QApplication.quit()

if __name__=='__main__':
    if '--smoke-test' in sys.argv:
        import tempfile
        os.environ['LOCALAPPDATA']=tempfile.mkdtemp(prefix='pet-smoke-');DATA=Path(os.environ['LOCALAPPDATA'])/'LR-StudyPet'
    app=QApplication(sys.argv);app.setStyleSheet(STYLE);app.setQuitOnLastWindowClosed(False);main=Main();main.show() if '--tray' not in sys.argv else main.hide()
    if '--smoke-test' in sys.argv:
        from smoke import run
        run(main,app,Path.cwd());main.tray.hide();main.pet.hide();main.hide();sys.exit(0)
    if '--screenshot' in sys.argv:
        QTimer.singleShot(800,lambda:main.grab().save(str(ROOT/'preview.png')));QTimer.singleShot(1000,app.quit)
    sys.exit(app.exec())
