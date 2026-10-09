"""Preview, no-clobber moves and journalled undo, scoped to one directory."""
import hashlib
import json
import os
import uuid
from collections import Counter
from pathlib import Path

CATEGORIES = {
    'Documents': {'.pdf','.doc','.docx','.txt','.ppt','.pptx','.xls','.xlsx','.md','.csv'},
    'Images': {'.png','.jpg','.jpeg','.webp','.gif','.svg','.heic'},
    'Archives': {'.zip','.7z','.rar','.tar','.gz'},
    'Media': {'.mp4','.mkv','.mp3','.wav','.mov','.flac'},
}
LIMIT = 128 * 1024 * 1024


def digest(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > LIMIT:
        raise ValueError('文件不可用、是链接或超过 128 MB：'+path.name)
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def preview(root):
    root=Path(root).resolve(strict=True)
    if not root.is_dir():raise ValueError('请选择目录')
    items=[];skipped=[];reserved=set()
    for source in sorted(root.iterdir()):
        if source.is_symlink() or not source.is_file() or source.name.startswith('.'):
            continue
        category=next((name for name,ext in CATEGORIES.items() if source.suffix.lower() in ext),None)
        if not category:continue
        try:
            fingerprint=digest(source)
            destination=root/category/source.name
            index=1
            while destination.exists() or destination.is_symlink() or str(destination).casefold() in reserved:
                destination=root/category/f'{source.stem} ({index}){source.suffix}';index+=1
            reserved.add(str(destination).casefold())
            items.append({'source':source.name,'destination':destination.relative_to(root).as_posix(),
                          'sha256':fingerprint,'size':source.stat().st_size})
            if len(items)>=500:
                skipped.append('已达 500 文件预览上限；整理后可重新扫描。');break
        except (OSError,ValueError) as e:skipped.append(str(e))
    counts=Counter(row['sha256'] for row in items)
    for row in items:row['same_content']=counts[row['sha256']]>1
    return {'schema':1,'root':str(root),'items':items,'skipped':skipped}


def scoped(root, relative):
    relative=Path(relative)
    if relative.is_absolute() or '..' in relative.parts or not relative.parts:
        raise ValueError('路径超出所选目录')
    path=root/relative
    for part in [path,*path.parents]:
        if part==root:break
        if part.is_symlink():raise ValueError('跳过符号链接路径：'+str(relative))
    if not path.resolve().is_relative_to(root):raise ValueError('路径超出所选目录')
    return path


def move_no_clobber(source,destination):
    if destination.exists() or destination.is_symlink():raise FileExistsError('目标已存在：'+str(destination))
    if os.name=='nt':
        os.rename(source,destination)  # Windows rename refuses an existing destination.
    else:
        os.link(source,destination,follow_symlinks=False)
        try:source.unlink()
        except OSError:
            destination.unlink();raise


def save_journal(path,data):
    temporary=path.with_suffix('.tmp')
    with temporary.open('w',encoding='utf-8') as stream:
        json.dump(data,stream,ensure_ascii=False,indent=2);stream.flush();os.fsync(stream.fileno())
    os.replace(temporary,path)


def validate_plan(plan):
    if plan.get('schema')!=1 or not isinstance(plan.get('items'),list):raise ValueError('无效计划')
    root=Path(plan['root'])
    if root.is_symlink() or not root.is_dir() or root!=root.resolve():raise ValueError('根目录已变化')
    for row in plan['items']:
        src=scoped(root,row['source']);dest=scoped(root,row['destination'])
        if src.parent!=root or len(Path(row['destination']).parts)!=2 or dest.parent.name not in CATEGORIES:
            raise ValueError('计划只支持当前目录到分类文件夹')
        if digest(src)!=row['sha256']:raise ValueError('预览后文件已变化，请重新扫描：'+src.name)
        if dest.exists() or dest.is_symlink():raise FileExistsError('目标已存在，请重新扫描：'+str(dest))
        if dest.parent.exists() and not dest.parent.is_dir():raise ValueError('分类目录被同名文件占用')
    return root


def apply(plan):
    root=validate_plan(plan)
    if not plan['items']:raise ValueError('没有选中的文件')
    history=root/'.lr-desktidy'
    if history.is_symlink():raise ValueError('历史目录不能是符号链接')
    history.mkdir(exist_ok=True)
    journal=history/(uuid.uuid4().hex+'.json')
    data={'schema':1,'root':str(root),'operations':[]}
    save_journal(journal,data)
    try:
        for row in plan['items']:
            source=scoped(root,row['source']);destination=scoped(root,row['destination'])
            if digest(source)!=row['sha256']:raise ValueError('执行前文件已变化：'+source.name)
            destination.parent.mkdir(exist_ok=True)
            destination=scoped(root,row['destination'])
            op={**row,'status':'pending'};data['operations'].append(op);save_journal(journal,data)
            move_no_clobber(source,destination)
            op['status']='moved';save_journal(journal,data)
    except Exception as e:
        data['error']=str(e);save_journal(journal,data)
        raise RuntimeError(f'整理部分完成，可撤销。历史文件：{journal}\n{e}') from e
    return journal


def undo(journal):
    journal=Path(journal)
    data=json.loads(journal.read_text(encoding='utf-8'))
    if data.get('schema')!=1:raise ValueError('不支持的历史格式')
    root=Path(data['root'])
    if root.is_symlink() or root!=root.resolve() or not root.is_dir():raise ValueError('原目录不存在或已变化')
    if journal.resolve().parent!=root/'.lr-desktidy':raise ValueError('历史文件不属于该目录')
    results=[]
    for op in reversed(data['operations']):
        if op['status']=='undone':continue
        try:
            source=scoped(root,op['source']);destination=scoped(root,op['destination'])
            if len(Path(op['source']).parts)!=1 or len(Path(op['destination']).parts)!=2 or destination.parent.name not in CATEGORIES:
                raise ValueError('不支持的历史路径')
            if source.exists() and not destination.exists() and digest(source)==op['sha256']:
                op['status']='undone';save_journal(journal,data);continue
            if source.exists() or source.is_symlink():
                # Recover a process stop between POSIX link and unlink without losing either copy.
                if op['status']=='pending' and destination.exists() and os.path.samefile(source,destination) and digest(source)==op['sha256']:
                    destination.unlink();op['status']='undone';save_journal(journal,data);continue
                raise FileExistsError('原位置已被占用，保留整理后的文件')
            if digest(destination)!=op['sha256']:raise ValueError('整理后文件已修改，保留当前文件')
            move_no_clobber(destination,source)
            op['status']='undone';save_journal(journal,data);results.append('已恢复：'+op['source'])
        except (OSError,ValueError) as e:results.append('跳过 '+op['source']+'：'+str(e))
    return results


def latest_journal(root):
    history=Path(root).resolve()/'.lr-desktidy'
    if history.is_symlink():raise ValueError('历史目录不能是链接')
    files=sorted(history.glob('*.json'),key=lambda p:p.stat().st_mtime_ns,reverse=True)
    for file in files:
        if file.is_symlink():continue
        data=json.loads(file.read_text(encoding='utf-8'))
        if any(op['status']!='undone' for op in data.get('operations',[])):return file
    return None
