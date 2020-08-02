from threading  import Thread
from time       import sleep
from datetime   import datetime as dt

import os, re, asyncio, random, string

from .utils import *

class Listener:
    def __init__(self,listen_address,lid="",name="",talkers=[],msg_setup={},throttle=0,color="#FFFFFF",accumulate_sentences=False,resilient=False,timeout=10,restart_period=1):
        self.id = lid if len(lid) > 0 else ''.join(random.choices(string.ascii_uppercase+string.digits,k=8))
        self.listen_address = listen_address
        self.name = name
        self.talkers = talkers
        self.talker_ids = list(map(lambda s: s.id, talkers))
        self.msg_setup = msg_setup
        self.throttle = throttle
        self.color = color
        self.accumulate_sentences = accumulate_sentences
        self.resilient = resilient
        self.timeout = timeout
        self.restart_period = min(1,restart_period)

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
        self.writer = None
        self.alive = True
        self.go_on = True
        self.uptime = 0
        self.started_at = dt.now()
        self.for_export = ["id","listen_address","name","msg_setup","msg_order","talker_ids","go_on","throttle","color","accumulate_sentences","resilient","go_on","timeout"]

    def start(self):
        self.go_on = True
        self.alive = True
        self.started_at = dt.now()


        if not self.thread:
            self.thread = Thread(target=self.async_start,name="Listener: "+self.name+" "+str(self.thread_counter))
            self.thread.start()
            self.thread_counter += 1
            pprint('Starting              {}:{}{}{} {}'.format(self.listen_address[0].rjust(15," "), Style.BRIGHT, str(self.listen_address[1]).ljust(5," "), Fore.BLUE, self.name), "LISTENER", "INFO")
        elif not self.status == "PAUSED":
            self.thread.join()
            self.thread = Thread(target=self.async_start,name="Listener: "+self.name+" "+str(self.thread_counter))
            self.thread.start()
            self.thread_counter += 1
            pprint('Restarting            {}:{}{}{} {}'.format(self.listen_address[0].rjust(15," "), Style.BRIGHT, str(self.listen_address[1]).ljust(5," "), Fore.BLUE, self.name), "LISTENER", "INFO")
        else:
            pprint('Resuming              {}:{}{}{} {}'.format(self.listen_address[0].rjust(15," "), Style.BRIGHT, str(self.listen_address[1]).ljust(5," "), Fore.BLUE, self.name), "LISTENER", "INFO")

        if not self.resilience_thread:
            self.resilience_thread = Thread(target=self.insist,name="Listener (resilience): "+self.name)
            self.resilience_thread.start()

        self.status = "INIT"

    def restart(self):
        self.started_at = dt.now()
        self.reader = None
        pprint('Restarting            {}:{}{}{} {}'.format(self.listen_address[0].rjust(15," "), Style.BRIGHT, str(self.listen_address[1]).ljust(5," "), Fore.BLUE, self.name), "LISTENER", "INFO")
        if self.thread:
            resilient = self.resilient
            self.alive = False
            self.go_on = False
            self.resilient = False
            self.thread.join()
            self.thread_counter += 1
            while self.thread.is_alive():
                sleep(0.1)
            self.resilient = resilient
        if self.loop:
            self.loop.stop()
            while self.loop.is_running():
                sleep(0.1)
            if self.loop:
                self.loop.close()
                while not self.loop.is_closed():
                    sleep(0.1)
        self.loop = asyncio.new_event_loop()
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
            sleep(self.restart_period)


    def pause(self):
        self.status = "PAUSED"
        self.go_on = False
        self.uptime += (dt.now() - self.started_at).total_seconds()
        pprint('Pausing               {}:{}{}{} {}'.format(self.listen_address[0].rjust(15," "), Style.BRIGHT, str(self.listen_address[1]).ljust(5," "), Fore.BLUE, self.name), "LISTENER", "INFO")

    def kill(self):
        self.status = "KILLED"
        self.alive = False
        self.go_on = False
        self.resilience_alive = False
        self.uptime += (dt.now() - self.started_at).total_seconds()
        pprint('Closing               {}:{}{}{} {}'.format(self.listen_address[0].rjust(15," "), Style.BRIGHT, str(self.listen_address[1]).ljust(5," "), Fore.BLUE, self.name), "LISTENER", "INFO")
        self.thread.join()
        self.resilience_thread.join()
        while self.thread.is_alive():
            sleep(0.1)
        if self.loop:
            self.loop.stop()
            while self.loop.is_running():
                sleep(0.1)
            if self.loop:
                try:
                    self.loop.close()
                except:
                    pass
                while not self.loop.is_closed():
                    sleep(0.1)

    def update(self):
        self.talker_ids = list(map(lambda s: s.id, self.talkers))


    def downdate(self,talkers):
        self.talkers = []
        for s in talkers:
            if s.id in self.talker_ids:
                self.talkers.append(s)

    def async_start(self):
        if not self.loop.is_running():
            self.loop.run_until_complete(self.__async__start())

    async def __async__start(self):

        if not self.reader:
            try:
                self.reader, self.writer = await asyncio.open_connection(*self.listen_address)
            except ConnectionRefusedError:
                self.status = "CONN RFSD"
                pprint('{} {}:{}{}{} {}'.format(self.status.ljust(21," "), self.listen_address[0].rjust(15," "), Style.BRIGHT, str(self.listen_address[1]).ljust(5," "), Fore.BLUE, self.name), "LISTENER", "WARN")
                self.go_on = False
                self.alive = False
            except OSError:
                self.status = "SOCK BUSY"
                pprint('{} {}:{}{}{} {}'.format(self.status.ljust(21," "), self.listen_address[0].rjust(15," "), Style.BRIGHT, str(self.listen_address[1]).ljust(5," "), Fore.BLUE, self.name), "LISTENER", "WARN")
                self.go_on = False
                self.alive = False

        while self.alive and not self.reader._eof:
            try:
                payload = await asyncio.wait_for(self.reader.readline(),self.timeout) # ERR
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


                        for talker in self.talkers:
                            talker.emit(payload,self.color)

            except ConnectionResetError as err:
                pprint('{} {}:{}{}{} {}'.format(str(err).ljust(21," "), self.listen_address[0].rjust(15," "), Style.BRIGHT, str(self.listen_address[1]).ljust(5," "), Fore.BLUE, self.name), "LISTENER", "ERROR")
                self.go_on = False
                self.alive = False
                if self.writer:
                    self.writer.close()
                return

            except ValueError as err:
                # Handle common AIS overflow silently
                if str(err) in ["Separator is not found, and chunk exceed the limit","Separator is found, but chunk is longer than limit"]:
                    pprint('{} {}:{}{}{} {}'.format(str(err).ljust(21," "), self.listen_address[0].rjust(15," "), Style.BRIGHT, str(self.listen_address[1]).ljust(5," "), Fore.BLUE, self.name), "LISTENER", "DEBUG")
                else:
                    pprint('ValueError: {} {}:{}{}{} {}'.format(str(err).ljust(21," "), self.listen_address[0].rjust(15," "), Style.BRIGHT, str(self.listen_address[1]).ljust(5," "), Fore.MAGENTA, self.name), "LISTENER", "ERROR")

            except TimeoutError as err:
                pprint('{}: {} {}:{}{}{} {}'.format(type(err).__name__,str(err).ljust(21," "), self.listen_address[0].rjust(15," "), Style.BRIGHT, str(self.listen_address[1]).ljust(5," "), Fore.MAGENTA, self.name), "LISTENER", "WARN")
                break

            except Exception as err:
                pprint('EXCEPTION ({}): {} {}:{}{}{} {}'.format(type(err).__name__,str(err).ljust(21," "), self.listen_address[0].rjust(15," "), Style.BRIGHT, str(self.listen_address[1]).ljust(5," "), Fore.MAGENTA, self.name), "LISTENER", "ERROR")
                break

        if self.reader and self.reader._eof:
            self.status = "BROKEN PIPE" 
            pprint('{} {}:{}{}{} {}'.format("BROKEN PIPE".ljust(21," "), self.listen_address[0].rjust(15," "), Style.BRIGHT, str(self.listen_address[1]).ljust(5," "), Fore.BLUE, self.name), "LISTENER", "ERROR")

        self.go_on = False
        self.alive = False
        if self.writer:
            self.writer.close()
            try:
                await self.writer.wait_closed()
            except Exception as err:
                pprint('EXCEPTION ({}): {}:{}{}{} {}'.format(type(err).__name__,str(err).ljust(21," "), self.listen_address[0].rjust(15," "), Style.BRIGHT, str(self.listen_address[1]).ljust(5," "), Fore.BLUE, self.name), "LISTENER", "DEBUG")

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

