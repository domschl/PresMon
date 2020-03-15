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
    '''Async wrapper for `keyboard` and `mouse` modules.'''
    def __init__(self, monitor_keyboard=True, monitor_mouse=True, hotkeys=[], mouse_event_throttle=0.5, min_key_pressed_duration=1.0):
        self.log = logging.getLogger("InputMonitor")
        self.loop = asyncio.get_event_loop()
        self.kdb_thread_active = True
        self.lock=threading.Lock()  # asyncio.Queue is *not* thread-safe
        self.que=queue.Queue()
        self.threads_active=True
        self.mouse_event_throttle=mouse_event_throttle
        self.throttle_timer=0
        self.hotkeys=hotkeys
        self.min_key_pressed_duration=min_key_pressed_duration

        if use_keyboard is False and use_mouse is False:
            self.log.error('This module wont do anything, since neither of the required packages `mouse` and `keyboard` are installed.')
        if monitor_keyboard is False and monitor_mouse is False:
            self.log.warning('All monitoring is disabled!')
        if monitor_keyboard is True and use_keyboard is False:
            self.log.error('Cannot monitor keyboard if python module `keyboard` is not installed!')
        if monitor_keyboard is True and use_keyboard is True:
            self.hotkey_state={}
            self.kbd_event_thread = threading.Thread(
                target=self.kbd_background_thread, args=())
            self.kbd_event_thread.setDaemon(True)
            self.kbd_event_thread.start()
            # Workarounds for broken key-release:
            time.sleep(0.05)
            self.broken_kbd_release_event_thread = threading.Thread(
                target=self.kbd_release_background_thread, args=())
            self.broken_kbd_release_event_thread.setDaemon(True)
            self.broken_kbd_release_event_thread.start()
        if monitor_mouse is True and use_mouse is False:
            self.log.error('Cannot monitor mouse if python module `mouse` is not installed!')
        if monitor_mouse is True and use_mouse is True:
            self.mouse_event_thread = threading.Thread(
                target=self.mouse_background_thread, args=())
            self.mouse_event_thread.setDaemon(True)
            self.mouse_event_thread.start()
        
    def que_kdb_event(self, event):
        line = ', '.join(str(code) for code in keyboard._pressed_events)
        ev={"event_type": "key", "keys": line}
        self.lock.acquire()
        try:
            self.que.put_nowait(ev)
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
        ev = event._asdict()
        ev['event_class'] = event.__class__.__name__
        ev['event_type'] = 'mouse'
        line=json.dumps(ev)
        self.log.debug(line)
        self.lock.acquire()
        try:
            self.que.put_nowait(ev)
        except Exception as e:
            self.log.warning(f"Putting event into queue failed: {e}")
        try:
            self.lock.release()
        except Exception as e:
            self.log.error(f"Unlock failed: {e}")

    def que_hotkey_event(self, hotkey, state):
        if state is True:
            # Workround for broken key-release-event and repeat-ignore:
            if time.time() - self.hotkey_state[hotkey]['last_pressed'] < self.min_key_pressed_duration and self.hotkey_state[hotkey]['pressed'] is True:
                self.hotkey_state[hotkey]['last_pressed']=time.time()
                return
        ev={"event_type": "hotkey", "hotkey": hotkey, "state": state}
        if state is True:
            self.hotkey_state[hotkey]['last_pressed']=time.time()
            self.hotkey_state[hotkey]['pressed']=state
        self.log.debug(ev)
        self.lock.acquire()
        try:
            self.que.put_nowait(ev)
        except Exception as e:
            self.log.warning(f"Putting event into queue failed: {e}")
        try:
            self.lock.release()
        except Exception as e:
            self.log.error(f"Unlock failed: {e}")

    # def que_hotkey_event_end(self, hotkey, state):   ## broken in keyboard lib.
    #     print(f"RELEASE {hotkey}")
    #     self.que_hotkey_event(hotkey, state)

    # Key-Release-Bug work-around thread:
    def kbd_release_background_thread(self):
        while self.threads_active is True:
            for hotkey in self.hotkey_state:
                if time.time() - self.hotkey_state[hotkey]['last_pressed'] > self.min_key_pressed_duration and self.hotkey_state[hotkey]['pressed'] is True:
                    self.hotkey_state[hotkey]['last_pressed']=0
                    self.hotkey_state[hotkey]['pressed']=False
                    self.que_hotkey_event(hotkey, False)
            time.sleep(0.1)

    def kbd_background_thread(self):
        keyboard.hook(self.que_kdb_event)
        if self.hotkeys is not None:
            for hotkey in self.hotkeys:
                self.log.debug(f"Adding hotkey hook for {hotkey}")
                self.hotkey_state[hotkey]={'last_pressed': 0, 'pressed': False}
                keyboard.add_hotkey(hotkey, self.que_hotkey_event, args=(hotkey, True))
                # Unfortunately trigger_on_release seems broken: https://github.com/boppreh/keyboard/issues/178
                # keyboard.add_hotkey(hotkey, self.que_hotkey_event_end, args=(hotkey, False), trigger_on_release=True)

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
            'event': ev}
        return xev

class AsyncInputPresence():
    '''Generates a presence state by monitoring keyboard and/or mouse events.
    
    Considers presence state `away` if no input events for `timeout` seconds. Generate
    a presence event at least every `refresh_time` seconds, even if state hasn't changed.'''
    def __init__(self, monitor_keyboard, monitor_mouse, hotkeys, timeout=300, refresh_time=60):
        self.log = logging.getLogger("KeyboardPresence")
        self.input_event_timeout=timeout
        self.input_events=AsyncInputEventMonitor(monitor_keyboard=monitor_keyboard, monitor_mouse=monitor_mouse, hotkeys=hotkeys)
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
                result = await asyncio.wait_for(self.input_events.input(), timeout=1)
                if self.state is False or (self.state==True and self.refresh_time > 0 and time.time()-self.last_time > self.refresh_time):
                    self.last_time=time.time()
                    self.state=True
                    state_change=True
                    xstate={'cmd': 'presence',
                            'state': self.state}
                if result['event']['event_type']=="hotkey":
                    self.log.debug(f"Hotkey: {result['event']['hotkey']}")
                    state_change=True
                    xstate={'cmd': 'hotkey',
                            'hotkey': result['event']['hotkey'], 'state': result['event']['state']}
            except asyncio.TimeoutError:
                if (self.state is True and time.time()-self.last_time > self.input_event_timeout) or (self.state==False and self.refresh_time > 0 and time.time()-self.last_time > self.refresh_time):
                    self.last_time=time.time()
                    self.state=False
                    state_change=True
                    xstate={'cmd': 'presence',
                            'state': self.state}
        return xstate                    
