from threading import Thread
from time      import sleep
from datetime  import datetime as dt
from .utils    import *
import re, socket

class Server:


    def __init__(self,bind_address,iface="",name="",verbose=False):
        self.bind_address = bind_address
        self.name = name
        self.iface = iface
        self.id = bind_address[0]+":"+str(bind_address[1])
        self.ip = bind_address[0]
        self.port = bind_address[1]
        self.verbose = verbose

        self.thread = None
        self.alive = True
        self.go_on = True
        self.clients=[]
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.uptime = 0
        self.started_at = dt.now()
        self.for_export = ["bind_address","name","iface"]
        self.tries = 3
        self.status = "INIT"

    def start(self):
        self.tries -= 1
        self.started_at = dt.now()
        try:
            self.socket.bind(self.bind_address)
            self.status = "UP"
            self.socket.listen()
            print('    Starting server on {} port {}'.format(*self.bind_address))
            if not self.thread:
                self.thread = Thread(target=self.process)
                self.thread.start()
        except Exception as err:
            if self.tries >= 0:
                print(err, ", retrying")
                sleep(1)
                self.start()
            else:
                self.alive = False
                self.go_on = False
                print("Tried many times, didn't work")
                pass

    def kill(self):
        self.status = "CLOSING"
        self.alive = False
        self.uptime += (dt.now() - self.started_at).total_seconds()
        for client in self.clients:
            client.close()
            self.clients.remove(client)
        if self.socket:
            self.socket.shutdown(socket.SHUT_RDWR)
        self.thread.join()
        self.status = "KILLED"


    def pause(self):
        if self.alive:
            self.status = "PAUSED"
            self.alive = False
            self.uptime += (dt.now() - self.started_at).total_seconds()

    def resume(self):
        if not self.alive:
            self.status = "UP"
            self.alive = True
            self.uptime += (dt.now() - self.started_at).total_seconds()

    def emit(self,sentence):
        if self.verbose:
            print(sentence) 
        if self.alive:
            for client in self.clients:
                try:
                    client.sendall(sentence)
                except Exception as err:
                    if err.errno == 32:
                        print("    Client disconnected:",err.strerror)
                        client.close()
                        if client in self.clients:
                            self.clients.remove(client)
                    else:
                        print()
                        print("    EXCEPTION for Server:",err)
                        print()

    def process(self):

        while self.alive:
            client = None
            try:
                client, client_address = self.socket.accept()
                print("    Incoming client: ",client_address)
                self.clients.append(client)

            except KeyboardInterrupt:
                print()
                print("    KeyboardInterrupt for Server - closing client sockets")
                self.kill()
                print()

            except OSError as err:
                if err.errno == 22:
                    if client:
                        client.close()
                        if client in self.clients:
                            self.clients.remove(client)
                else:
                    print()
                    print("    Closing Server:",err)
                    print()


            except Exception as err:
                print()
                print("    EXCEPTION for Server:",err)
                print()



    def get_uptime(self):
        if self.alive:
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



