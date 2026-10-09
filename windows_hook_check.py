"""CI-only hook check using an injected F24 down/up; never run on normal startup."""
import sys,time

def check(main,app):
    if sys.platform!='win32':return 'not-Windows'
    import ctypes
    from ctypes import wintypes as wt
    for _ in range(100):
        app.processEvents()
        if main.keyboard.running:break
        if main.keyboard.error:raise RuntimeError(main.keyboard.error)
        time.sleep(.01)
    if not main.keyboard.running:raise RuntimeError('Windows keyboard hook did not start')
    class Mouse(ctypes.Structure):
        _fields_=[('dx',wt.LONG),('dy',wt.LONG),('data',wt.DWORD),('flags',wt.DWORD),('time',wt.DWORD),('extra',ctypes.c_size_t)]
    class Key(ctypes.Structure):
        _fields_=[('vk',wt.WORD),('scan',wt.WORD),('flags',wt.DWORD),('time',wt.DWORD),('extra',ctypes.c_size_t)]
    class Union(ctypes.Union):_fields_=[('mi',Mouse),('ki',Key)]
    class Input(ctypes.Structure):_fields_=[('type',wt.DWORD),('u',Union)]
    events=(Input*2)();events[0].type=1;events[0].u.ki.vk=0x87;events[1].type=1;events[1].u.ki.vk=0x87;events[1].u.ki.flags=2
    send=ctypes.windll.user32.SendInput;send.argtypes=[wt.UINT,ctypes.POINTER(Input),ctypes.c_int];send.restype=wt.UINT
    before=main.key_count
    if send(2,events,ctypes.sizeof(Input))!=2:raise RuntimeError('F24 test injection failed')
    for _ in range(100):
        app.processEvents();main.activity_tick()
        if main.key_count>before:return 'F24 down/up observed by real Windows hook'
        time.sleep(.01)
    raise RuntimeError('Windows hook did not observe the injected key')
