import sqlite3, json, datetime, time
from pathlib import Path

def day(): return datetime.date.today().isoformat()

class Store:
    def __init__(self, path):
        self.path = Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY, title TEXT NOT NULL, subject TEXT, minutes INTEGER, done INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS sessions(id INTEGER PRIMARY KEY, date TEXT, subject TEXT, seconds INTEGER, note TEXT);
        CREATE TABLE IF NOT EXISTS reviews(id INTEGER PRIMARY KEY, question TEXT, answer TEXT, subject TEXT, due TEXT, interval INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS journal(id INTEGER PRIMARY KEY, date TEXT, kind TEXT, text TEXT);
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
        '''); self.db.commit()
    def rows(self, table):
        if table not in ('tasks','sessions','reviews','journal'): raise ValueError('table')
        return [dict(r) for r in self.db.execute(f'SELECT * FROM {table} ORDER BY id DESC')]
    def get(self, key, default=None):
        r=self.db.execute('SELECT value FROM settings WHERE key=?',(key,)).fetchone()
        return json.loads(r[0]) if r else default
    def set(self, key, value):
        self.db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)',(key,json.dumps(value,ensure_ascii=False))); self.db.commit()
    def task(self,title,subject,minutes):
        title=title.strip()
        if not title: raise ValueError('任务不能为空')
        if not 1<=minutes<=240: raise ValueError('时长应为 1～240 分钟')
        self.db.execute('INSERT INTO tasks(title,subject,minutes) VALUES(?,?,?)',(title,subject,minutes));self.db.commit()
    def done(self, ident):
        self.db.execute('UPDATE tasks SET done=1-done WHERE id=?',(ident,));self.db.commit()
    def session(self,subject,seconds,note):
        if seconds<=0:return
        self.db.execute('INSERT INTO sessions(date,subject,seconds,note) VALUES(?,?,?,?)',(day(),subject,int(seconds),note));self.db.commit()
    def journal(self,kind,text):
        if text.strip():
            self.db.execute('INSERT INTO journal(date,kind,text) VALUES(?,?,?)',(day(),kind,text.strip()));self.db.commit()
    def review(self,q,a,subject):
        if not q.strip() or not a.strip():raise ValueError('问题和答案都要填写')
        self.db.execute('INSERT INTO reviews(question,answer,subject,due) VALUES(?,?,?,?)',(q.strip(),a.strip(),subject,day()));self.db.commit()
    def grade(self,ident,grade):
        r=self.db.execute('SELECT interval FROM reviews WHERE id=?',(ident,)).fetchone()
        if not r: return
        old=r[0]; interval=1 if grade==0 else max(2,old*2) if grade==1 else max(4,old*3)
        due=(datetime.date.today()+datetime.timedelta(days=min(interval,365))).isoformat()
        self.db.execute('UPDATE reviews SET interval=?,due=? WHERE id=?',(interval,due,ident));self.db.commit()
    def today_seconds(self):return sum(r['seconds'] for r in self.rows('sessions') if r['date']==day())
    def xp(self):return sum(r['seconds']//60 for r in self.rows('sessions'))+10*sum(r['done'] for r in self.rows('tasks'))
    def recommend(self,energy):
        due=[r for r in self.rows('reviews') if r['due']<=day()]
        pending=[r for r in self.rows('tasks') if not r['done']]
        if energy=='低':pending.sort(key=lambda r:r['minutes'])
        else:pending.sort(key=lambda r:(sum(s['seconds'] for s in self.rows('sessions') if s['subject']==r['subject'] and s['date']==day()),r['minutes']))
        text=f'今天有 {len(due)} 张到期复习卡。'
        if pending:
            r=pending[0];text+=f" 下一步做「{r['title']}」，{r['subject']} {min(r['minutes'],15) if energy=='低' else r['minutes']} 分钟。"
        else:text+=' 先添加一个能在一段时间内完成的小任务。'
        return text
    def export(self,path):
        data={t:self.rows(t) for t in ('tasks','sessions','reviews','journal')};data['schema']=1
        Path(path).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    def restore(self,path):
        data=json.loads(Path(path).read_text(encoding='utf-8'))
        if data.get('schema')!=1:raise ValueError('不支持的备份格式')
        columns={'tasks':['id','title','subject','minutes','done'],'sessions':['id','date','subject','seconds','note'],'reviews':['id','question','answer','subject','due','interval'],'journal':['id','date','kind','text']}
        for t,cols in columns.items():
            if not isinstance(data.get(t),list):raise ValueError('备份缺少表 '+t)
            for row in data[t]:
                if set(row)!=set(cols):raise ValueError('备份字段不匹配')
                if not isinstance(row['id'],int):raise ValueError('记录编号错误')
        # One transaction: a malformed row must never destroy the current backup.
        with self.db:
            for t,cols in columns.items():
                self.db.execute(f'DELETE FROM {t}')
                for row in data[t]:self.db.execute(f"INSERT INTO {t}({','.join(cols)}) VALUES({','.join('?' for _ in cols)})",tuple(row[c] for c in cols))

class FocusClock:
    def __init__(self,now=time.monotonic):self.now=now;self.mode='idle';self.duration=0;self.elapsed=0;self.anchor=now()
    def start(self,minutes,mode='focus'):
        self.mode=mode;self.duration=minutes*60;self.elapsed=0;self.anchor=self.now()
    def tick(self):
        if self.mode in ('focus','break'):
            n=self.now();self.elapsed+=max(0,n-self.anchor);self.anchor=n
        return max(0,self.duration-self.elapsed)
    def pause(self):
        self.tick()
        if self.mode in ('focus','break'):self.previous=self.mode;self.mode='paused'
    def resume(self):
        if self.mode=='paused':self.mode=self.previous;self.anchor=self.now()
    def reset(self):self.mode='idle';self.elapsed=0;self.duration=0
