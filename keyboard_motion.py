"""Character reaction state contains timing and left/right taps, never typed text."""
import time

class TypingMotion:
    def __init__(self,now=time.monotonic):
        self.now=now;self.started=now();self.last=None;self.taps=[];self.side=0;self.held=False
    def press(self,count=1):
        n=self.now();self.last=n
        self.taps=[(s,t) for s,t in self.taps if n-t<0.24]
        start=max(n,self.taps[-1][1]+0.075 if self.taps else n)
        for i in range(min(6,max(1,count))):
            self.side=1-self.side;self.taps.append((self.side,min(n+0.30,start+i*0.075)))
    def clear(self):self.started=self.now();self.last=None;self.taps=[];self.held=False
    def state(self,focused=False,enabled=True,sleep_after=45):
        if not enabled:return 'focus' if focused else 'idle'
        if self.last is None:return 'sleep' if not focused and self.now()-self.started>=sleep_after else 'focus' if focused else 'idle'
        age=self.now()-self.last
        if (self.held and age<1.5) or age<0.45:return 'typing'
        if age>=sleep_after and not focused:return 'sleep'
        return 'focus' if focused else 'idle'
    def pressure(self,side):
        n=self.now();self.taps=[(s,t) for s,t in self.taps if n-t<0.24]
        values=[]
        for s,t in self.taps:
            if s==side and 0<=n-t<0.22:
                age=(n-t)/0.22;values.append(max(0,1-abs(age-0.35)/0.65))
        return max(values,default=0)
