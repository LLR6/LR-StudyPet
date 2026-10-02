"""Launcher with persistent diagnostics and a friendly Windows error dialog."""
import sys, os, traceback, runpy, datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parent
DATA=Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'.local/share')))/'LR-StudyPet'
DATA.mkdir(parents=True,exist_ok=True)
LOG=DATA/'startup.log'
if __name__=='__main__':
    try:
        os.chdir(ROOT);sys.path.insert(0,str(ROOT))
        with LOG.open('a',encoding='utf-8') as f:f.write('\n'+str(datetime.datetime.now())+' launcher '+sys.version.split()[0]+'\n')
        if not (ROOT/'assets/pet.png').exists():raise FileNotFoundError('角色文件 assets/pet.png 不存在，请完整解压 Windows 包。')
        runpy.run_path(str(ROOT/'app.py'),run_name='__main__')
    except SystemExit:raise
    except Exception:
        with LOG.open('a',encoding='utf-8') as f:traceback.print_exc(file=f)
        msg='星梨启动失败。请完整解压压缩包后启动。\n\n详细日志：'+str(LOG)+'\n\n'+traceback.format_exc()[-1400:]
        print(msg)
        if sys.platform=='win32':
            import ctypes
            ctypes.windll.user32.MessageBoxW(None,msg,'LR StudyPet 启动诊断',0x10)
        sys.exit(1)
