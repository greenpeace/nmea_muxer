from flask          import Flask, render_template, session, request, \
                           g, redirect
from flask_socketio import SocketIO, emit

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

socketio = SocketIO(app,async_mode='threading')
pusher = Pusher(socketio)
servers = []
listeners = []

settings = Settings()

colors = {"Red":"#f44336", "Pink":"#e91e63", "Purple":"#9c27b0", "Deep purple":"#673ab7", "Indigo":"#3f51b5", "Blue":"#2196f3", "Light blue":"#03a9f4", "Cyan":"#00bcd4", "Teal":"#009688", "Green":"#4caf50", "Light green":"#8bc34a", "Lime":"#cddc39", "Yellow":"#ffeb3b", "Amber":"#ffc107", "Orange":"#ff9800", "Deep orange":"#ff5722", "Brown":"#795548", "Blue grey":"#607d8b", "Grey":"#9e9e9e", "White":"#ffffff"}

@app.before_request
def before_request():
    #print_threads()

    g.popserver = False
    if servers == []:
        init()
        sleep(0.1)
        if servers == []:
            g.popserver = True

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
                try:
                    g.clients.append(["",c.getpeername()[0],c.getpeername()[1]])
                except:
                    server.clients.remove(c)
                    print("client not found")
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

                        if 'throttle' in iface.keys():
                            server.throttle = True
                            server.run_throttle()
                        else:
                            server.throttle = False
                            server.throttling = False

                        if 'delete' in iface.keys():
                            for l in listeners:
                                if server in l.servers:
                                    l.servers.remove(server)
                            servers.remove(server)
                            server.kill()
                            hold = True


                if not hold:
                    try:
                        server = Server((iface['ip'],int(iface['port'])),iface['id'],iface['name'],('throttle' in iface.keys() ),listeners, pusher)
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
                g.servers.append([server.iface,server.name,server.ip,server.port,(1 if server.alive else 0),(1 if server.throttle else 0)])
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
            listener.color = request.form['color']
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


    g.colors = colors
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
            oldthrottle = listener.throttle
            listener.throttle = int(request.form['throttle'])

            if 'accumulate' in request.form.keys():
                listener.accumulate_sentences = True
            else:
                listener.accumulate_sentences = False

            if 'resilient' in request.form.keys():
                listener.resilient = True
            else:
                listener.resilient = False

            listener.color = request.form['color']
            listener.update()
            update()
            if oldthrottle != listener.throttle:
                for s in listener.servers:
                    if s.throttling:
                        s.rerun_throttle()
            return redirect("/",code=303)
        except Exception as err:
            return redirect("/?err="+str(err))



    if listener:
        g.l = listener
        g.servers = servers
        g.colors = colors
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

@app.route("/restart_listener",methods=["POST"])
def restart_listener():
    if request.method == 'POST':
        listener = None
        for l in listeners:
            if l.id == request.form['id']:
                listener = l
        if listener:
            listener.restart()
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
        update()
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





@app.route("/feed/<sid>")
def feed(sid):
    g.s = None
    g.listeners = listeners
    for s in servers:
        if sid == s.id:
            print("pushing", s.name)
            s.push = True
            g.s = s
    g.namespace = '/'+re.sub("\D","_",sid)
    return render_template("feed.html")

@app.route("/nofeed/<sid>")
def nofeed(sid):
    g.s = None
    for s in servers:
        if sid == s.id:
            g.s = s
    s.push = False
    return ""



@app.route("/threads",methods=["GET"])
def threads():
    g.threads = threading.enumerate()
    return render_template("threads.html")



@app.route("/register")
def register():
    global listen_address
    listen_address = (ip, 54321)
    main()
    sleep(0.1)
    return client_message


def init():
    threading.enumerate()[1].setName("MainFork")
    if os.path.isfile("lib/settings/current.json"):
        settings.load()
        for s in settings.servers:
            server = Server(tuple(s['bind_address']),s['iface'],s['name'],s['throttle'],[],pusher)
            servers.append(server)
            server.start()
        for l in settings.listeners:
            ss = []
            for s in servers:
                if s.id in l['server_ids']:
                    ss.append(s)
            color = '#ffffff' if not 'color' in l.keys() else l['color']
            accumulate = False if not 'accumulate_sentences' in l.keys() else l['accumulate_sentences']
            resilient = False if not 'resilient' in l.keys() else l['resilient']
            listener = Listener(l['listen_address'],l['id'],l['name'],ss,l['msg_setup'],l['throttle'],color,accumulate,resilient)
            listeners.append(listener)
            listener.start()
            if not 'go_on' in l.keys() or l['go_on'] == False:
                listener.pause()
        update()
        for s in servers:
            if server.throttle:
                server.run_throttle();

def update():
    settings.save(servers,listeners)
    for s in servers:
        s.listeners = listeners
    pusher.servers = servers
    pusher.reload()

def print_threads():
    print()
    for t in threading.enumerate():
        print(t.name)
    if servers == []:
        init()
    print()



if __name__ == '__main__':
    app.run(debug=True, threaded=True)






