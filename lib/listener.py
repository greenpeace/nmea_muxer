from threading import Thread
from datetime  import datetime as dt
from .utils import *
import os, re, asyncio, random, string

class Listener:
    def __init__(self,listen_address,lid="",name="",servers=[],msg_setup={},throttle=0):
        self.id = lid if len(lid) > 0 else ''.join(random.choices(string.ascii_uppercase+string.digits,k=8))
        self.listen_address = listen_address
        self.name = name
        self.servers = servers
        self.server_ids = list(map(lambda s: s.id, servers))
        self.msg_setup = msg_setup
        self.throttle = throttle

        self.status = "INIT"
        self.msg_count = {}
        self.msg_queue = {}
        self.msg_order = []
        self.loop = asyncio.new_event_loop()
        self.thread = None
        self.reader = None
        self.alive = True
        self.go_on = True
        self.uptime = 0
        self.started_at = dt.now()
        self.for_export = ["id","listen_address","name","msg_setup","msg_order","server_ids","go_on","throttle"]

    def start(self):
        self.go_on = True
        self.alive = True
        self.started_at = dt.now()
        if not self.thread:
            self.thread = Thread(target=self.async_start)
            self.thread.start()
        elif not self.status == "PAUSED":
            self.thread.join()
            self.thread = Thread(target=self.async_start)
            self.thread.start()
        self.status = "INIT"

    def pause(self):
        self.status = "PAUSED"
        self.go_on = False
        self.uptime += (dt.now() - self.started_at).total_seconds()

    def kill(self):
        self.status = "KILLED"
        self.alive = False
        self.go_on = False
        self.uptime += (dt.now() - self.started_at).total_seconds()
        self.thread.join()

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
            print(self.name, "no reader")
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

        while self.alive:
            try:
                payload = await self.reader.readline()
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
                            self.msg_queue[verb] = payload

                        for server in self.servers:
                            server.emit(payload)

            except Exception as err:
                print(str(err))
                if not str(err) == "Separator is not found, and chunk exceed the limit":
                    print(self.name, err)
                    self.go_on = False
                    self.alive = False
                    break

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

