#!/usr/bin/env python3

import asyncio
import functools
import json
import os
import random
import re
import string
import sys
import threading
import time
import traceback
import urllib.request
from datetime import datetime
from numbers import Number
from queue import Empty, SimpleQueue

import requests
import websockets

from pipe import Pipe

# local versions of libraries
sys.path.insert(0, 'buttplug')
sys.path.insert(0, 'python_readchar\\readchar')
from buttplug.client import (ButtplugClient, ButtplugClientConnectorError,
                             ButtplugClientDevice,
                             ButtplugClientWebsocketConnector)
from buttplug.core import ButtplugLogLevel
from readchar import key as KEY
from readchar import readkey

def main():
    # TODO recording tips for funscript/syncydink
    broadcaster = sys.argv[1] if len(sys.argv) >= 2 else ''
    pipe = Pipe()
    pipe_comm = pipe.pipe_a
    pipe_watcher = pipe.pipe_b

    comm_thread = threading.Thread(
        target=communicator_runner, args=(pipe_comm, broadcaster))
        # target=comm_dummy, args=(pipe_comm, broadcaster))
    watcher_thread = threading.Thread(
        target=chat_watcher_runner, args=(pipe_watcher, broadcaster))
        # target=comm_test, args=(pipe_watcher, broadcaster))
    comm_thread.start()
    watcher_thread.start()
    print('main: started threads')
    print('main: [q]uit\t[a]/[z] delay\t[c]hange broadcaster\t[r]eload')
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
                new_broadcaster = input('Enter new broadcaster: ')
                pipe_comm.put(('broadcaster', new_broadcaster))
                pipe_watcher.put(('broadcaster', new_broadcaster))
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


def communicator_runner(pipe, broadcaster):
    asyncio.run(communicator(pipe, broadcaster))
    print('communicator_runner finished')


async def communicator(tips_queue, broadcaster):
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
                await asyncio.sleep(0.1)
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

    def init_user(tips_queue, broadcaster):
        users = json.load(open('levels.json', 'r'))
        user = None
        if broadcaster in users:
            user = users[broadcaster]
        else:
            print('comm: broadcaster not found in levels.json')
            user = users['default']
        rand = [l for l in user if 'type' in l and l['type'] == 'e' and 'level' in l and l['level'] == 'r']
        if len(rand) > 0:
            tips_queue.put(('random_levels', rand[0]))
        else:
            tips_queue.put(('random_levels', None))
        return user

    levelmap = {'0': 0.0,
                'L': 0.25,
                'M': 0.5,
                'H': 0.75,
                'U': 1.0}
    OFF = 0.0

    client = None
    try:
        user = init_user(tips_queue, broadcaster)
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
                        elif tip[0] == 'broadcaster':
                            broadcaster = tip[1]
                            tips_queue.clear()
                            user = init_user(tips_queue, broadcaster)
                            print('comm: new broadcaster ' + broadcaster)
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
                        if tip.level != None:
                            tip.val = level['selection'][tip.level - 1]
                        else:
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


def comm_test(tips_queue, broadcaster):
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


def chat_watcher_runner(tips_queue, broadcaster):
    asyncio.run(chat_watcher(tips_queue, broadcaster))
    print('chat_watcher_runner finished')


async def chat_watcher(tips_queue, broadcaster):
    try:
        api_info = None
        with urllib.request.urlopen(f'https://chaturbate.com/api/chatvideocontext/{broadcaster}/') as url:
            api_info = json.loads(url.read().decode())
        # CB uses SockJS defaults of randomness
        ws_uri = f"{api_info['wschat_host'].replace('https://', 'wss://')}/{random.randint(100, 999)}/{''.join(random.choices(string.ascii_letters + string.digits, k=8))}/websocket"
        async with websockets.connect(ws_uri) as websocket:
            # opening handshake
            resp = await websocket.recv()
            # print(f'<< {resp}') # 'o'
            json_encoder = json.JSONEncoder()
            obj2 = json_encoder.encode({'method': 'connect', 'data': {'user': api_info['chat_username'], 'password': api_info['chat_password'], 'room': api_info['broadcaster_username'], 'room_password': api_info['room_pass']}})
            obj3 = json_encoder.encode([obj2])
            # print(f'>> {obj3}')
            await websocket.send(obj3)
            resp = await websocket.recv()
            assert 'onAuthResponse' in resp
            # print(f'<< {resp}') # 'a["{\"args\":[\"1\"],\"callback\":null,\"method\":\"onAuthResponse\"}"]'
            obj2 = json_encoder.encode({'method': 'joinRoom', 'data': {'room': broadcaster, 'exploringHashTag': ''}})
            obj3 = json_encoder.encode([obj2])
            # print(f'>> {obj3}')
            await websocket.send(obj3)
            print('watcher connected to chat room')
            ws_connect_time = time.time()

            random_levels = None
            prev_resps = SimpleQueue() # allow follow-up message clarifying random levels to be sent with the tip
            while True:
                resp = None

                try:
                    try:
                        resp = prev_resps.get_nowait()
                    except Empty:
                        resp = await asyncio.wait_for(websocket.recv(), 1)
                except asyncio.TimeoutError:
                    pass

                # save all websockets messages for debugging
                # with open('ws.log', 'a') as f:
                        # f.write(datetime.now().isoformat() + ' ' + resp + '\n')

                if resp != None and re.search(r'tip_alert', resp, re.IGNORECASE) and time.time() - ws_connect_time > 1: # ignore initial burst of old tips
                    # tip notification: a["{\"args\":[\"{\\\"in_fanclub\\\": false, \\\"to_username\\\": \\\"{broadcaster}\\\", \\\"has_tokens\\\": true, \\\"message\\\": \\\"\\\", \\\"tipped_recently\\\": true, \\\"is_anonymous_tip\\\": false, \\\"dont_send_to\\\": \\\"\\\", \\\"from_username\\\": \\\"{username}\\\", \\\"send_to\\\": \\\"\\\", \\\"tipped_alot_recently\\\": true, \\\"amount\\\": 1, \\\"tipped_tons_recently\\\": true, \\\"is_mod\\\": false, \\\"type\\\": \\\"tip_alert\\\", \\\"history\\\": true}\",\"true\"],\"callback\":null,\"method\":\"onNotify\"}"]
                    # random level chosen a["{\"args\":[\"{broadcaster}\",\"{\\\"c\\\": \\\"rgb(120,0,175)\\\", \\\"X-Successful\\\": true, \\\"in_fanclub\\\": false, \\\"f\\\": \\\"Arial, Helvetica\\\", \\\"i\\\": \\\"HWBBR7LPLE7F7V\\\", \\\"gender\\\": \\\"f\\\", \\\"has_tokens\\\": true, \\\"m\\\": \\\"--------\\\\\\\"{username} has RANDOMLY activated level DOMI in 3 by tipping 44 tokens\\\", \\\"tipped_alot_recently\\\": false, \\\"user\\\": \\\"{broadcaster}\\\", \\\"is_mod\\\": false, \\\"tipped_tons_recently\\\": false, \\\"tipped_recently\\\": false}\"],\"callback\":null,\"method\":\"onRoomMsg\"}"]
                    msg = json.loads(json.loads(json.loads(resp[1:])[0])['args'][0])
                    if msg['type'] == 'tip_alert':
                        # print(f'<<j {msg}')
                        amt = msg['amount']
                        tip = Tip(int(amt), time.time())
                        # one of the next few messages might have the randomly chosen level if this tip was for random level
                        if random_levels != None and tip.val == random_levels['value']:
                            # limit to 5 messages or 1 second
                            while prev_resps.qsize() < 5 and time.time() < tip.timestamp + 1:
                                try:
                                    resp = await asyncio.wait_for(websocket.recv(), 1)
                                    matches = re.search(r'level[^\d]+(\d+)', resp)
                                    if matches:
                                        random_tip_level = int(matches.group(1))
                                        tip.val = random_levels['selection'][random_tip_level - 1]
                                        print(f'watcher random tip level found:{random_tip_level} tip.val:{tip.val}')
                                    else:
                                        prev_resps.put(resp)
                                except asyncio.TimeoutError:
                                    pass

                        # send the tip
                        tips_queue.put(tip)
                        print('watcher sent ' + str(tip.val) +
                                ' from ' + msg['from_username'] +
                                ' tip queue len ' + str(tips_queue.len_write()))

                await asyncio.sleep(0.1)
                try:
                    ex = tips_queue.get_nowait()
                    if type(ex) == Exception:
                        raise ex
                    else:
                        if ex[0] == 'broadcaster':
                            broadcaster = ex[1]
                            print('watcher new broadcaster: ' + broadcaster)
                            break
                        elif ex[0] == 'reload':
                            break # TODO
                        elif ex[0] == 'random_levels':
                            random_levels = ex[1]
                            if random_levels != None:
                                random_levels['selection'] = sorted(random_levels['selection'])
                except Empty:
                    pass
    except Exception as ex:
        print('watcher thread error')
        print(traceback.format_exc())
    finally:
        tips_queue.put(Exception('watcher thread error'))
        return


def comm_dummy(pipe, broadcaster):
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

    def __init__(self, val, timestamp, level=None):
        self.val = val
        self.timestamp = timestamp

    def __str__(self):
        return f'Tip val:{self.val} timestamp:{self.timestamp}'


if __name__ == '__main__':
    main()