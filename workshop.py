"""Local data-only pet packs. A pack never contains executable behavior."""
import json
import re
import shutil
import tempfile
import uuid
import zipfile
from pathlib import Path

STATES={'idle':'待机','typing':'打字','sleep':'睡觉','focus':'读书 / 专注','celebrate':'庆祝','rest':'休息','pat':'摸头'}
MAX_FILE=8*1024*1024


def validate_metadata(data):
    if not isinstance(data,dict) or data.get('schema')!=1:raise ValueError('角色包需要 schema=1')
    for key in ('name','author','license'):
        if not isinstance(data.get(key),str) or not 1<=len(data[key].strip())<=120:raise ValueError('请填写角色名称、作者和素材许可（每项 1～120 字）')
    states=data.get('states')
    if not isinstance(states,dict) or 'idle' not in states or not set(states)<=set(STATES):raise ValueError('至少需要 idle 待机素材，动作名称必须符合模板')
    for state,file in states.items():
        if not isinstance(file,str) or not re.fullmatch(r'[a-zA-Z0-9_-]+\.(png|gif|webp)',file):raise ValueError('素材文件名只支持英文、数字、连字符和 PNG/GIF/WebP 扩展名')
    if not isinstance(data.get('keyboard_overlay',True),bool):raise ValueError('keyboard_overlay 必须为 true 或 false')
    return data


def validate_image(path):
    from PySide6.QtGui import QImageReader
    path=Path(path)
    if path.is_symlink() or not path.is_file() or not 0<path.stat().st_size<=MAX_FILE:raise ValueError('素材缺失或超过 8 MB：'+path.name)
    reader=QImageReader(str(path));size=reader.size()
    if not size.isValid() or max(size.width(),size.height())>2048:raise ValueError('素材必须是有效图片，最长边不超过 2048 像素：'+path.name)
    if reader.imageCount()>240:raise ValueError('单段动图最多 240 帧：'+path.name)
    if reader.read().isNull():raise ValueError('无法读取素材：'+path.name)


def load_pack(folder):
    folder=Path(folder)
    if folder.is_symlink():raise ValueError('角色目录不能是符号链接')
    manifest=folder/'pet.json'
    if manifest.is_symlink() or manifest.stat().st_size>32000:raise ValueError('配置文件无效或过大')
    data=validate_metadata(json.loads(manifest.read_text(encoding='utf-8')))
    for file in set(data['states'].values()):validate_image(folder/file)
    return data


def install_pack(archive,library):
    archive=Path(archive);library=Path(library)
    if archive.stat().st_size>64*1024*1024:raise ValueError('角色包最多 64 MB')
    library.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=library) as temporary:
        temp=Path(temporary)
        with zipfile.ZipFile(archive) as pack:
            members=pack.infolist()
            if len(members)>20 or sum(m.file_size for m in members)>64*1024*1024:raise ValueError('角色包文件过多或解压后过大')
            names=[m.filename for m in members]
            if len(names)!=len(set(names)) or 'pet.json' not in names:raise ValueError('包根目录需要唯一的 pet.json')
            for member in members:
                if member.filename=='pet.json':
                    if member.file_size>32000:raise ValueError('配置文件过大')
                elif not re.fullmatch(r'[a-zA-Z0-9_-]+\.(png|gif|webp)',member.filename):raise ValueError('包中只允许配置与图片，不允许目录或程序')
                if member.file_size>MAX_FILE or ((member.external_attr>>16)&0o170000)==0o120000:raise ValueError('素材过大或包含符号链接')
                (temp/member.filename).write_bytes(pack.read(member))
        data=load_pack(temp)
        if set(names)!={'pet.json',*data['states'].values()}:raise ValueError('包中有未引用的文件，请删去后再导入')
        ident=uuid.uuid4().hex;target=library/ident
        temp.rename(target)
    return ident,data


def make_pack(path,name,author,license_text,sources,keyboard_overlay=True):
    states={state:state+Path(file).suffix.lower() for state,file in sources.items() if file}
    data=validate_metadata({'schema':1,'name':name.strip(),'author':author.strip(),'license':license_text.strip(),'keyboard_overlay':keyboard_overlay,'states':states})
    for state,file in sources.items():
        if file:
            if Path(file).suffix.lower() not in ('.png','.gif','.webp'):raise ValueError('仅支持 PNG/GIF/WebP')
            validate_image(file)
    with tempfile.TemporaryDirectory() as folder:
        temp=Path(folder)/'package.lrpet'
        with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED) as pack:
            pack.writestr('pet.json',json.dumps(data,ensure_ascii=False,indent=2))
            for state,file in sources.items():
                if file:pack.write(file,states[state])
        # Commit the output only after every source has been checked and the archive is complete.
        Path(path).write_bytes(temp.read_bytes())
    return data


def export_pack(folder,path):
    folder=Path(folder);data=load_pack(folder)
    sources={state:folder/file for state,file in data['states'].items()}
    return make_pack(path,data['name'],data['author'],data['license'],sources,data.get('keyboard_overlay',True))


def list_packs(library):
    library=Path(library);library.mkdir(parents=True,exist_ok=True)
    result=[]
    for folder in sorted(library.iterdir()):
        if re.fullmatch(r'[0-9a-f]{32}',folder.name):
            try:result.append((folder.name,load_pack(folder)))
            except (OSError,ValueError,TypeError):continue
    return result
