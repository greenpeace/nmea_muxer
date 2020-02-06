from flask          import Flask, render_template, session, request, \
                           g, redirect
from flask_socketio import SocketIO, emit, disconnect

from time           import sleep
from datetime       import datetime as dt

import threading
import netifaces
import socket, json, re, os, resource

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
    g.threadCount = threading.active_count()
    g.serverCount = len(servers)
    g.listenerCount = len(listeners)
    g.clientCount = 0
    for s in servers:
        g.clientCount += len(s.clients)


@app.route("/")
def index():
    if servers == []:
        init()
        return redirect("setup", code=303)
    else:
        g.servers = servers
        g.listeners = listeners
        return render_template("index.html")

@app.route("/clients/<sid>")
def clients(sid):
    server = None
    for s in servers:
        if s.id == sid:
            server = s

    if server:
        g.s = server
        if len(g.s.clients) > 0:
            g.clients = []
            for c in server.clients:
                g.clients.append(["",c.getpeername()[0],c.getpeername()[1]])
                #try:
                #    g.clients.append([socket.gethostbyaddr(c.getpeername()[0])[0],c.getpeername()[0],c.getpeername()[1]])
                #except:
                #    g.clients.append(["---",c.getpeername()[0],c.getpeername()[1]])
            return render_template("clients.html")
        else:
            return "<h6>No client registered.</h6>"
    else:
        return ""




@app.route("/setup",methods=["GET","POST"])
def setup():
    g.error = ""
    if request.method == 'POST':
        try:
            for iface in deformalize(request.form):
                hold = False
                print(iface)
                iid = iface['ip']+":"+str(iface['port'])
                for server in servers:
                    if iid == server.id:
                        if int(iface['port']) != server.port:
                            for l in listeners:
                                if server in l.servers:
                                    l.servers.remove(server)
                            servers.remove(server)
                            server.kill()
                        else:
                            hold = True

                        if iface['name'] != server.name:
                            server.name = iface['name']

                        if 'active' in iface.keys():
                            server.resume()
                        else:
                            server.pause()

                        if 'delete' in iface.keys():
                            for l in listeners:
                                if server in l.servers:
                                    l.servers.remove(server)
                            servers.remove(server)
                            server.kill()
                            hold = True


                if not hold:
                    try:
                        server = Server((iface['ip'],int(iface['port'])),iface['id'],iface['name'])
                        server.start()
                        server.alive = ('active' in iface.keys() )
                        servers.append(server)
                    except:
                        pass

            for l in listeners:
                l.downdate(servers)
            update()

            return redirect("/",code=303)
        except Exception as err:
            g.error = '<script>M.toast({html:"'+str(err)+'",classes:"red darken-4"})</script>'



    if servers == []:
        g.ifaces = []
        g.slen = len(servers)
        for name in netifaces.interfaces():
            iface = netifaces.ifaddresses(name)
            if 2 in iface.keys():
                g.ifaces.append([name,name,iface[2][0]['addr']])
        return render_template("setup.html")

    else:
        g.servers = []
        g.ifaces = []
        g.slen = len(servers)
        for server in servers:
            if server.iface in netifaces.interfaces():
                g.servers.append([server.iface,server.name,server.ip,server.port,(1 if server.alive else 0)])
        for name in netifaces.interfaces():
            iface = netifaces.ifaddresses(name)
            if 2 in iface.keys():
                g.ifaces.append([name,name,iface[2][0]['addr']])
        return render_template("setup.html")





@app.route("/add_listener",methods=["GET","POST"])
def add_listener():
    g.error = ''
    g.servers = servers
    if request.method == 'POST':
        if not re.match(r"^\d\d?\d?\.\d\d?\d?\.\d\d?\d?\.\d\d?\d?$",request.form['ip']):
            g.error = '<script>M.toast({html:"Invalid IP address",classes:"red darken-4"})</script>'
            return render_template("add_listener.html")
        if not re.match(r"^\d+$",request.form['port']) or int(request.form['port']) > 65535 or int(request.form['port']) <= 0:
            g.error = '<script>M.toast({html:"Invalid port number",classes:"red darken-4"})</script>'
            return render_template("add_listener.html")
        try:
            print(request.form)
            ss = servers if ('publish' in request.form.keys()) else []
            listener = Listener( (request.form['ip'], int(request.form['port'])), "", request.form['name'])
            listener.start()
            listeners.append(listener)
            listener.servers = []
            for k in request.form:
                if re.match(r"^server_",k):
                    for s in servers:
                        if s.id == re.sub(r"^server_","",k):
                            listener.servers.append(s)
            listener.update()
            update()
            return redirect("/",code=303)
        except Exception as err:
            g.error = '<script>M.toast({html:"'+str(err)+'",classes:"red darken-4"})</script>'


    return render_template("add_listener.html")


@app.route("/edit_listener/<id>",methods=["GET","POST"])
def edit_listener(id):
    g.error = ''
    listener = None
    for l in listeners:
        if l.id == id:
            listener = l

    if request.method == 'POST' and listener:
        print(request.form)
        try:
            listener.name = request.form['name']
            listener.servers = []
            for k in request.form:
                if re.match(r"^server_",k):
                    for s in servers:
                        if s.id == re.sub(r"^server_","",k):
                            listener.servers.append(s)
            listener.update()
            update()
            return redirect("/",code=303)
        except Exception as err:
            g.error = '<script>M.toast({html:"'+str(err)+'",classes:"red darken-4"})</script>'



    if listener:
        g.l = listener
        g.servers = servers
        return render_template("edit_listener.html")
    else:
        return ""


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
            return ""
    return ""

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
            print("ack")
            return "ack"
        else:
            return "nack"

@app.route("/reorder",methods=["GET","POST"])
def reorder():
    if request.method == 'POST':
        global listeners
        ls = []
        for lid in request.form.getlist('order[]'):
            for l in listeners:
                print(l.id)
                if l.id == lid:
                    ls.append(l)
        listeners = ls
        return "ack"

    g.listeners = listeners
    return render_template("reorder.html")

@app.route("/reorder/<lid>",methods=["POST"])
def reorder_sentences(lid):
    if request.method == 'POST':
        listener = None
        for l in listeners:
            if l.id == lid:
                listener = l
        if listener:
            print(request.form)
            listener.msg_order = request.form.getlist('order[]')
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
                if s.id in l['server_ids']:
                    ss.append(s)
            listener = Listener(l['listen_address'],l['id'],l['name'],ss,l['msg_setup'])
            listeners.append(listener)
            listener.start()
        update()

def update():
    settings.save(servers,listeners)




if __name__ == '__main__':
    app.run(debug=True, threaded=True)






