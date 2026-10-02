"""Local desktop helpers. No typed characters, clipboard content or desktop names are written to disk."""
import os, sys, time, ctypes, re, json
from pathlib import Path
from collections import Counter

class ClipboardMemory:
    def __init__(self,ttl=60,now=time.monotonic):self.ttl=ttl;self.now=now;self.current=None;self.previous=None
    def clear(self):self.current=None;self.previous=None
    def expire(self):
        n=self.now()
        if self.current and n-self.current[1]>=self.ttl:self.current=None
        if self.previous and n-self.previous[1]>=self.ttl:self.previous=None
    def observe(self,text):
        self.expire()
        if not isinstance(text,str) or not text or len(text)>10000:return
        if self.current and self.current[0]==text:return
        self.previous=(self.current[0],self.now()) if self.current else None
        self.current=(text,self.now())
    def prior(self):self.expire();return self.previous[0] if self.previous else ''
    def remaining(self):self.expire();return max(0,int(self.ttl-(self.now()-self.previous[1]))) if self.previous else 0

class KeyboardActivity:
    def __init__(self):self.previous=set();self.available=sys.platform=='win32';self.error=''
    def poll(self):
        if not self.available:return 0
        try:
            # High bit only: current key state. Keep only codes held in this instant; never decode text.
            current={k for k in range(8,255) if ctypes.windll.user32.GetAsyncKeyState(k)&0x8000}
            count=len(current-self.previous);self.previous=current;return count
        except Exception as e:self.error=str(e);self.available=False;return 0
    def clear(self):self.previous.clear()

def desktop_path():
    if sys.platform=='win32':
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders') as k:
                value,_=winreg.QueryValueEx(k,'Desktop');return Path(os.path.expandvars(value))
        except OSError:pass
    return Path.home()/'Desktop'

def desktop_advice(path):
    root=Path(path)
    if not root.is_dir():raise ValueError('请选择存在的桌面目录')
    files=[];folders=0;unreadable=0
    for p in root.iterdir():
        if p.is_symlink():continue
        try:
            if p.is_dir():folders+=1;continue
            if p.is_file():
                stat=p.stat();files.append({'name':p.name,'size':stat.st_size,'mtime':stat.st_mtime,'suffix':p.suffix.lower()})
        except OSError:unreadable+=1
    groups=Counter(f['suffix'] or '无扩展名' for f in files)
    lines=[f'仅扫描一层：{len(files)} 个文件，{folders} 个文件夹。不会移动、删除或上传。']
    categories={'文档':{'.pdf','.doc','.docx','.txt','.ppt','.pptx','.xls','.xlsx'},'图片':{'.png','.jpg','.jpeg','.webp','.gif'},'安装与压缩包':{'.exe','.msi','.zip','.7z','.rar'},'代码':{'.py','.js','.ts','.cpp','.c','.html','.ipynb'}}
    for name,ext in categories.items():
        selected=[f for f in files if f['suffix'] in ext]
        if len(selected)>=3:lines.append(f'建议建「{name}」文件夹，收纳 {len(selected)} 个相关文件。')
    large=sorted((f for f in files if f['size']>=100*1024*1024),key=lambda f:-f['size'])
    for f in large[:8]:lines.append(f"大文件可优先检查：{f['name']} ({f['size']/1024/1024:.0f} MB)")
    stale=[f for f in files if time.time()-f['mtime']>30*86400 and f['suffix'] in {'.exe','.msi','.zip','.7z','.rar'}]
    if stale:lines.append(f'有 {len(stale)} 个超过 30 天未修改的安装/压缩包；确认仍需保留后再手动整理。')
    names=Counter(re.sub(r'\s*\(\d+\)$','',Path(f['name']).stem).lower()+f['suffix'] for f in files)
    similar=[n for n,c in names.items() if c>1]
    if similar:lines.append('名称相似（尚未比较内容）：'+ '、'.join(similar[:8]))
    if len(files)>30:lines.append('桌面文件较多，可以只留「当前学习」「常用快捷方式」「待归档」三个入口。')
    if not files:lines.append('桌面很整洁，继续保持就好。')
    if unreadable:lines.append(f'{unreadable} 个项目无法读取，已跳过。')
    return '\n\n'.join(lines)

COMMANDS=[
 ('Git','查看状态','git status','显示工作区和暂存区状态'),
 ('Git','查看修改','git diff','查看尚未暂存的差异'),
 ('Git','查看日志','git log --oneline -10','查看最近十条提交'),
 ('Git','查看分支','git branch --all','列出本地与远程分支'),
 ('Git','暂存指定文件','git add <file>','替换 <file> 为要暂存的文件'),
 ('Git','提交修改','git commit -m "<message>"','提交已暂存的修改，替换占位说明'),
 ('Python','创建虚拟环境','python -m venv .venv','在当前目录创建 .venv'),
 ('Python','安装依赖','python -m pip install -r requirements.txt','下载并安装依赖，修改环境'),
 ('Python','启动本地网页','python -m http.server 8000 --bind 127.0.0.1','仅在本机提供当前目录；退出用 Ctrl+C'),
 ('Python','运行单元测试','python -m unittest discover -v','发现并运行 unittest 测试'),
 ('Docker','查看容器','docker ps -a','列出所有容器'),
 ('Docker','查看日志','docker logs --tail 100 <container>','替换容器名，查看最近日志'),
 ('Docker','查看镜像','docker images','列出本地镜像'),
 ('Docker','启动服务','docker compose up -d','后台启动 Compose 服务，可能创建资源'),
 ('Docker','资源使用','docker stats --no-stream','显示一次容器资源使用情况'),
 ('Windows','查看进程','Get-Process','PowerShell：列出进程'),
 ('Windows','查看端口','Get-NetTCPConnection -State Listen','PowerShell：查看 TCP 监听端口'),
 ('Windows','查看当前文件','Get-ChildItem','PowerShell：列出当前目录'),
 ('Windows','查找文件','Get-ChildItem -Recurse -Filter "*.pdf"','PowerShell：递归查找 PDF 文件'),
 ('Windows','测试端口','Test-NetConnection <host> -Port <port>','替换主机和端口，网络连接测试'),
 ('Linux','查看监听端口','ss -lntp','查看监听 TCP 端口与进程'),
 ('Linux','查看磁盘','df -h','显示文件系统磁盘容量'),
 ('Linux','查看内存','free -h','显示内存和交换空间'),
 ('Linux','查看服务日志','journalctl -u <service> -n 100 --no-pager','替换服务名，查看最近日志'),
 ('Linux','查看服务状态','systemctl status <service> --no-pager','替换服务名，查询服务状态'),
 ('Linux','查找文本','rg "<text>" <directory>','替换查找文本与目录'),
 ('网络','请求响应头','curl -I https://<host>','向你填写的主机发送 HEAD 请求'),
 ('网络','测试域名解析','nslookup <host>','解析指定主机名'),
]
def suggest_commands(text,category='全部'):
    text=text.strip().lower()
    return [r for r in COMMANDS if (category=='全部' or r[0]==category) and (not text or text in ' '.join(r).lower())]

def startup_file():
    return Path(os.environ.get('APPDATA',str(Path.home())))/'Microsoft/Windows/Start Menu/Programs/Startup/LR-StudyPet.vbs'
def configure_startup(enabled,root,interpreter=None):
    if sys.platform!='win32':raise OSError('自启动设置仅支持 Windows')
    file=startup_file()
    if not enabled:
        if file.exists():file.unlink()
        return
    root=Path(root).resolve();exe=Path(interpreter or sys.executable).resolve();windowed=exe.with_name('pythonw.exe')
    if windowed.exists():exe=windowed
    launcher=root/'bootstrap.py'
    frozen=getattr(sys,'frozen',False)
    if not exe.exists() or (not frozen and not launcher.exists()):raise OSError('启动文件不完整，无法设置自启动')
    file.parent.mkdir(parents=True,exist_ok=True)
    # JSON quoting is not used as shell quoting. VBScript quotes are doubled explicitly.
    command=('"'+str(exe)+'" --tray') if frozen else ('"'+str(exe)+'" "'+str(launcher)+'" --tray')
    escaped=command.replace('"','""');folder=str(root).replace('"','""')
    file.write_text(f'Set sh = CreateObject("WScript.Shell")\r\nsh.CurrentDirectory = "{folder}"\r\nsh.Run "{escaped}", 0, False\r\n',encoding='utf-16')
