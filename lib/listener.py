import re
import asyncio
from threading import Thread

class Listener:
    def __init__(self,listen_address,servers=[],allow=[],deny=[]):
        self.status = "DOWN"
        self.listen_address = listen_address
        self.servers = servers
        self.allow = allow
        self.deny = deny
        self.msg_count = {}
        self.loop = asyncio.new_event_loop()
        self.thread = None
        self.reader = None
        self.alive = True
        self.go_on = True

    def start(self):
        self.go_on = True
        if not self.thread:
            self.thread = Thread(target=self.async_start)
            self.thread.start()

    def pause(self):
        self.status = "DOWN"
        self.go_on = False

    def kill(self):
        self.status = "DOWN"
        self.alive = False
        self.thread.join()

    def async_start(self):
        if not self.loop.is_running():
            self.loop.run_until_complete(self.__async__start())

    async def __async__start(self):
        if not self.reader:
            try:
                self.reader, writer = await asyncio.open_connection(*self.listen_address)
            except ConnectionRefusedError:
                self.status = "Connection refused"
                print(self.status)
            except OSError:
                self.status = "Socket busy"
                print(self.status)

        
        try:
            while self.alive:
                payload = await self.reader.readline()
                sentence = payload.decode().strip()
                self.status = "UP"
                if re.match(r"^[\$!]\w{4,5},",sentence) and self.go_on:
                    verb = sentence.split(",")[0][3:]

                    if verb in self.msg_count:
                        self.msg_count[verb] += 1
                    else:
                        self.msg_count[verb] = 1

                    if self.allow == []:
                        if not verb in self.deny:
                            for server in self.servers:
                                server.emit(payload)
                    elif verb in self.allow:
                        for server in self.servers:
                            server.emit(payload)

        except KeyboardInterrupt:
            print()
            print("KeyboardInterrupt for Listener - closing sockets")
            self.kill()
            print()
            pass

        except Exception as err:
            print()
            print("EXCEPTION for Listener:")
            print(err)
            print()


