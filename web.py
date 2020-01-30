import socket
import threading
from flask import Flask, request
from time import sleep
from datetime import datetime as dt
#import re

sock = None
listen = None
clients = []
client_message = "ACK"
listen_address = None

app = Flask(__name__)

@app.route("/")
def index():
    if listen_address == None:
        return 'No NMEA source registered'
    else:
        return 'NMEA source found on {}'.format(listen_address[0])

@app.route("/register")
def register():
    global listen_address
    if request.headers.getlist("X-Forwarded-For"):
        ip = request.headers.getlist("X-Forwarded-For")[0]
    else:
        ip = request.remote_addr
    print(ip)
    listen_address = (ip, 54321)
    main()
    sleep(0.1)
    return client_message

def fork_server():
    global sock
    global clients
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = ('192.168.212.181', 54321)
    try:
        sock.bind(server_address)
    except OSError:
        print("Address in use - exiting.")
        exit(2)
    sock.listen()
    print('Starting up on {} port {}'.format(*server_address))
    while True:
        try:
            client, client_address = sock.accept()
            print("")
            print("incoming: ",client_address)
            print("")
            clients.append(client)
        except:
            pass

def fork_listener():
    global listen
    global clients
    global listen_address
    global client_message

    listen = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        listen.connect(listen_address)
        client_message = "ACK"

    except ConnectionRefusedError:
        client_message = "Connection refused"
        return

    except OSError:
        client_message = "Endpoint busy"
        return

    print('Listening to {} port {}'.format(*listen_address))
    print("")

    try:
        blank = False
        while True:
            sentence = listen.recv(1024).decode().strip()
            if dt.now().second % 10 == 0:
                blank = True
                if len(sentence) > 0:
                    print(sentence," >> {} client(s)".format(len(clients)))
                    payload = sentence.encode()
                    for client in clients:
                        try:
                            client.sendall(payload)
                        except:
                            print()
                            print('Stopping client: {}'.format(str(client)))
                            print()
                            client.close()
                            clients.remove(client)
            elif blank:
                print()
                blank = False

    except:
        listen.close()
        exit(0)

def main():
    threading.Thread(target=fork_server).start()
    threading.Thread(target=fork_listener).start()
