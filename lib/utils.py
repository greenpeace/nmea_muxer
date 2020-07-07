from math       import gcd
from datetime   import datetime as dt
from colorama   import Fore, Back, Style
import re, struct, socket

def deformalize(form):
    result = {}
    for k in form:
        ordinal = k.split("_")[-1]
        if not ordinal in result.keys():
            result[ordinal] = {}
        result[ordinal]["_".join(k.split("_")[0:-1])] = form[k]
    return list(result.values())

def time_ago(seconds):
    d, rem = divmod(seconds, 86400)
    h, rem = divmod(rem, 3600)
    m, s = divmod(rem, 60)
    if s < 1:s = 0
    locals_ = locals()
    magnitudes_str = ("{n}{magnitude}".format(n=int(locals_[magnitude]), magnitude=magnitude) for magnitude in ("d", "h", "m", "s") if locals_[magnitude])
    result = " ".join(magnitudes_str) if s >= 1 else "N/A"
    return result

def getTCPInfo(s):
    fmt = "B"*7+"I"*21
    x = struct.unpack(fmt, s.getsockopt(socket.IPPROTO_TCP, socket.TCP_INFO, 92))
    return x[0]

def lcm_list(a):
    lcm = int(a[0])
    for i in a[1:]:
        lcm = int(lcm*int(i)/gcd(lcm, int(i)))
    return lcm

def gcd_list(a):
    res = int(a[0])
    for i in a[1:]:
        res = gcd(res, int(i))
    return res

def pprint(msg,sender="SYSTEM",severity="INFO"):
    sen_colors = {
        "CLIENT"    : Fore.GREEN,
        "TALKER"    : Fore.CYAN,
        "LISTENER"  : Fore.BLUE,
        "WEB"       : Fore.YELLOW,
        "SYSTEM"    : Fore.MAGENTA
        }
    sev_colors = {
        "DEBUG"     : Fore.GREEN,
        "INFO"      : Fore.WHITE,
        "WARN"      : Fore.YELLOW+Style.BRIGHT,
        "ERROR"     : Fore.RED+Style.BRIGHT
        }
    sev_times = {
        "DEBUG"     : Fore.MAGENTA,
        "INFO"      : Fore.MAGENTA,
        "WARN"      : Fore.YELLOW,
        "ERROR"     : Fore.RED
        }
    print(sev_times.get(severity) + Style.DIM + dt.now().strftime("%y%m%d%H%M%S")+Style.RESET_ALL,sen_colors.get(sender)+sender.ljust(8," "),sev_colors.get(severity)+msg+Style.RESET_ALL)

class Pusher:
    def __init__(self,socketio,servers=[]):
        self.socketio = socketio
        self.servers = servers

    def push(self, sentence, sid=0, color="#ffffff"):
        self.socketio.emit('feed', {"sentence": sentence, "color":color}, namespace='/'+re.sub("\D","_",sid))
        
    def reload(self):
        self.socketio.emit('reset', {}, namespace="/general")

