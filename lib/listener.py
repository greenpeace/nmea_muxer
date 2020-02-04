import re
import asyncio
from threading import Thread

class Listener:
    def __init__(self,listen_address,server=None):
        self.status = "DOWN"
        self.listen_address = listen_address
        self.server = server
        self.msg_count = {}
        self.loop = asyncio.get_event_loop()
        self.thread = None
        self.reader = None
        self.alive = True
        self.go_on = True

    def start(self):
        self.go_on = True
        if not self.thread:
            self.thread = Thread(target=self.async_start)
            self.thread.start()

    def stop(self):
        self.status = "DOWN"
        self.go_on = False

    def kill(self):
        self.status = "DOWN"
        self.alive = False
        self.thread.join()

    def async_start(self):
        if not self.loop.is_running():
            self.loop.run_until_complete(self.__async__start())
            print("loop stopped")

    async def __async__start(self):
        if not self.reader:
            try:
                self.reader, writer = await asyncio.open_connection(*self.listen_address)
                self.status = "UP"
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
                if re.match(r"^[\$!]\w{4,5},",sentence) and self.go_on:
                    verb = sentence.split(",")[0][3:]
                    if verb in self.msg_count:
                        self.msg_count[verb] += 1
                    else:
                        self.msg_count[verb] = 1

        except:
            exit(0)


if __name__ == '__main__':
    l = Listener(("192.168.212.17",7008))
    loop = asyncio.get_event_loop()
    loop.run_until_complete(l.start())
