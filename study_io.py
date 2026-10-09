"""Portable review cards and human-readable local study reports."""
import csv
import datetime as dt
from collections import Counter
from pathlib import Path


def read_cards(path, default_subject='其他'):
    if Path(path).stat().st_size > 5 * 1024 * 1024:
        raise ValueError('CSV 请保持在 5 MB 以内')
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        if not {'question', 'answer'} <= set(reader.fieldnames or []):
            raise ValueError('CSV 需要 question、answer 列，可选 subject 列')
        cards = []
        for number, row in enumerate(reader, 2):
            q, a = ((row.get(k) or '').strip() for k in ('question', 'answer'))
            subject = (row.get('subject') or default_subject).strip() or default_subject
            if not q and not a:
                continue
            if not q or not a or max(len(q), len(a)) > 20000 or len(subject) > 80:
                raise ValueError(f'第 {number} 行内容不完整或过长，未导入任何卡片')
            cards.append((q, a, subject))
            if len(cards) > 10000:
                raise ValueError('单次最多导入 10000 张卡片')
        return list(dict.fromkeys(cards))


def import_cards(store, cards):
    known = {(r['question'], r['answer'], r['subject']) for r in store.rows('reviews')}
    new = list(dict.fromkeys(tuple(c) for c in cards if tuple(c) not in known))
    with store.db:
        store.db.executemany('INSERT INTO reviews(question,answer,subject,due) VALUES(?,?,?,?)',
                             [(*c, dt.date.today().isoformat()) for c in new])
    return len(new)


def export_cards(store, path):
    with Path(path).open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['question', 'answer', 'subject'])
        for row in reversed(store.rows('reviews')):
            writer.writerow([row[k] for k in ('question', 'answer', 'subject')])


def activity_days(store, count=28, today=None):
    today = today or dt.date.today()
    totals = Counter()
    for row in store.rows('sessions'):
        totals[row['date']] += row['seconds']
    return [((today - dt.timedelta(days=i)).isoformat(), totals[(today - dt.timedelta(days=i)).isoformat()])
            for i in reversed(range(count))]


def weekly_report(store, today=None):
    today = today or dt.date.today()
    days = activity_days(store, 7, today)
    dates = {d for d, _ in days}
    sessions = [r for r in store.rows('sessions') if r['date'] in dates]
    subjects = Counter()
    for row in sessions:
        subjects[row['subject'] or '其他'] += row['seconds']
    lines = [f'# 学习周报 · {days[0][0]} 至 {days[-1][0]}', '',
             f'专注 {sum(s for _, s in days) // 60} 分钟，活跃 {sum(s > 0 for _, s in days)} 天，计时 {len(sessions)} 段。', '',
             '| 日期 | 分钟 |', '|---|---:|']
    lines += [f'| {d} | {s // 60} |' for d, s in days]
    lines += ['', '## 分科投入', '']
    lines += [f'- {subject.replace(chr(10), " ")}: {seconds // 60} 分钟' for subject, seconds in subjects.most_common()] or ['暂无专注记录。']
    due = sum(r['due'] <= today.isoformat() for r in store.rows('reviews'))
    pending = sum(not r['done'] for r in store.rows('tasks'))
    lines += ['', f'当前待完成任务 {pending} 项；到期复习卡 {due} 张。', '', '## 本周手记', '']
    for row in reversed(store.rows('journal')):
        if row['date'] in dates:
            lines += [f"{row['date']} · {row['kind']}", '', *['> ' + line for line in row['text'].splitlines()], '']
    lines += ['', '统计来自手动计时；时间不等于掌握程度。周报包含手记，分享前请检查个人内容。', '']
    return '\n'.join(lines)
