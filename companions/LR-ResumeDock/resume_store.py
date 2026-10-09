import datetime as dt
import sqlite3
from pathlib import Path

class DockStore:
    def __init__(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS bookmarks (
          id INTEGER PRIMARY KEY, title TEXT NOT NULL, context TEXT NOT NULL,
          next_step TEXT NOT NULL, resource TEXT NOT NULL, archived INTEGER DEFAULT 0,
          updated TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events (
          id INTEGER PRIMARY KEY, bookmark_id INTEGER, seconds INTEGER, created TEXT);
        ''')
        self.db.commit()
    def save(self, ident, title, context, next_step, resource=''):
        if not title.strip() or not next_step.strip():
            raise ValueError('请填写项目名和回来后的第一步')
        values = (title.strip(), context.strip(), next_step.strip(), resource.strip(), dt.datetime.now().isoformat(timespec='seconds'))
        with self.db:
            if ident is None:
                cur = self.db.execute('INSERT INTO bookmarks(title,context,next_step,resource,updated) VALUES(?,?,?,?,?)', values)
                return cur.lastrowid
            if not self.db.execute('SELECT id FROM bookmarks WHERE id=?', (ident,)).fetchone():
                raise ValueError('书签已不存在')
            self.db.execute('UPDATE bookmarks SET title=?,context=?,next_step=?,resource=?,updated=? WHERE id=?', (*values, ident))
        return ident
    def rows(self, archived=False):
        return [dict(r) for r in self.db.execute('SELECT * FROM bookmarks WHERE archived=? ORDER BY updated DESC,id DESC', (int(archived),))]
    def archive(self, ident, value=True):
        with self.db:
            self.db.execute('UPDATE bookmarks SET archived=? WHERE id=?', (int(value), ident))
    def record(self, ident, seconds):
        if seconds > 0:
            with self.db:
                self.db.execute('INSERT INTO events(bookmark_id,seconds,created) VALUES(?,?,?)', (ident, int(seconds), dt.datetime.now().isoformat(timespec='seconds')))
    def report(self):
        lines = ['# ResumeDock · 工作续接书签', '', '导出包含本地书签，分享前检查个人内容。', '']
        for row in self.rows():
            seconds = self.db.execute('SELECT COALESCE(SUM(seconds),0) FROM events WHERE bookmark_id=?', (row['id'],)).fetchone()[0]
            lines += ['## ' + row['title'].replace('\n', ' '), '', '做到这里：', '', row['context'], '', '回来第一步：', '', row['next_step'], '', '资料：' + row['resource'], '', f'累计主动计时：{seconds // 60} 分钟', '']
        return '\n'.join(lines)
