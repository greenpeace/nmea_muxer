import socket
import threading
from time import sleep
from random import random

sock = None
listen = None
nxt = 0
clients = []
client_message = "ACK"
listen_address = None

sentences = open("nmea_sample.txt").readlines()

def main():
    global sock
    global clients
    global nxt
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = ('127.0.0.1', 54321)
    try:
        sock.bind(server_address)
    except OSError:
        print("Address in use - exiting.")
        exit(2)
    sock.listen()
    print('Starting up on {} port {}'.format(*server_address))
    threading.Thread(target=fork_server).start()

    while True:
        print(sentences[nxt])
        for client in clients:
            client.sendall(sentences[nxt])
        nxt += 1
        if nxt >= len(sentences):
            nxt = 0

        if nxt % 5 == 0:
            sleep(1)
        sleep(random()*0.2)

def fork_server():
    global sock
    global clients
    while True:
        client, client_address = sock.accept()
        print("")
        print("incoming: ",client_address)
        print("")
        clients.append(client)
if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Closing {} clients.".format(len(clients)))
        for client in clients:
            client.close()

        pass

