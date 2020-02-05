from flask          import Flask, render_template, session, request, \
                           g, redirect

from time           import sleep
from datetime       import datetime as dt

import threading
import netifaces
import json, re, os

from lib.server     import Server
from lib.listener   import Listener
from lib.settings   import Settings
from lib.utils      import *

app = Flask(__name__)
#app._static_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.config['SECRET_KEY'] = 'M-LkyLF&sid=379941accd8541ef9f9c7e8efb323c82'

servers = []
listeners = []
ship_id = "212"

settings = Settings()

@app.before_request
def before_request():
    if servers == []:
        init()
    if request.headers.getlist("X-Forwarded-For"):
        g.ip = request.headers.getlist("X-Forwarded-For")[0]
    else:
        g.ip = request.remote_addr
    g.day = dt.now().strftime("%a, %b %d")
    g.title = "NMEA MUXER"


@app.route("/")
def index():
    if servers == []:
        init()
        return redirect("setup", code=302)
    else:
        g.servers = servers
        return render_template("index.html")

@app.route("/setup",methods=["GET","POST"])
def setup():
    if request.method == 'POST':
        for iface in deformalize(request.form):
            hold = False
            if "active" in iface.keys():
                print(iface)
                for server in servers:
                    if iface["id"] == server.iface:
                        if iface["port"] != server.port:
                            server.kill()
                            servers.remove(server)
                        else:
                            server.name = iface["name"]
                            hold = True
                if not hold:
                    server = Server((iface["ip"],int(iface["port"])),iface["id"],iface["name"])
                    servers.append(server)
                    print("start up server")
                    server.start()
        settings.save(servers,listeners)


    g.title = "NMEA MUXER - Server Setup"
    if servers == []:
        g.ifaces = []
        for name in netifaces.interfaces():
            iface = netifaces.ifaddresses(name)
            if 2 in iface.keys() and iface[2][0]['addr'].split('.')[2] == ship_id:
                g.ifaces.append([name,name,iface[2][0]['addr']])
        return render_template("setup.html")
    else:
        g.ifaces = []
        ids = []
        for server in servers:
            g.ifaces.append([server.iface,server.name,server.ip,server.port,1])
            ids.append(server.iface)
        for name in netifaces.interfaces():
            if not name in ids:
                iface = netifaces.ifaddresses(name)
                if 2 in iface.keys() and iface[2][0]['addr'].split('.')[2] == ship_id:
                    g.ifaces.append([name,name,iface[2][0]['addr']])
        return render_template("setup.html")

@app.route("/register")
def register():
    global listen_address
    listen_address = (ip, 54321)
    main()
    sleep(0.1)
    return client_message


def init():
    if os.path.isfile("lib/settings/current.json"):
        settings.load()
        for s in settings.servers:
            server = Server(tuple(s['bind_address']),s['iface'],s['name'])
            servers.append(server)
            server.start()
        for l in settings.listeners:
            listener = Listener(l['bind_address'],l['iface'],l['name'])
            listeners.append(listener)
            listener.start()





if __name__ == '__main__':
    app.run(debug=True, threaded=True)






