import json
import time
import logging
import threading
import fileinput
import asyncio

import keyboard

class AsyncInputEventMonitor():
    '''Async wrapper for `keyboard` module.'''
    def __init__(self):
        self.log = logging.getLogger("InputMonitor")
        self.loop = asyncio.get_event_loop()
        self.kdb_thread_active = True
        self.lock=threading.Lock()  # asyncio.Queue is *not* thread-safe
        self.que=asyncio.Queue()
        self.kbd_event_thread = threading.Thread(
            target=self.background_thread, args=())
        self.kbd_event_thread.setDaemon(True)
        self.kbd_event_thread.start()
        
    def send_event_json(self, event):
        self.que_event(event)

    def que_event(self, event):
        line = ', '.join(str(code) for code in keyboard._pressed_events)
        try:
            self.lock.acquire()
            self.que.put_nowait(line)
        except Exception as e:
            self.log.warning(f"Putting event into queue failed: {e}")
        finally:
            self.lock.release()

    def background_thread(self):
        keyboard.hook(self.que_event)
        keyboard.wait()

    async def input(self):
        ev = None
        while ev is None:
            self.lock.acquire()
            try:
                ev = self.que.get_nowait()
                self.lock.release()
                self.que.task_done()
            except asyncio.QueueEmpty:
                self.lock.release()
                ev=None
                await asyncio.sleep(0.1)
        xev={'cmd': 'input',
            'ev': ev}
        return xev

class AsyncKeyboardPresence():
    '''Generates a presence state by monitoring keyboard events.
    
    Considers presence state `away` if no input events for `timeout` seconds. Generate
    a presence event at least every `refresh_time` seconds, even if state hasn't changed.'''
    def __init__(self, timeout=300, refresh_time=60):
        self.log = logging.getLogger("KeyboardPresence")
        self.input_event_timeout=timeout
        self.input_events=AsyncInputEventMonitor()
        self.state=False
        self.last_time=0
        if refresh_time is not None and refresh_time!=0:
            self.refresh_time=refresh_time
        else:
            self.refresh_time=365*24*3600  # [once a year is almost never]

    async def presence(self):
        state_change=False
        while state_change is False:
            try:
                await asyncio.wait_for(self.input_events.input(), timeout=self.input_event_timeout)
                if self.state is False or time.time()-self.last_time > self.refresh_time:
                    self.last_time=time.time()
                    self.state=True
                    state_change=True
            except asyncio.TimeoutError:
                if self.state is True or time.time()-self.last_time > self.refresh_time:
                    self.last_time=time.time()
                    self.state=False
                    state_change=True
        xstate={'cmd': 'presence',
        'state': self.state}
        return xstate                    
