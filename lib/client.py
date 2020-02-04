import socket

sock = None

def main():
    global sock
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = ('192.168.212.181',54321)
    sock.connect(server_address)
    print('Connected to {} port {}'.format(*server_address))

    while True:
        sentence = sock.recv(1024)
        if len(sentence) > 0:
            print(str(sentence.decode().strip()))

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sock.close()
        pass
