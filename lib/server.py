from threading import Thread
from time      import sleep
from datetime  import datetime as dt
from .utils    import *
import re, socket, random

class Server:


    def __init__(self,bind_address,iface="",name="",throttle=False,listeners=[],pusher=None,verbose=False):

        self.bind_address = bind_address
        self.name = name
        self.iface = iface
        self.id = bind_address[0]+":"+str(bind_address[1])
        self.ip = bind_address[0]
        self.port = bind_address[1]
        self.throttle = throttle
        self.verbose = verbose
        self.listeners = listeners
        self.pusher = pusher

        self.thread = None
        self.alive = True
        self.go_on = True
        self.push = False

        self.throttle_thread = None
        self.throttle_steps={}
        self.throttling = False
        self.throttle_step = 0
        self.tt = 0

        self.clients=[]
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.uptime = 0
        self.started_at = dt.now()
        self.tries = 3

        self.for_export = ["bind_address","name","iface","throttle"]

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
                self.thread = Thread(target=self.process,name="S "+self.name+" "+str(round(random.random()*1000)))
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

    def emit(self,sentence,color):
        if self.verbose:
            print(sentence) 
        if self.alive and not self.throttle:
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
            if self.pusher and self.push:
                self.pusher.push(sentence.decode().strip(),self.id,color)


    def update_throttle(self):
        if self.throttle:
            tl = {}
            for l in self.listeners:
                if l.throttle <= 0:
                    next
                elif self.id in l.server_ids:
                    tl[l.id] = l.throttle

            if len(tl) == 0:
                self.throttle_steps = {}
                return

            self.tt = lcm_list(list(tl.values()))
            sp = gcd_list(list(tl.values()))
            ts = {}
            for i in range(int(self.tt/sp)):
                step = i * sp
                for l in tl:
                    if step == 0:
                        ts[0] = list(tl.keys())
                    else:
                        if step % tl[l] == 0:
                            if step in ts.keys():
                                ts[step].append(l)
                            else:
                                ts[step] = [l]
                #if step in ts.keys():
                #    print(step, ts[step])
            self.throttle_steps = ts


    def run_throttle(self):
        self.update_throttle()
        print("thrun")
        if len(self.throttle_steps) == 0:
            self.throttling = False
            return False
        if self.throttling:
            return False
        else:
            print("thrunin")
            if not self.throttle_thread:
                self.throttle_thread = Thread(target=self.process_throttle,name="T "+self.name+" "+str(round(random.random()*1000)))
                self.throttle_thread.start()
            else:
                self.throttling = True
                self.throttle_thread.join()
                self.throttle_thread = Thread(target=self.process_throttle,name="T "+self.name+" "+str(round(random.random()*1000)))
                self.throttle_thread.start()

    def rerun_throttle(self):
        self.update_throttle()
        self.throttle_step = 0
        if len(self.throttle_steps) == 0:
            self.throttling = False
            return False

    def process_throttle(self):
        self.throttling = True
        self.throttle_step = 0
        while self.throttling:
            nextstart = list(self.throttle_steps.keys())[(self.throttle_step+1)%len(self.throttle_steps)]
            if nextstart == 0:
                nextstart = self.tt
            start = list(self.throttle_steps.keys())[self.throttle_step]
            period = nextstart - start
            current = dt.now()
            offset = (current - current.replace(microsecond=0)).total_seconds()
            solong = period - offset % period
            if offset + solong > 1:
                solong += 1 % period
            #ls = []
            for send in list(self.throttle_steps.values())[self.throttle_step]:
                for l in self.listeners:
                    if send == l.id and l.go_on:
                        #ls.append(l.name)
                        for verb in l.msg_order:
                            print("tt: ",start, l.name,  verb, verb in l.msg_queue.keys())
                            if verb in l.msg_queue.keys():
                                sentence = l.msg_queue[verb]
                                del l.msg_queue[verb]
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
                                    sleep(0.01)
                                if self.pusher and self.push:
                                    self.pusher.push(sentence.decode().strip(),self.id,l.color)
            #print(start, period, ls)
            sleep(solong)
            self.throttle_step = 0 if self.throttle_step >= len(self.throttle_steps) - 1 else self.throttle_step + 1

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



