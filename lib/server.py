import re
import socket
from threading import Thread
from time import sleep

class Server:


    def __init__(self,bind_address,iface="",name="",verbose=False):
        self.status = "DOWN"
        self.bind_address = bind_address
        self.name = name
        self.iface = iface
        self.ip = bind_address[0]
        self.port = bind_address[1]
        self.verbose = verbose
        self.thread = None
        self.alive = True
        self.go_on = True
        self.clients=[]
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.for_export = ["bind_address","name","iface"]
        self.tries = 3

    def start(self):
        self.tries -= 1
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
                print("Tried many times, didn't work")
                pass

    def kill(self):
        self.status = "CLOSING"
        self.alive = False
        for client in self.clients:
            client.close()
            self.clients.remove(client)
        if self.socket:
            self.socket.shutdown(socket.SHUT_RDWR)
        self.thread.join()
        self.status = "DOWN"

    def emit(self,sentence):
        if self.verbose:
            print(sentence) 
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
                print("  incoming: ",client_address)
                self.clients.append(client)

            except KeyboardInterrupt:
                print()
                print("    KeyboardInterrupt for Server - closing client sockets")
                self.kill()
                print()

            except OSError as err:
                if err.errno != 22:
                    print()
                    print("    Closing Server:",err)
                    print()
                else:
                    if client:
                        client.close()
                        if client in self.clients:
                            self.clients.remove(client)


            except Exception as err:
                print()
                print("    EXCEPTION for Server:",err)
                print()


    def as_json(self):
        json = {}
        for attr in dir(self):
            if not callable(getattr(self, attr)) and attr in self.for_export:
                json[attr] = self.__dict__[attr]
        return json



