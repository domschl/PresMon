import json
import time
import logging
import threading
import fileinput
import asyncio

import queue

try:
    import keyboard
    use_keyboard=True
except:
    use_keyboard=False

try:
    import mouse
    use_mouse=True
except:
    use_mouse=False

class AsyncInputEventMonitor():
    '''Async wrapper for `keyboard` module.'''
    def __init__(self, monitor_keyboard=True, monitor_mouse=True, mouse_event_throttle=0.2):
        self.log = logging.getLogger("InputMonitor")
        self.loop = asyncio.get_event_loop()
        self.kdb_thread_active = True
        self.lock=threading.Lock()  # asyncio.Queue is *not* thread-safe
        # self.que=asyncio.Queue()
        self.que=queue.Queue()
        self.threads_active=True
        self.mouse_event_throttle=mouse_event_throttle
        self.throttle_timer=0

        if use_keyboard is False and use_mouse is False:
            self.log.error('This module wont do anything, since neither of the required packages `mouse` and `keyboard` are installed.')
        if monitor_keyboard is False and monitor_mouse is False:
            self.log.warning('All monitoring is disabled!')
        if monitor_keyboard is True and use_keyboard is True:
            self.kbd_event_thread = threading.Thread(
                target=self.kbd_background_thread, args=())
        if monitor_keyboard is True and use_keyboard is False:
            self.log.error('Cannot monitor keyboard if python module `keyboard` is not installed!')
        if monitor_mouse is True and use_mouse is False:
            self.log.error('Cannot monitor mouse if python module `mouse` is not installed!')
        if monitor_mouse is True and use_mouse is True:
            self.kbd_event_thread = threading.Thread(
                target=self.mouse_background_thread, args=())
        self.kbd_event_thread.setDaemon(True)
        self.kbd_event_thread.start()
        
#     def send_event_json(self, event):
#        self.que_event(event)

    def que_kdb_event(self, event):
        line = ', '.join(str(code) for code in keyboard._pressed_events)
        self.lock.acquire()
        try:
            self.que.put_nowait(line)
        except Exception as e:
            self.log.warning(f"Putting event into queue failed: {e}")
        try:
            self.lock.release()
        except Exception as e:
            self.log.error(f"Unlock failed: {e}")

    def que_mouse_event(self, event):
        if time.time()-self.throttle_timer < self.mouse_event_throttle:
            return
        self.throttle_timer=time.time()
        d = event._asdict()
        d['event_class'] = event.__class__.__name__
        line=json.dumps(d)
        self.log.debug(line)
        self.lock.acquire()
        try:
            self.que.put_nowait(line)
        except Exception as e:
            self.log.warning(f"Putting event into queue failed: {e}")
        try:
            self.lock.release()
        except Exception as e:
            self.log.error(f"Unlock failed: {e}")

    def kbd_background_thread(self):
        keyboard.hook(self.que_kdb_event)
        while self.threads_active is True:
            keyboard.wait()

    def mouse_background_thread(self):
        mouse.hook(self.que_mouse_event)
        while self.threads_active is True:
            mouse.wait()
        self.log.warning('mouse event thread exited.')

    async def input(self):
        ev = None
        while ev is None:
            self.lock.acquire()
            try:
                ev = self.que.get_nowait()
                self.lock.release()
                self.que.task_done()
            except:
                self.lock.release()
                ev=None
                await asyncio.sleep(0.1)
        xev={'cmd': 'input',
            'ev': ev}
        return xev

class AsyncInputPresence():
    '''Generates a presence state by monitoring keyboard and/or mouse events.
    
    Considers presence state `away` if no input events for `timeout` seconds. Generate
    a presence event at least every `refresh_time` seconds, even if state hasn't changed.'''
    def __init__(self, monitor_keyboard, monitor_mouse, timeout=300, refresh_time=60):
        self.log = logging.getLogger("KeyboardPresence")
        self.input_event_timeout=timeout
        self.input_events=AsyncInputEventMonitor(monitor_keyboard=monitor_keyboard, monitor_mouse=monitor_mouse)
        self.state=False
        self.last_time=0
        if refresh_time is not None:
            self.refresh_time=refresh_time
        else:
            self.refresh_time=0

    async def presence(self):
        state_change=False
        while state_change is False:
            try:
                await asyncio.wait_for(self.input_events.input(), timeout=1)
                if self.state is False or (self.refresh_time > 0 and time.time()-self.last_time > self.refresh_time):
                    self.last_time=time.time()
                    self.state=True
                    state_change=True
            except asyncio.TimeoutError:
                if (self.state is True and time.time()-self.last_time > self.input_event_timeout) or (self.refresh_time > 0 and time.time()-self.last_time > self.refresh_time):
                    self.last_time=time.time()
                    self.state=False
                    state_change=True
        xstate={'cmd': 'presence',
        'state': self.state}
        return xstate                    
