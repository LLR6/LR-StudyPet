"""Generate UI previews using isolated sample data, never the user's database."""
import os
from PIL import Image
import tempfile
from pathlib import Path
with tempfile.TemporaryDirectory() as folder:
    os.environ['LOCALAPPDATA']=folder
    import datetime as dt
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    from app import Main,STYLE
    app=QApplication([]);app.setStyleSheet(STYLE);main=Main()
    main.store.set('custom_subjects',['科研','写作','英语','408'])
    main.store.task('给文章的第二张图补说明','科研',25)
    main.store.review('如何确认结论有证据？','区分观察到的事实与尚未验证的推断。','科研')
    for i in range(21):
        if i%4==0:continue
        day=(dt.date.today()-dt.timedelta(days=i)).isoformat()
        main.store.db.execute('INSERT INTO sessions(date,subject,seconds,note) VALUES(?,?,?,?)',(day,['科研','写作','英语'][i%3],(15+(i*17)%100)*60,'演示数据'))
    main.store.db.commit();main.resume_note.setText('图 1 已说明；回来先补图 2 的解释。');main.update_subjects();main.refresh();main.show();app.processEvents()
    main.grab().save('preview.png')
    frames=[Image.open('preview.png')]
    main.tabs.setCurrentIndex(5);app.processEvents();main.grab().save('docs/growth-preview.png');frames.append(Image.open('docs/growth-preview.png'))
    main.tabs.setCurrentIndex(8);app.processEvents();main.grab().save('docs/toolbox-preview.png');frames.append(Image.open('docs/toolbox-preview.png'))
    frames[0].save('docs/demo.gif',save_all=True,append_images=frames[1:],duration=2400,loop=0)
    pet_frames=[]
    main.pet.setFixedSize(230,310);main.pet.say('演示：你打字，我也陪着打字。')
    for i in range(12):
        main.pet.typing();main.pet.animate();app.processEvents()
        frame=Path(folder)/'pet.png';main.pet.grab().save(str(frame));pet_frames.append(Image.open(frame).copy())
    pet_frames[0].save('docs/pet-demo.gif',save_all=True,append_images=pet_frames[1:],duration=100,loop=0,disposal=2)
    main.tray.hide();main.pet.hide();main.store.db.close();main.hide()
