from threading  import Thread
from time       import sleep
from datetime   import datetime as dt
from colorama   import Fore, Back, Style

import os, re, asyncio, random, string

from .utils import *

class Listener:
    def __init__(self,listen_address,lid="",name="",servers=[],msg_setup={},throttle=0,color="#FFFFFF",accumulate_sentences=False,resilient=False,timeout=10):
        self.id = lid if len(lid) > 0 else ''.join(random.choices(string.ascii_uppercase+string.digits,k=8))
        self.listen_address = listen_address
        self.name = name
        self.servers = servers
        self.server_ids = list(map(lambda s: s.id, servers))
        self.msg_setup = msg_setup
        self.throttle = throttle
        self.color = color
        self.accumulate_sentences = accumulate_sentences
        self.resilient = resilient
        self.timeout = timeout

        self.status = "INIT"
        self.msg_count = {}
        self.msg_order = []
        self.msg_queue = {}
        self.loop = asyncio.new_event_loop()
        self.thread = None
        self.thread_counter = 0
        self.resilience_thread = None
        self.resilience_alive = True
        self.reader = None
        self.alive = True
        self.go_on = True
        self.uptime = 0
        self.started_at = dt.now()
        self.for_export = ["id","listen_address","name","msg_setup","msg_order","server_ids","go_on","throttle","color","accumulate_sentences","resilient","go_on","timeout"]

    def start(self):
        self.go_on = True
        self.alive = True
        self.started_at = dt.now()


        if not self.thread:
            self.thread = Thread(target=self.async_start,name="Listener: "+self.name+" "+str(self.thread_counter))
            self.thread.start()
            self.thread_counter += 1
        elif not self.status == "PAUSED":
            self.thread.join()
            self.thread = Thread(target=self.async_start,name="Listener: "+self.name+" "+str(self.thread_counter))
            self.thread.start()
            self.thread_counter += 1

        if not self.resilience_thread:
            self.resilience_thread = Thread(target=self.insist,name="Listener (resilience): "+self.name)
            self.resilience_thread.start()

        self.status = "INIT"

    def restart(self):
        self.started_at = dt.now()
        self.reader = None
        print(dt.now().strftime("%Y%m%d %H%M%S"),'Restarting Listener {} on {}:{}'.format(self.name, *self.listen_address))
        if self.thread:
            resilient = self.resilient
            self.alive = False
            self.go_on = False
            self.resilient = False
            self.loop.close()
            self.thread.join()
            self.thread_counter += 1
            while self.thread.is_alive() or self.loop.is_running():
                sleep(0.5)
                print("waiting for shutdown")
            self.resilient = resilient
        self.thread = Thread(target=self.async_start,name="Listener: "+self.name+" "+str(self.thread_counter))
        self.alive = True
        self.go_on = True
        self.thread.start()

        if not self.resilience_thread:
            self.resilience_thread = Thread(target=self.insist,name="Listener (resilience): "+self.name)
            self.resilience_thread.start()

        self.status = "INIT"

    def insist(self):
        while self.resilience_alive:
            if self.resilient and not self.alive:
                self.restart()
            sleep(1)


    def pause(self):
        self.status = "PAUSED"
        self.go_on = False
        self.uptime += (dt.now() - self.started_at).total_seconds()

    def kill(self):
        self.status = "KILLED"
        self.alive = False
        self.go_on = False
        self.resilience_alive = False
        self.uptime += (dt.now() - self.started_at).total_seconds()
        self.loop.close()
        self.thread.join()
        self.resilience_thread.join()

    def update(self):
        self.server_ids = list(map(lambda s: s.id, self.servers))


    def downdate(self,servers):
        self.servers = []
        for s in servers:
            if s.id in self.server_ids:
                self.servers.append(s)

    def async_start(self):
        if not self.loop.is_running():
            self.loop.run_until_complete(self.__async__start())

    async def __async__start(self):

        if not self.reader:
            try:
                self.reader, writer = await asyncio.open_connection(*self.listen_address)
            except ConnectionRefusedError:
                self.status = "CONN RFSD"
                print(self.name, self.status)
                self.go_on = False
                self.alive = False
            except OSError:
                self.status = "SOCK BUSY"
                print(self.name, self.status)
                self.go_on = False
                self.alive = False

        while self.alive and not self.reader._eof:
            try:
                payload = await asyncio.wait_for(self.reader.readline(),self.timeout)
                sentence = payload.decode().strip()
                if re.match(r"^[\$!]\w{4,5},",sentence) and self.go_on:
                    self.status = "UP"
                    verb = sentence.split(",")[0][1:]

                    if not verb in self.msg_setup:
                        self.msg_setup[verb] = {}

                    if not verb in self.msg_order:
                        self.msg_order.append(verb)

                    if 'deny' in self.msg_setup[verb].keys():
                        pass

                    else:
                        if verb in self.msg_count:
                            self.msg_count[verb] += 1
                        else:
                            self.msg_count[verb] = 1

                        if self.throttle > 0:
                            if self.accumulate_sentences:
                                if not verb in self.msg_queue.keys():
                                    self.msg_queue[verb] = []
                                self.msg_queue[verb].append(payload)
                            else:
                                self.msg_queue[verb] = payload


                        for server in self.servers:
                            server.emit(payload,self.color)

            except Exception as err:
                print(Fore.YELLOW + dt.now().strftime("%y%m%d %H%M%S"),Fore.RED+"EXCEPTION"+Style.RESET_ALL," for Listener %s:"%self.name)
                print(err)
                print(Fore.RED+"EOE")
                if not str(err) in ["Separator is not found, and chunk exceed the limit","Separator is found, but chunk is longer than limit"]:
                    break

        if self.reader and self.reader._eof:
            self.status = "BROKEN PIPE"
            print(self.name, self.status)

        self.go_on = False
        self.alive = False

    def get_uptime(self):
        if self.go_on:
            up = self.uptime + (dt.now()-self.started_at).total_seconds()
        else:
            up = self.uptime
        return time_ago(up)

    def as_json(self):
        json = {}
        for attr in dir(self):
            if not callable(getattr(self, attr)) and attr in self.for_export:
                json[attr] = self.__dict__[attr]
        return json

