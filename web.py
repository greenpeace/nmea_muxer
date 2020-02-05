from flask          import Flask, render_template, session, request, \
                           g, redirect
from flask_socketio import SocketIO, emit, disconnect

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

socketio = SocketIO(app, async_mode="gevent")
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
    g.threadCount = threading.activeCount()
    g.serverCount = len(servers)
    g.listenerCount = len(listeners)


@app.route("/")
def index():
    if servers == []:
        init()
        return redirect("setup", code=303)
    else:
        g.servers = servers
        g.listeners = listeners
        print(listeners[0].as_json())
        return render_template("index.html")




@app.route("/setup",methods=["GET","POST"])
def setup():
    if request.method == 'POST':
        for iface in deformalize(request.form):
            hold = False
            for server in servers:
                if iface["id"] == server.iface:
                    if int(iface["port"]) != server.port:
                        for l in listeners:
                            if server in l.servers:
                                l.servers.remove(server)
                        servers.remove(server)
                        server.kill()
                    else:
                        hold = True
                    if iface["name"] != server.name:
                        server.name = iface["name"]
                    if "active" in iface.keys():
                        for l in listeners:
                            if server in l.servers:
                                l.servers.remove(server)
                        servers.remove(server)
                        server.kill()
            if "active" in iface.keys() and not hold:
                server = Server((iface["ip"],int(iface["port"])),iface["id"],iface["name"])
                servers.append(server)
                server.start()
        update()
        return redirect("/",code=303)


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
            if server.iface in netifaces.interfaces():
                g.ifaces.append([server.iface,server.name,server.ip,server.port,1])
                ids.append(server.iface)
        for name in netifaces.interfaces():
            if not name in ids:
                iface = netifaces.ifaddresses(name)
                if 2 in iface.keys() and iface[2][0]['addr'].split('.')[2] == ship_id:
                    g.ifaces.append([name,name,iface[2][0]['addr']])
        return render_template("setup.html")





@app.route("/add_listener",methods=["GET","POST"])
def add_listener():
    if request.method == 'POST':
        ss = servers if ('publish' in request.form.keys()) else []
        listener = Listener( (request.form['ip'], request.form['port']), "", request.form['name'], ss )
        listener.start()
        listeners.append(listener)
        update()
        return redirect("/",code=303)


    return render_template("add_listener.html")


@app.route("/kill_listener",methods=["POST"])
def kill_listener():
    if request.method == 'POST':
        listener = None
        for l in listeners:
            if l.id == request.form['id']:
                listener = l
        if listener:
            listener.kill()
            listeners.remove(listener)
            update()
            return "ack"
        else:
            return "nack"

@app.route("/pause_listener",methods=["POST"])
def pause_listener():
    if request.method == 'POST':
        listener = None
        for l in listeners:
            if l.id == request.form['id']:
                listener = l
        if listener:
            listener.pause()
            update()
            return "ack"
        else:
            return "nack"

@app.route("/resume_listener",methods=["POST"])
def resume_listener():
    if request.method == 'POST':
        listener = None
        for l in listeners:
            if l.id == request.form['id']:
                listener = l
        if listener:
            listener.start()
            update()
            return "ack"
        else:
            return "nack"

@app.route("/toggle_verb",methods=["POST"])
def toggle_verb():
    if request.method == 'POST':
        listener = None
        for l in listeners:
            if l.id == request.form['id']:
                listener = l
        if listener:
            try:
                ms = listener.msg_setup[request.form['verb']]
                if not 'deny' in ms.keys() or ms['deny'] == False:
                    ms['deny'] = True
                else:
                    del ms['deny']
                update()
                return "ack"
            except:
                print("oy")
                return "nack"
        else:
            return "nack"





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
            ss = []
            for s in servers:
                if s.iface in l['server_ids']:
                    ss.append(s)
            listener = Listener(l['listen_address'],l['id'],l['name'],ss,l['msg_setup'])
            listeners.append(listener)
            listener.start()
        update()

def update():
    settings.save(servers,listeners)




if __name__ == '__main__':
    app.run(debug=True, threaded=True)






