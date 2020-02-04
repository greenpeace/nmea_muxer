from lib.listener import Listener
from time import sleep


def test():
    l = Listener(("192.168.212.17",7008))

    print(l.msg_count)
    print(l.thread)
    print(l.loop)
    print("")

    l.start()
    print("")
    print("start")

    sleep(1)

    print(l.msg_count)
    print(l.thread)
    print(l.loop)

    sleep(1)

    print(l.msg_count)
    print(l.thread)
    print(l.loop)

    l.stop()
    print("stop")
    sleep(1)

    print(l.msg_count)
    print(l.thread)
    print(l.loop)

    sleep(1)

    print(l.msg_count)
    print(l.thread)
    print(l.loop)

    l.start()
    print("")
    print("start")

    print(l.msg_count)
    print(l.thread)
    print(l.loop)

    sleep(1)

    print(l.msg_count)
    print(l.thread)
    print(l.loop)

    l.kill()
    print("kill")
    sleep(1)

    print(l.msg_count)
    print(l.thread)
    print(l.loop)

    sleep(1)

    print(l.msg_count)
    print(l.thread)
    print(l.loop)

    sleep(1)

    print(l.msg_count)
    print(l.thread)
    print(l.loop)

    exit(0)

test()
