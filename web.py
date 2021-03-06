

from flask          import Flask, render_template, session, request, \
                           g, redirect
from flask_socketio import SocketIO, emit

from time           import sleep
from datetime       import datetime as dt
from colorama       import Fore, Back, Style
from shutil         import copyfile
from tailer         import tail

import threading
import netifaces
import socket, json, re, os, resource, logging, requests

from lib.talker     import Talker
from lib.listener   import Listener
from lib.settings   import Settings
from lib.utils      import *





app = Flask(__name__)
#app._static_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.config['SECRET_KEY'] = 'M-LkyLF&sid=379941accd8541ef9f9c7e8efb323c82'

socketio = SocketIO(app,async_mode='threading')
pusher = Pusher(socketio)
talkers = []
listeners = []

settings = Settings(app)
logging.basicConfig(
        level=logging.INFO,
        filename=os.path.join(app.root_path, "log", "nmea_muxer.log"),
        filemode='w',
        format='%(message)s'
        )

logging.getLogger('werkzeug').setLevel(logging.WARN)

colors = {"Red":"#f44336", "Pink":"#e91e63", "Purple":"#9c27b0", "Deep purple":"#673ab7", "Indigo":"#3f51b5", "Blue":"#2196f3", "Light blue":"#03a9f4", "Cyan":"#00bcd4", "Teal":"#009688", "Green":"#4caf50", "Light green":"#8bc34a", "Lime":"#cddc39", "Yellow":"#ffeb3b", "Amber":"#ffc107", "Orange":"#ff9800", "Deep orange":"#ff5722", "Brown":"#795548", "Blue grey":"#607d8b", "Grey":"#9e9e9e", "White":"#ffffff"}




@app.before_request
def before_request():
    #print_threads()

    g.poptalker = False
    if talkers == []:
        init()
        sleep(0.1)
        if talkers == []:
            g.poptalker = True

    if request.headers.getlist("X-Forwarded-For"):
        g.ip = request.headers.getlist("X-Forwarded-For")[0]
    else:
        g.ip = request.remote_addr
    g.day = dt.now().strftime("%a, %b %d")
    g.title = "NMEA MUXER"
    g.threadCount = threading.active_count()
    g.talkerCount = len(talkers)
    g.listenerCount = len(listeners)
    g.clientCount = 0
    for s in talkers:
        g.clientCount += len(s.clients)


@app.route("/")
def index():
    g.talkers = talkers
    g.listeners = listeners
    g.sentences = sentences
    return render_template("index.html")

@app.route("/clients/<sid>")
def clients(sid):
    talker = None
    for s in talkers:
        if s.id == sid:
            talker = s

    if talker:
        g.s = talker
        if len(g.s.clients) > 0:
            g.clients = []
            for c in talker.clients:
                try:
                    g.clients.append(["",c.getpeername()[0],c.getpeername()[1]])
                except:
                    talker.clients.remove(c)
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
                #print(iface)
                hold = False
                iid = iface['ip']+":"+str(iface['port'])
                for talker in talkers:
                    if iid == talker.id:
                        if int(iface['port']) != talker.port:
                            for l in listeners:
                                if talker in l.talkers:
                                    l.talkers.remove(talker)
                            talkers.remove(talker)
                            talker.kill()
                        else:
                            hold = True

                        if iface['name'] != talker.name:
                            talker.name = iface['name']

                        if 'active' in iface.keys():
                            talker.resume()
                        else:
                            talker.pause()

                        if 'throttle' in iface.keys():
                            talker.throttle = True
                            talker.run_throttle()
                        else:
                            talker.throttle = False
                            talker.throttling = False

                        if 'delete' in iface.keys():
                            for l in listeners:
                                if talker in l.talkers:
                                    l.talkers.remove(talker)
                            talkers.remove(talker)
                            talker.kill()
                            hold = True


                if not hold:
                    try:
                        talker = Talker((iface['ip'],int(iface['port'])),iface['id'],iface['name'],('throttle' in iface.keys() ),listeners, pusher)
                        talker.start()
                        talker.alive = ('active' in iface.keys() )
                        talkers.append(talker)
                    except:
                        pass

            for l in listeners:
                l.downdate(talkers)
            update()

            return redirect("/",code=303)
        except Exception as err:
            return redirect("/?err="+str(err),code=303)
            #g.error = '<script>M.toast({html:"'+str(err)+'",classes:"red darken-4"})</script>'



    if talkers == []:
        g.ifaces = []
        g.slen = len(talkers)
        for name in netifaces.interfaces():
            iface = netifaces.ifaddresses(name)
            if 2 in iface.keys():
                g.ifaces.append([name,name,iface[2][0]['addr']])
        return render_template("setup.html")

    else:
        g.talkers = []
        g.ifaces = []
        g.slen = len(talkers)
        for talker in talkers:
            if talker.iface in netifaces.interfaces() or True:
                g.talkers.append([talker.iface,talker.name,talker.ip,talker.port,(1 if talker.go_on else 0),(1 if talker.throttle else 0)])
        for name in netifaces.interfaces():
            iface = netifaces.ifaddresses(name)
            if 2 in iface.keys():
                g.ifaces.append([name,name,iface[2][0]['addr']])
        return render_template("setup.html")





@app.route("/add_listener",methods=["GET","POST"])
def add_listener():
    g.error = ''
    g.talkers = talkers
    if request.method == 'POST':
        if not re.match(r"^\d\d?\d?\.\d\d?\d?\.\d\d?\d?\.\d\d?\d?$",request.form['ip']):
            g.error = '<script>M.toast({html:"Invalid IP address",classes:"red darken-4"})</script>'
            return render_template("add_listener.html")
        if not re.match(r"^\d+$",request.form['port']) or int(request.form['port']) > 65535 or int(request.form['port']) <= 0:
            g.error = '<script>M.toast({html:"Invalid port number",classes:"red darken-4"})</script>'
            return render_template("add_listener.html")
        try:
            #print(request.form)
            ss = talkers if ('publish' in request.form.keys()) else []
            listener = Listener( (request.form['ip'], int(request.form['port'])), "", request.form['name'])
            listener.color = request.form['color']
            listener.start()
            listeners.append(listener)
            listener.talkers = []
            for k in request.form:
                if re.match(r"^talker_",k):
                    for s in talkers:
                        if s.id == re.sub(r"^talker_","",k):
                            listener.talkers.append(s)
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
        #print(request.form)
        try:
            listener.name = request.form['name']
            listener.talkers = []
            for k in request.form:
                if re.match(r"^talker_",k):
                    for s in talkers:
                        if s.id == re.sub(r"^talker_","",k):
                            listener.talkers.append(s)
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
            listener.timeout = int(request.form['timeout'])
            listener.update()
            update()
            if oldthrottle != listener.throttle:
                for s in listener.talkers:
                    if s.throttling:
                        s.rerun_throttle()
            return redirect("/",code=303)
        except Exception as err:
            return redirect("/?err="+str(err))



    if listener:
        g.l = listener
        g.talkers = talkers
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
                #print(l.id)
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
            #print(request.form)
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
                return "nack"
        else:
            return "nack"





@app.route("/feed/<sid>")
def feed(sid):
    g.s = None
    g.listeners = listeners
    for s in talkers:
        if sid == s.id:
            #print("pushing", s.name)
            s.push = True
            g.s = s
    g.namespace = '/'+re.sub("\D","_",sid)
    return render_template("feed.html")

@app.route("/nofeed/<sid>")
def nofeed(sid):
    g.s = None
    for s in talkers:
        if sid == s.id:
            g.s = s
    s.push = False
    return ""



@app.route("/threads",methods=["GET"])
def threads():
    g.threads = threading.enumerate()
    return render_template("threads.html")


@app.route("/logs",methods=["GET"])
def logs():
    g.logs = "\n".join(tail(open("./log/nmea_muxer.log"),512))
    pusher.logs()
    return render_template("logs.html")

@app.route("/nologs")
def nologs():
    pusher.nologs()
    return ""



@app.route("/register")
def register():
    global listen_address
    listen_address = (ip, 54321)
    main()
    sleep(0.1)
    return client_message




@app.route("/reboot",methods=["POST"])
def reboot_request():
    if request.method == 'POST':
        rebooted = reboot(request.form['message'])
        return {True:"ack", False:"nack"}[rebooted]





@app.route("/settings",methods=["GET"])
def edit_settings():
    g.listeners = listeners
    g.ct = settings.client_treshold
    g.period = settings.period
    g.saveds = []
    for (_,_, files) in os.walk(os.path.join(app.root_path, "lib", "settings")):
        for f in files:
            if not f in ["_current.json","_backup.json"]:
                g.saveds.append([f[0:-5],os.path.getmtime(os.path.join(app.root_path, "lib", "settings",f))])
                g.toload = len(g.saveds) > 0
    return render_template("settings.html")

@app.route("/set",methods=["POST"])
def set_settings():
    if request.method == 'POST':
        settings.period = request.form['period']
        settings.client_treshold = request.form['client_treshold']
        settings.save(talkers,listeners)
    return "ack"


@app.route("/save_settings",methods=["POST"])
def save_settings():
    if request.method == 'POST':
        settings.save(talkers,listeners,request.form['savefile'])
    return redirect("/",code=303)

@app.route("/load_settings",methods=["POST"])
def load_settings():
    if request.method == 'POST':
        frompath = os.path.join(app.root_path, "lib", "settings", request.form['loadfile']+".json")
        topath = os.path.join(app.root_path, "lib", "settings", "_current.json")
        bkpath = os.path.join(app.root_path, "lib", "settings", "_backup.json")
        if os.path.isfile(frompath):
            copyfile(topath,bkpath)
            copyfile(frompath,topath)
            rebooted = reboot()
            #sleep(1)
            return {True:"ack", False:"nack"}[rebooted]
    return "nack"

@app.route("/delete_settings",methods=["POST"])
def delete_settings():
    if request.method == 'POST':
        path = os.path.join(app.root_path, "lib", "settings", request.form['loadfile']+".json")
        if os.path.isfile(path):
            os.remove(path)
            return "ack"
    return "nack"



def init():
    threading.enumerate()[1].setName("MainFork")
    pprint(Fore.CYAN+'Boot NMEA Multiplexer', " SYSTEM ", "INFO")
    if os.path.isfile(os.path.join(app.root_path, "lib", "settings", "_current.json")):
        settings.load()
        for s in settings.talkers:
            talker = Talker(tuple(s['bind_address']),s['iface'],s['name'],s['throttle'],[],pusher,False,settings.client_treshold)
            talkers.append(talker)
            talker.start()
        for l in settings.listeners:
            ss = []
            for s in talkers:
                if s.id in l['talker_ids']:
                    ss.append(s)
            color = '#ffffff' if not 'color' in l.keys() else l['color']
            accumulate = False if not 'accumulate_sentences' in l.keys() else l['accumulate_sentences']
            resilient = False if not 'resilient' in l.keys() else l['resilient']
            timeout = 10 if not 'timeout' in l.keys() else int(l['timeout'])
            listener = Listener(l['listen_address'],l['id'],l['name'],ss,l['msg_setup'],l['throttle'],color,accumulate,resilient,timeout,settings.period)
            listeners.append(listener)
            listener.start()
            if not 'go_on' in l.keys() or l['go_on'] == False:
                listener.pause()
        update()
        for s in talkers:
            if talker.throttle:
                talker.run_throttle();

def reboot(msg='Reboot initiated, closing sockets'):
    if os.path.isfile(os.path.join(app.root_path, "lib", "app.pid")):
        pid = open(os.path.join(app.root_path, "lib", "app.pid"),"r").read().strip()
        if re.match(r"^\d+$",pid):
            pprint(Fore.MAGENTA+msg, " SYSTEM ", "INFO")
            for talker in talkers:
                talker.kill()
            for listener in listeners:
                listener.kill()
            os.system("kill -HUP {}".format(pid))
            pprint(Fore.MAGENTA+'Signaling worker restart', " SYSTEM ", "INFO")
            return True
        else:
            return False
    else:
        return False

def update():
    settings.save(talkers,listeners)
    for s in talkers:
        s.listeners = listeners
    pusher.talkers = talkers
    pusher.reload()

def print_threads():
    print()
    for t in threading.enumerate():
        print(t.name)
    if talkers == []:
        init()
    print()

def ignition(worker):
    ign = threading.Thread(target=ignite)
    for talker in talkers:
        talker.kill()
    for listener in listeners:
        listener.kill()
    sleep(1)
    ign.start()

def ignite():
    #os.system("curl http://"+os.environ['NMEA_BIND_ADDRESS']+" &> /dev/null")
    requests.get("http://"+os.environ['NMEA_BIND_ADDRESS'])
    return


if __name__ == '__main__':
    app.run(debug=True, threaded=True)






