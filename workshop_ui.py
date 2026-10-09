from pathlib import Path
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap,QMovie,QImageReader
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QListWidget,
    QListWidgetItem,QComboBox,QFileDialog,QMessageBox,QLineEdit,QCheckBox,QFormLayout,QScrollArea,QApplication)
from workshop import STATES,list_packs,install_pack,export_pack,make_pack,load_pack,validate_image

class Workshop(QWidget):
    def __init__(self,main,library):
        super().__init__();self.main=main;self.library=Path(library);self.movie=None;self.sources={};self.source_labels={}
        layout=QHBoxLayout(self);left=QVBoxLayout();right=QVBoxLayout();layout.addLayout(left,1);layout.addLayout(right,2)
        left.addWidget(QLabel('本地创意工坊 · 做一只自己的桌宠'))
        self.items=QListWidget();self.items.currentItemChanged.connect(self.preview);left.addWidget(self.items)
        for title,fn in [('导入角色包 (.lrpet / .zip)',self.import_file),('应用选中角色',self.apply_selected),('导出选中角色包',self.export_selected),('恢复默认星梨',self.default),('导出星梨制作模板',self.template)]:
            b=QPushButton(title);b.clicked.connect(fn);left.addWidget(b)
        self.info=QLabel('角色包只包含图片和配置，安装后保存在本机。');self.info.setWordWrap(True);self.info.setTextFormat(Qt.PlainText);left.addWidget(self.info)
        self.image=QLabel('选择左侧角色进行预览');self.image.setAlignment(Qt.AlignCenter);self.image.setMinimumSize(260,190);self.image.setStyleSheet('background:#e8f3fd;border-radius:12px');right.addWidget(self.image)
        row=QHBoxLayout();self.state=QComboBox()
        for state,title in STATES.items():self.state.addItem(title,state)
        self.state.currentIndexChanged.connect(self.preview);row.addWidget(self.state)
        b=QPushButton('模拟敲键体验');b.clicked.connect(self.simulate);row.addWidget(b);right.addLayout(row)
        form=QWidget();fields=QFormLayout(form);self.name=QLineEdit();self.name.setPlaceholderText('例如：我的小蓝猫');self.author=QLineEdit();self.author.setPlaceholderText('作者 / 昵称');self.license=QLineEdit();self.license.setPlaceholderText('例如：原创，仅个人使用 / CC BY 4.0')
        fields.addRow('角色名称',self.name);fields.addRow('作者',self.author);fields.addRow('素材许可',self.license)
        for state,title in STATES.items():
            row=QHBoxLayout();text=QLabel('未选择' if state!='idle' else '必须选择');text.setTextFormat(Qt.PlainText);self.source_labels[state]=text;row.addWidget(text,1)
            b=QPushButton('选 PNG / GIF');b.clicked.connect(lambda checked=False,s=state:self.choose_image(s));row.addWidget(b);clear=QPushButton('清除');clear.clicked.connect(lambda checked=False,s=state:self.clear_image(s));row.addWidget(clear);fields.addRow(title,row)
        self.overlay=QCheckBox('打字时叠加双手与键盘（已有完整打字 GIF 可取消）');self.overlay.setChecked(True);fields.addRow(self.overlay)
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(form);right.addWidget(scroll,1)
        row=QHBoxLayout();b=QPushButton('制作并安装角色');b.clicked.connect(self.create);row.addWidget(b);b=QPushButton('复制画图提示词');b.clicked.connect(self.prompt);row.addWidget(b);right.addLayout(row)
        self.hint=QLabel('至少一张待机图即可制作；可选动作缺失时回退到待机。透明 PNG 最方便，GIF 可直接播放。单张图不会自动变成完整多姿态动画。');self.hint.setWordWrap(True);right.addWidget(self.hint);self.refresh()
    def refresh(self,select=None):
        self.items.clear()
        for ident,data in list_packs(self.library):
            item=QListWidgetItem(data['name']);item.setData(Qt.UserRole,ident);self.items.addItem(item)
            if ident==select:self.items.setCurrentItem(item)
    def selected(self):
        item=self.items.currentItem();return self.library/item.data(Qt.UserRole) if item else None
    def preview(self,*args):
        folder=self.selected()
        if self.movie:self.movie.stop();self.movie=None
        self.image.clear()
        if not folder:self.image.setText('导入或制作一个角色，再选择动作预览。');return
        try:
            data=load_pack(folder);state=self.state.currentData();file=data['states'].get(state,data['states']['idle']);path=folder/file
            self.info.setText(data['name']+'\n作者：'+data['author']+'\n素材许可：'+data['license'])
            if QImageReader(str(path)).supportsAnimation():
                self.movie=QMovie(str(path));self.movie.setScaledSize(QPixmap(str(path)).size().scaled(230,190,Qt.KeepAspectRatio));self.image.setMovie(self.movie);self.movie.start()
            else:self.image.setPixmap(QPixmap(str(path)).scaled(230,190,Qt.KeepAspectRatio,Qt.SmoothTransformation))
        except Exception as e:self.info.setText('角色不可用：'+str(e))
    def import_file(self):
        path,_=QFileDialog.getOpenFileName(self,'导入角色包','','角色包 (*.lrpet *.zip)')
        if path:
            try:ident,data=install_pack(path,self.library);self.refresh(ident);self.info.setText('已导入 '+data['name']+'。点应用后切换桌宠。')
            except Exception as e:QMessageBox.warning(self,'导入失败',str(e))
    def apply_selected(self):
        folder=self.selected()
        if folder:
            try:self.main.pet.apply_skin(folder);self.main.store.set('active_skin',folder.name);self.main.pet.say('新角色已到桌面，一起开始吧。')
            except Exception as e:QMessageBox.warning(self,'角色不可用',str(e))
    def default(self):self.main.pet.apply_skin(None);self.main.store.set('active_skin',None);self.main.pet.say('星梨回来啦。')
    def simulate(self):
        self.main.pet.show();self.main.pet.typing(4);self.main.pet.say('这是模拟敲键预览。实际联动请在桌面助手中开启。')
    def export_selected(self):
        folder=self.selected()
        if not folder:return
        path,_=QFileDialog.getSaveFileName(self,'导出角色包','my-pet.lrpet','角色包 (*.lrpet)')
        if path:
            try:export_pack(folder,path);self.info.setText('已导出，可发给朋友导入。请确认素材许可允许分享。')
            except Exception as e:QMessageBox.warning(self,'导出失败',str(e))
    def template(self):
        path,_=QFileDialog.getSaveFileName(self,'导出星梨制作模板','xingli-template.lrpet','角色包 (*.lrpet)')
        if path:
            try:self.main.pet.export_template(path);self.info.setText('模板已导出。它是 ZIP 格式，解压后替换素材，再压缩根目录中的配置与图片。')
            except Exception as e:QMessageBox.warning(self,'导出失败',str(e))
    def choose_image(self,state):
        path,_=QFileDialog.getOpenFileName(self,'选择 '+STATES[state]+' 素材','','图片 (*.png *.gif *.webp)')
        if path:
            try:
                validate_image(path);self.sources[state]=path;self.source_labels[state].setText(Path(path).name)
                if self.movie:self.movie.stop();self.movie=None
                if QImageReader(path).supportsAnimation():
                    self.movie=QMovie(path);self.movie.setScaledSize(QPixmap(path).size().scaled(230,190,Qt.KeepAspectRatio));self.image.setMovie(self.movie);self.movie.start()
                else:self.image.setPixmap(QPixmap(path).scaled(230,190,Qt.KeepAspectRatio,Qt.SmoothTransformation))
                self.info.setText('制作中素材预览：'+STATES[state]+'。填写名称、作者和许可后即可安装。')
            except Exception as e:QMessageBox.warning(self,'素材不可用',str(e))
    def clear_image(self,state):self.sources.pop(state,None);self.source_labels[state].setText('必须选择' if state=='idle' else '未选择')
    def create(self):
        import tempfile
        try:
            with tempfile.TemporaryDirectory() as folder:
                archive=Path(folder)/'pet.lrpet';make_pack(archive,self.name.text(),self.author.text(),self.license.text(),self.sources,self.overlay.isChecked());ident,data=install_pack(archive,self.library)
            self.refresh(ident);self.info.setText('制作完成。点“应用选中角色”放到桌面；也可导出分享。')
        except Exception as e:QMessageBox.warning(self,'制作失败',str(e))
    def prompt(self):
        name=self.name.text().strip() or '原创浅蓝色可爱角色'
        text=f'绘制{name}的透明背景桌宠素材。主体完整、正面或三分之二侧面、无文字、无场景，512×512。分别制作同一造型的待机、打字、睡觉、读书、庆祝、休息、摸头七种动作，每个动作单独保存 PNG；需要连续动画时逐帧绘制并导出 GIF。角色尺寸与位置保持一致，不裁切四肢。'
        QApplication.instance().clipboard().setText(text);self.hint.setText('提示词已复制。用你自己的绘图工具制作素材后，回到本页选择图片；本按钮不联网生成图片。')
