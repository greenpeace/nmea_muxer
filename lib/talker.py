from threading import Thread
from time      import sleep
from datetime  import datetime as dt
from .utils    import *
import os, re, socket, random, requests

class Talker:


    def __init__(self,bind_address,iface="",name="",throttle=False,listeners=[],pusher=None,verbose=False,client_treshold=5):

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
        self.client_treshold = int(client_treshold)

        self.thread = None
        self.roadkills = 0
        self.alive = True
        self.go_on = True
        self.push = False

        self.reboot_thread = None

        self.resilience_thread = None
        self.resilience_alive = True

        self.throttle_thread = None
        self.throttle_roadkills = 0
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
        self.cip = None

        self.for_export = ["bind_address","name","iface","throttle"]

        self.status = "INIT"

    def start(self):
        self.tries -= 1
        self.started_at = dt.now()
        try:
            self.socket.bind(self.bind_address)
            self.status = "UP"
            self.socket.listen()
            pprint('Starting              {}:{}{} {}{}'.format(self.bind_address[0].rjust(15," "),Style.BRIGHT,str(self.bind_address[1]).ljust(5," "),Fore.CYAN,self.name), " TALKER ", "INFO")
            if not self.thread:
                self.thread = Thread(target=self.process,name="Talker: "+self.name+" "+str(self.roadkills))
                self.thread.start()
        except Exception as err:
            if self.tries >= 0:
                pprint('Retrying              {}:{}{}{} {}'.format(self.bind_address[0].rjust(15," "), Style.BRIGHT, str(self.bind_address[1]).ljust(5," "), Fore.CYAN, self.name), " TALKER ", "DEBUG")
                sleep(1)
                self.restart()
            else:
                self.alive = False
                self.go_on = False
                pprint('Failed to start       {}:{}{}{} {}'.format(self.bind_address[0].rjust(15," "), Style.BRIGHT, str(self.bind_address[1]).ljust(5," "), Fore.CYAN, self.name), " TALKER ", "WARN")
                pass

    def restart(self):
        if self.resilience_alive:
            self.started_at = dt.now()
            self.alive = False
            self.resilience_alive = False
            self.uptime += (dt.now() - self.started_at).total_seconds()
            self.close_clients()
            if self.socket:
                try:
                    self.socket.shutdown(socket.SHUT_RDWR)
                except:
                    pass
                try:
                    self.socket.close()
                except:
                    pass
            if self.thread:
                self.thread.join()
                while self.thread.is_alive():
                    sleep(0.1)
            try:
                self.socket.bind(self.bind_address)
                self.status = "UP"
                self.socket.listen()
                pprint('Restarting            {}:{}{}{} {}'.format(self.bind_address[0].rjust(15," "), Style.BRIGHT, str(self.bind_address[1]).ljust(5," "), Fore.CYAN, self.name), " TALKER ", "INFO")
                self.alive = True
                self.go_on = True
                self.thread = Thread(target=self.process,name="Talker: "+self.name+" "+str(self.roadkills))
                self.thread.start()
            except Exception as err:
                self.alive = False
                self.go_on = False
                pass

        self.resilience_alive = True
        if not self.resilience_thread:
            self.resilience_thread = Thread(target=self.insist,name="Talker (resilience): "+self.name)
            self.resilience_thread.start()


    def insist(self):
        while self.resilience_alive:
            if not self.alive:
                self.restart()
            sleep(1)

    def kill(self):
        self.status = "CLOSING"
        self.alive = False
        self.go_on = False
        self.resilience_alive = False
        self.uptime += (dt.now() - self.started_at).total_seconds()
        self.close_clients()
        if self.socket:
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
            except:
                pass
            try:
                self.socket.close()
                self.socket.wait_closed()
            except:
                pass
            #except Exception as err:
            #    pprint('EXCEPTION ({}): {}:{}{}{} {}'.format(type(err).__name__,str(err).ljust(19," "), self.bind_address[0].rjust(15," "), Style.BRIGHT, str(self.bind_address[1]).ljust(5," "), Fore.CYAN, self.name), " TALKER ", "WARN")
        if self.thread:
            self.thread.join()
        if self.resilience_thread:
            self.resilience_thread.join()
        while (self.thread and self.thread.is_alive()) or (self.resilience_thread and self.resilience_thread.is_alive()):
            sleep(0.1)
        self.status = "KILLED"
        pprint('Closing               {}:{}{}{} {}'.format(self.bind_address[0].rjust(15," "), Style.BRIGHT, str(self.bind_address[1]).ljust(5," "), Fore.CYAN, self.name), " TALKER ", "INFO")


    def pause(self):
        if self.go_on:
            self.close_clients()
            self.status = "PAUSED"
            self.go_on = False
            self.uptime += (dt.now() - self.started_at).total_seconds()
            pprint('Pausing               {}:{}{}{} {}'.format(self.bind_address[0].rjust(15," "), Style.BRIGHT, str(self.bind_address[1]).ljust(5," "), Fore.CYAN, self.name), " TALKER ", "INFO")

    def resume(self):
        if not self.go_on:
            self.status = "UP"
            self.go_on = True
            self.uptime += (dt.now() - self.started_at).total_seconds()
            pprint('Resuming              {}:{}{}{} {}'.format(self.bind_address[0].rjust(15," "), Style.BRIGHT, str(self.bind_address[1]).ljust(5," "), Fore.CYAN, self.name), " TALKER ", "INFO")

    def close_clients(self):
        for client in self.clients:
            try:
                client.shutdown(socket.SHUT_RDWR)
            except:
                pass
            try:
                client.close()
            except:
                pass
            if client in self.clients:
                self.clients.remove(client)

    def emit(self,sentence,color,force=False):
        if self.verbose:
            pprint(Fore.WHITE+sentence.decode().strip(), " SYSTEM ", "INFO")
        if self.alive and self.go_on and (force or not self.throttle):
            for client in self.clients:
                try:
                    client.sendall(sentence)
                except Exception as err:
                    if err.errno in [32]:
                        pprint('Disconnecting client: not connected', " CLIENT ", "INFO")
                        client.close()
                        if client in self.clients:
                            self.clients.remove(client)
                        if len(self.clients) == 0:
                            self.reboot_thread = Thread(target=self.reboot,name="Talker (reboot): "+self.name)
                            self.reboot_thread.start()
                    elif err.errno in [9,110]:
                        pprint('Disconnecting         {}:{}{}'.format(client.getpeername()[0].rjust(15," "),Style.BRIGHT,str(client.getpeername()[1]).ljust(5," ")), " CLIENT ", "INFO")
                        client.shutdown(socket.SHUT_RDWR)
                        client.close()
                        if client in self.clients:
                            self.clients.remove(client)
                        if len(self.clients) == 0:
                            self.reboot_thread = Thread(target=self.reboot,name="Talker (reboot): "+self.name)
                            self.reboot_thread.start()

                    else:
                        pprint('EXCEPTION             {} {}:{}{}'.format(err,client.getpeername()[0].rjust(15," "),Style.BRIGHT,str(client.getpeername()[1]).ljust(5," ")), " CLIENT ", "ERROR")
                        client.shutdown(socket.SHUT_RDWR)
                        client.close()
                        if client in self.clients:
                            self.clients.remove(client)
                        if len(self.clients) == 0:
                            self.reboot_thread = Thread(target=self.reboot,name="Talker (reboot): "+self.name)
                            self.reboot_thread.start()
            if self.pusher and self.push:
                self.pusher.push(sentence.decode().strip(),self.id,color)


    def update_throttle(self):
        if self.throttle:
            tl = {}
            for l in self.listeners:
                if l.throttle <= 0:
                    next
                elif self.id in l.talker_ids:
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
            self.throttle_steps = ts


    def run_throttle(self):
        self.update_throttle()
        if len(self.throttle_steps) == 0:
            self.throttling = False
            return False
        if self.throttling:
            return False
        else:
            if not self.throttle_thread:
                self.throttle_thread = Thread(target=self.process_throttle,name="Talker (throttle): "+self.name+" "+str(self.throttle_roadkills))
                self.throttle_thread.start()
                self.throttle_roadkills += 1
            else:
                self.throttling = True
                self.throttle_thread.join()
                self.throttle_thread = Thread(target=self.process_throttle,name="Talker (throttle): "+self.name+" "+str(self.throttle_roadkills))
                self.throttle_thread.start()
                self.throttle_roadkills += 1

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
                            #print("tt: ",start, l.name,  verb, verb in l.msg_queue.keys())
                            if verb in l.msg_queue.keys():
                                if l.accumulate_sentences:
                                    for sentence in l.msg_queue[verb]:
                                        self.emit(sentence,l.color,True)
                                    del l.msg_queue[verb]
                                else:
                                    sentence = l.msg_queue[verb]
                                    del l.msg_queue[verb]
                                    self.emit(sentence,l.color,True)
            #print(start, period, ls)
            sleep(solong)
            self.throttle_step = 0 if self.throttle_step >= len(self.throttle_steps) - 1 else self.throttle_step + 1

    def process(self):

        while self.alive:
            client = None
            try:
                client, client_address = self.socket.accept()
                self.clients.append(client)
                #client.setblocking(False)

            except KeyboardInterrupt:
                pprint("KeyboardInterrupt     {}:{}{}{} {} - closing client sockets".format(self.bind_address[0].rjust(15," "), Style.BRIGHT, str(self.bind_address[1]).ljust(5," "), Fore.CYAN, self.name)," TALKER ","INFO")
                self.kill()

            except OSError as err:
                if err.errno == 22:
                    if client:
                        client.shutdown(socket.SHUT_RDWR)
                        client.close()
                        if client in self.clients:
                            self.clients.remove(client)
                else:
                    pprint('EXCEPTION             {}:{}{}{} {}'.format(self.bind_address[0].rjust(15," "), Style.BRIGHT, str(self.bind_address[1]).ljust(5," "), Fore.YELLOW, self.name), " TALKER ", "ERROR")


            except Exception as err:
                pprint('EXCEPTION             {}:{}{}{} {}'.format(self.bind_address[0].rjust(15," "), Style.BRIGHT, str(self.bind_address[1]).ljust(5," "), Fore.YELLOW, self.name), " TALKER ", "ERROR")
                self.alive = False

            if client:
                if self.go_on:
                    numconns = 0
                    cip = client.getpeername()[0]
                    for cli in self.clients:
                        if cli.getpeername()[0] == cip:
                            numconns += 1
                    if (numconns >= self.client_treshold):
                        self.cip = cip
                        self.reboot_thread = Thread(target=self.reboot,name="Talker (reboot): "+self.name)
                        self.reboot_thread.start()
                    else:
                        pprint('Incoming              {}:{}{} {}({})'.format(client.getpeername()[0].rjust(15," "),Style.BRIGHT,str(client.getpeername()[1]).ljust(5," "), Fore.GREEN, numconns), " CLIENT ", "INFO")
                else:
                    pprint('Rejecting             {}:{}{}'.format(client.getpeername()[0].rjust(15," "),Style.BRIGHT,str(client.getpeername()[1]).ljust(5," ")), " CLIENT ", "DEBUG")
                    client.shutdown(socket.SHUT_RDWR)
                    client.close()
                    if client in self.clients:
                        self.clients.remove(client)


    def reboot(self):
        requests.post("http://"+os.environ['NMEA_BIND_ADDRESS']+"/reboot", data = {"message":"Restart initiated due to connection treshold {}({}){} on client {}{}".format(Fore.GREEN,self.client_treshold,Style.RESET_ALL+Fore.MAGENTA,Style.BRIGHT,self.cip)})

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



