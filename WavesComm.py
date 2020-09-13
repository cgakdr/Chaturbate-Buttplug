#!/usr/bin/env python3

from pipe import Pipe
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as expected
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver import Firefox, FirefoxProfile
from lxml import html
import websockets
import functools
import os
import random
import json
import re
import sys
import threading
import time
from queue import Empty, SimpleQueue
import traceback
from math import sin
from datetime import datetime
from numbers import Number
import asyncio

import requests
import sys
# local versions of libraries
sys.path.insert(0, 'buttplug')
sys.path.insert(0, 'python_readchar\\readchar')
from buttplug.core import ButtplugLogLevel
from buttplug.client import (ButtplugClientWebsocketConnector, ButtplugClient,
                             ButtplugClientDevice, ButtplugClientConnectorError)
from readchar import key as KEY
from readchar import readkey

def main():
    username = sys.argv[1] if len(sys.argv) >= 2 else ''
    pipe = Pipe()
    pipe_comm = pipe.pipe_a
    pipe_watcher = pipe.pipe_b

    comm_thread = threading.Thread(
        target=communicator_runner, args=(pipe_comm, username))
    # target=comm_dummy, args=(pipe_comm, username))
    watcher_thread = threading.Thread(
        target=chat_watcher, args=(pipe_watcher, username))
    # target=comm_test, args=(pipe_watcher, username))
    comm_thread.start()
    watcher_thread.start()
    print('main: started threads')
    print('main: [q]uit\t[a]/[z] delay\t[c]hange user\t[r]eload')
    try:
        while True:
            inp = readkey()
            if inp == 'q':
                raise Exception('Quit pressed')
            elif inp == 'a':
                pipe_watcher.put(('delay', 0.5))
            elif inp == 'z':
                pipe_watcher.put(('delay', -0.5))
            elif inp == 'c':
                new_username = input('Enter new username: ')
                pipe_comm.put(('username', new_username))
                pipe_watcher.put(('username', new_username))
            elif inp == 'r':
                pipe_comm.put(('reload'))
            # TODO command to reload json
        watcher_thread.join()
        comm_thread.join()
    except Exception as ex:
        print('main thread error')
        print(ex)
        pipe_comm.put(Exception('main thread error'))
        pipe_watcher.put(Exception('main thread error'))


def get_config(key):
    config = json.load(open('config.json'))
    return config[key]


def communicator_runner(pipe, username):
    asyncio.run(communicator(pipe, username))
    print('communicator_runner finished')


async def communicator(tips_queue, username):
    async def do_comm(timeout, val):
        if isinstance(val, Number):
            print('do_comm with ' + str(timeout) + 's@' +
                  str(val))
            await dev.send_vibrate_cmd(val)
            await asyncio.sleep(timeout)
        elif type(val) == type('str'):
            print('do_comm with ' + str(timeout) + 's@' + val)
            patterns = {'wave': (0.4, 0.4, 0.4, 0.4, 0.4, 0.5, 0.5, 0.5, 0.5, 0.5, 0.6, 0.6, 0.6, 0.6, 0.6, 0.7, 0.7, 0.7, 0.7, 0.7, 0.8, 0.8, 0.8, 0.8, 0.8, 1.0, 1.0, 1.0, 1.0, 1.0, 0.8, 0.8, 0.8, 0.8, 0.8, 0.7, 0.7, 0.7, 0.7, 0.7, 0.6, 0.6, 0.6, 0.6, 0.6, 0.5, 0.5, 0.5, 0.5, 0.5),
                        'pulse': (1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0),
                        'earthquake': (0.4, 0.4, 0.4, 0.4, 0.4, 0.5, 0.5, 0.5, 0.5, 0.5, 0.6, 0.6, 0.6, 0.6, 0.6, 1.0, 1.0, 1.0, 1.0, 1.0, 0.7, 0.7, 0.7, 0.7, 0.7, 1.0, 1.0, 1.0, 1.0, 1.0, 0.7, 0.7, 0.7, 0.7, 0.7, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0),
                        'fireworks': (0.4, 0.4, 0.4, 0.4, 0.4, 0.5, 0.5, 0.5, 0.5, 0.5, 0.6, 0.6, 0.6, 0.6, 0.6, 0.7, 0.7, 0.7, 0.7, 0.7, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0)}
            pattern = patterns[val]
            idx = 0
            start = time.time()
            while time.time() < start + timeout:
                await dev.send_vibrate_cmd(pattern[idx % len(pattern)])
                idx += 1
                time.sleep(0.1)
        else:
            raise ValueError('Got type ' + str(type(val)))

    async def init_buttplug():
        nonlocal dev
        # print('comm 1')
        client = ButtplugClient('Waves Client')
        connector = ButtplugClientWebsocketConnector('ws://127.0.0.1:12345')
        client.device_added_handler += on_device_added
        await client.connect(connector)
        await client.request_log('Off')
        # print('comm 2')
        await client.start_scanning()
        while dev == None:
            await asyncio.sleep(0.1)
        await client.stop_scanning()
        print('device ready')
        return client

    def on_device_added(emitter, new_dev: ButtplugClientDevice):
        print(f'comm: device added {new_dev} {new_dev.name}')
        asyncio.create_task(on_device_added_task(new_dev))

    async def on_device_added_task(new_dev):
        nonlocal dev
        assert 'VibrateCmd' in new_dev.allowed_messages.keys()
        await new_dev.send_vibrate_cmd(0.25)
        await asyncio.sleep(0.5)
        await new_dev.send_vibrate_cmd(0)
        dev = new_dev

    levelmap = {'0': 0.0,
                'L': 0.25,
                'M': 0.5,
                'H': 0.75,
                'U': 1.0}
    OFF = 0.0

    client = None
    try:
        users = json.load(open('levels.json', 'r'))
        user = None
        if not username in users:
            print('comm: username not found in levels.json')
            user = users['default']
        user = user or users[username]
        dev = None
        client = await init_buttplug()

        delay = 6
        while True:  # each loop iteration handles 1 message
            while True:  # wait for queue message but also allow interrupts
                try:
                    tip = tips_queue.get(timeout=0.1)
                    if type(tip) == Tip:
                        print('comm: recv tip ' + str(tip.val))
                        break
                    else:  # TODO: handle Exception type
                        print('comm: recv command ' + str(tip[0]))
                        if tip[0] == 'delay':
                            delay += tip[1]
                            print('comm: new delay: ' + str(delay))
                        elif tip[0] == 'username':
                            username = tip[1]
                            tips_queue.clear()
                            if not username in users:
                                print('comm: username not found in levels.json')
                                user = users['default']
                            else:
                                user = users[username]
                            print('comm: new username: ' + username)
                        continue
                except Empty:
                    continue
            while time.time() < tip.timestamp + delay:
                await asyncio.sleep(0.25)
            # handle tips
            for level in user:
                if (level['type'] == 'e' and tip.val == level['value']) or (
                        level['type'] == 'g' and tip.val >= level['value']):
                    if level['level'] == 'x':
                        raise Exception('Exception requested in levels.json')
                    elif level['level'] == 'r':
                        tip.val = random.choice(level['selection'])
                        continue
                    elif level['level'] == 'c':
                        tips_queue.clear()
                    else:
                        lvl = None
                        if level['level'] in levelmap:
                            lvl = levelmap[level['level']]
                        lvl = lvl or level['level']
                        await do_comm(level['time'], lvl)
                    break

            await dev.send_vibrate_cmd(OFF)
            print('sent off')
    except ValueError as ex:  # non-int in queue
        print('valueerror in comm')
        print(traceback.format_exc())
    except Exception as ex:
        print('comm thread error')
        print(traceback.format_exc())
    finally:
        try:
            await do_comm(0.1, OFF)
        except:
            pass
        try:
            if client != None:
                await client.disconnect()
        except:
            pass
        return


def comm_test(tips_queue, username):
    try:
        while True:
            print('test: 666 wave 10s')
            tips_queue.put(Tip(666, time.time() - 6))
            time.sleep(12)
            print('test: 777 pulse 10s')
            tips_queue.put(Tip(777, time.time() - 6))
            time.sleep(12)
            print('test: 888 earthquake 10s')
            tips_queue.put(Tip(888, time.time() - 6))
            time.sleep(12)
            print('test: 999 fireworks 10s')
            tips_queue.put(Tip(999, time.time() - 6))
            time.sleep(15)
            print('test: nothing 10s')
            time.sleep(10)

    except Exception as ex:
        print('comm_test error')
        print(traceback.format_exc())
    finally:
        print('comm_test done')


def chat_watcher(tips_queue, username):
    webdriver_json = json.load(open('webdriver.json', 'r'))
    fx_opts = Options()
    fx_profile_dir = webdriver_json['geckodriver']['profileDirectory']
    if fx_profile_dir == '':
        print('watcher error: no profile directory in webdriver.json')
    fx_profile = FirefoxProfile(
        profile_directory=fx_profile_dir)
    fx_driver = Firefox(firefox_profile=fx_profile,
                        options=fx_opts)
    # fx_driver.set_window_size(1900, 980)

    try:
        while True:
            page_uri = 'https://chaturbate.com/' + username + '/'
            fx_driver.get(page_uri)
            WebDriverWait(fx_driver, 10).until(expected.visibility_of_element_located(
                (By.CSS_SELECTOR, '#main.chat_room')))  # wait for chat to start
            print('chat found')
            els = []
            els_old_len = 0

            while True:
                els = fx_driver.find_elements_by_css_selector(
                    '#main.chat_room #chat-box div[style*="background: rgb(255, 255, 51)"]')
                new_els_cnt = len(els) - els_old_len
                new_els = []
                if new_els_cnt > 0:
                    print(
                        f'watcher: new_els_cnt={new_els_cnt}, len(els)={len(els)}, els_old_len={els_old_len}')
                    new_els = els[-new_els_cnt:]
                for el in new_els:
                    text = el.get_attribute('textContent')
                    print(f'watcher found textContent "{text}"')
                    #text = el.find_element_by_css_selector(
                    #    'span.emoticonImage').text
                    try:
                        tip = Tip(int(text.split(' ')[2]), time.time())
                        tips_queue.put(tip)
                        print('watcher sent ' + str(tip.val) +
                              'tip queue len ' + str(tips_queue.len_write()))
                    except ValueError as error:
                        tip = Tip(0, time.time())
                    except IndexError as error:
                        print(
                            f'watcher tip message index error on string "{text}"')
                els_old_len = len(els)
                time.sleep(0.1)
                try:
                    ex = tips_queue.get_nowait()
                    if type(ex) == Exception:
                        raise ex
                    else:
                        if ex[0] == 'username':
                            username = ex[1]
                            print('watcher new username: ' + username)
                            break
                        elif ex[0] == 'reload':
                            break
                except Empty:
                    pass

    except Exception as ex:
        print('watcher thread error')
        print(traceback.format_exc())
    finally:
        tips_queue.put(Exception('watcher thread error'))
        fx_driver.close()
        fx_driver.quit()
        return


def comm_dummy(pipe, username):
    try:
        while True:
            try:
                el = pipe.get()
                print('comm_dummy recv' + str(el))
                if type(el) == Exception:
                    raise el
            except Empty:
                time.sleep(10)
    except Exception:
        print('comm_dummy error')
        print(traceback.format_exc())


class Tip(object):
    val = 0
    timestamp = 0

    def __init__(self, val, timestamp):
        self.val = val
        self.timestamp = timestamp


if __name__ == '__main__':
    main()
