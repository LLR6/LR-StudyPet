"""Windows event hook: aggregate presses/held-state only; no key names or text leave this module."""
import sys
import threading

class KeyboardListener:
    def __init__(self):
        self.available=sys.platform=='win32';self.error='';self.running=False
        self.thread=None;self.thread_id=0;self.lock=threading.Lock();self.count=0;self.held=False
        self.ready=threading.Event();self.stopping=threading.Event()
    def start(self):
        if not self.available or (self.thread and self.thread.is_alive()):return
        self.stopping.clear();self.ready.clear();self.thread=threading.Thread(target=self._run,daemon=True);self.thread.start()
    def poll(self):
        with self.lock:
            count=self.count;self.count=0;return count
    def clear(self):
        with self.lock:self.count=0;self.held=False
    def stop(self):
        self.stopping.set()
        if self.thread and self.thread.is_alive():
            self.ready.wait(0.3)
            if self.thread_id:
                import ctypes
                ctypes.windll.user32.PostThreadMessageW(self.thread_id,0x0012,0,0)
            self.thread.join(timeout=0.5)
        self.clear()
    def _run(self):
        import ctypes
        from ctypes import wintypes as wt
        user=ctypes.WinDLL('user32',use_last_error=True);kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        callback_type=ctypes.WINFUNCTYPE(ctypes.c_ssize_t,ctypes.c_int,wt.WPARAM,wt.LPARAM)
        class Key(ctypes.Structure):
            _fields_=[('vkCode',wt.DWORD),('scanCode',wt.DWORD),('flags',wt.DWORD),('time',wt.DWORD),('extra',ctypes.c_size_t)]
        user.SetWindowsHookExW.argtypes=[ctypes.c_int,callback_type,wt.HINSTANCE,wt.DWORD];user.SetWindowsHookExW.restype=wt.HANDLE
        user.CallNextHookEx.argtypes=[wt.HANDLE,ctypes.c_int,wt.WPARAM,wt.LPARAM];user.CallNextHookEx.restype=ctypes.c_ssize_t
        user.UnhookWindowsHookEx.argtypes=[wt.HANDLE];user.UnhookWindowsHookEx.restype=wt.BOOL
        user.GetMessageW.argtypes=[ctypes.POINTER(wt.MSG),wt.HWND,wt.UINT,wt.UINT];user.GetMessageW.restype=ctypes.c_int
        user.PeekMessageW.argtypes=[ctypes.POINTER(wt.MSG),wt.HWND,wt.UINT,wt.UINT,wt.UINT];user.PeekMessageW.restype=wt.BOOL
        kernel.GetModuleHandleW.argtypes=[wt.LPCWSTR];kernel.GetModuleHandleW.restype=wt.HMODULE
        kernel.GetCurrentThreadId.restype=wt.DWORD
        held=set();modifiers={16,17,18,20,91,92,160,161,162,163,164,165}
        hook=None
        def on_event(code,wparam,lparam):
            if code>=0:
                key=ctypes.cast(lparam,ctypes.POINTER(Key)).contents.vkCode
                if key not in modifiers:
                    if wparam in (0x0100,0x0104):
                        held.add(key)
                        with self.lock:self.count+=1;self.held=True
                    elif wparam in (0x0101,0x0105):
                        held.discard(key)
                        with self.lock:self.held=bool(held)
            return user.CallNextHookEx(hook,code,wparam,lparam)
        callback=callback_type(on_event)
        try:
            self.thread_id=kernel.GetCurrentThreadId();message=wt.MSG();user.PeekMessageW(ctypes.byref(message),None,0,0,0)
            hook=user.SetWindowsHookExW(13,callback,kernel.GetModuleHandleW(None),0)
            if not hook:raise ctypes.WinError(ctypes.get_last_error())
            self.running=True;self.ready.set()
            while not self.stopping.is_set():
                result=user.GetMessageW(ctypes.byref(message),None,0,0)
                if result==0:break
                if result==-1:raise ctypes.WinError(ctypes.get_last_error())
                user.TranslateMessage(ctypes.byref(message));user.DispatchMessageW(ctypes.byref(message))
        except Exception as e:self.error=str(e);self.available=False;self.ready.set()
        finally:
            if hook:user.UnhookWindowsHookEx(hook)
            held.clear();self.running=False;self.thread_id=0;self.clear()
