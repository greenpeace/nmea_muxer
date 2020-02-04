from lib.listener import Listener
from lib.server import Server
from time import sleep
import threading


def test():
    try:
        print("starting server")
        s = Server(("192.168.212.181",12345))
        s.start()
        print("defining listener")
        k = Listener(("192.168.212.17",7004),[s])
        l = Listener(("192.168.212.17",7006),[s])
        m = Listener(("192.168.212.17",7008),[s],["DBT","DPT"])
        print("starting listeners")
        sleep(0.3)
        k.start()
        sleep(0.3)
        l.start()
        sleep(0.3)
        m.start()
        while True:
            sleep(5)
            print()
            print(s.status)
            print(threading.activeCount())
            print(k.status,k.msg_count)
            print(l.status,l.msg_count)
            print(m.status,m.msg_count)
            print()
    except KeyboardInterrupt:
        print("")
        print("Kill signal caught - exiting.")
        s.kill()
        k.kill()
        l.kill()
        m.kill()
        while threading.activeCount() > 1:
            print("Active threads: ",threading.activeCount())
            sleep(0.1)
        print("finished.")
        exit(0)

test()
