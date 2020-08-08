from math       import gcd
from datetime   import datetime as dt
from colorama   import Fore, Back, Style
from tailer     import follow
from threading  import Thread
from time       import sleep
import re, struct, socket, logging

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

def pprint(msg,sender=" SYSTEM ",severity="INFO"):
    sen_colors = {
        " CLIENT "  : Fore.GREEN,
        " TALKER "  : Fore.CYAN,
        "LISTENER"  : Fore.BLUE,
        "  WEB   "  : Fore.YELLOW,
        " SYSTEM "  : Fore.MAGENTA
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

    log = Fore.BLACK+Style.BRIGHT+dt.now().strftime("%y%m%d")+Style.RESET_ALL+Style.DIM+Fore.MAGENTA + dt.now().strftime("%H%M%S")+" "+sev_times.get(severity) + severity[0]+ " "+Style.RESET_ALL+sen_colors.get(sender)+sender.ljust(8," ")+" "+sev_colors.get(severity)+msg+Style.RESET_ALL
    if severity == "DEBUG":
        logging.debug(log)
    elif severity == "INFO":
        logging.info(log)
    elif severity == "WARN":
        logging.warn(log)
    elif severity == "ERROR":
        logging.error(log)
    else:
        logging.info(log)

class Pusher:
    def __init__(self,socketio,talkers=[]):
        self.socketio = socketio
        self.talkers = talkers
        self.logging = True
        self.log_thread = None

    def push(self, sentence, sid=0, color="#ffffff"):
        self.socketio.emit('feed', {"sentence": sentence, "color":color}, namespace='/'+re.sub("\D","_",sid))
        
    def logs(self):
        self.logging = True
        self.log_thread = Thread(target=self.logger,name="Log pusher")
        self.log_thread.start()
        pprint("Starting log feed") # toa actually send the close signal :)

    def logger(self):
        for line in follow(open('log/nmea_muxer.log')):
            if self.logging:
                self.socketio.emit('logline', {"line": line}, namespace='/livelogs')
            else:
                return

    def nologs(self):
        self.logging = False
        pprint("Stopping log feed") # to actually send the close signal :)
        if self.log_thread:
            while self.log_thread.is_alive():
                sleep(0.1)
            self.log_thread.join()
            self.log_thread = None

    def reload(self):
        self.socketio.emit('reset', {}, namespace="/general")


sentences = { 
            "HDM":"Heading - Magnetic Actual vessel heading in degrees Magnetic.",
            "GGA":"Global Positioning System Fix Data",
            "DTM":"Datum Reference",
            "HDT":"Heading - True Actual vessel heading in degrees True produced by any device or system producing true heading.",
            "ROT":"Rate Of Turn",
            "VHW":"Water speed and heading",
            "RMC":"Recommended Minimum Navigation Information",
            "VBW":"Dual Ground/Water Speed",
            "VTG":"Track made good and Ground speed",
            "ZDA":"Time & Date - UTC, day, month, year and local time zone.",
            "DBT":"Depth below transducer",
            "DPT":"Depth of Water",
            "VLW":"Distance Traveled through Water",
            "PNG":"Ping status of networks*",
            "VDO":"AIS Ownship Vessel Data Message",
            "VDM":"AIS Vessel Data Message",
            # source of below: http://aprs.gids.nl/nmea/
            "AAM" : "Waypoint Arrival Alarm",
            "ALM" : "GPS Almanac Data",
            "APA" : "Autopilot Sentence \"A\"",
            "APB" : "Autopilot Sentence \"B\"",
            "ASD" : "Autopilot System Data",
            "BEC" : "Bearing & Distance to Waypoint, Dead Reckoning",
            "BOD" : "Bearing, Origin to Destination",
            "BWC" : "Bearing & Distance to Waypoint, Great Circle",
            "BWR" : "Bearing & Distance to Waypoint, Rhumb Line",
            "BWW" : "Bearing, Waypoint to Waypoint",
            "DBT" : "Depth Below Transducer",
            "DCN" : "Decca Position",
            "DPT" : "Depth",
            "FSI" : "Frequency Set Information",
            "GGA" : "Global Positioning System Fix Data",
            "GLC" : "Geographic Position, Loran-C",
            "GLL" : "Geographic Position, Latitude/Longitude",
            "GSA" : "GPS DOP and Active Satellites",
            "GSV" : "GPS Satellites in View",
            "GXA" : "TRANSIT Position",
            "HDG" : "Heading, Deviation & Variation",
            "HDT" : "Heading, True",
            "HSC" : "Heading Steering Command",
            "LCD" : "Loran-C Signal Data",
            "MTA" : "Air Temperature (to be phased out)",
            "MTW" : "Water Temperature",
            "MWD" : "Wind Direction",
            "MWV" : "Wind Speed and Angle",
            "OLN" : "Omega Lane Numbers",
            "OSD" : "Own Ship Data",
            "R00" : "Waypoint active route (not standard)",
            "RMA" : "Recommended Minimum Specific Loran-C Data",
            "RMB" : "Recommended Minimum Navigation Information",
            "RMC" : "Recommended Minimum Specific GPS/TRANSIT Data",
            "ROT" : "Rate of Turn",
            "RPM" : "Revolutions",
            "RSA" : "Rudder Sensor Angle",
            "RSD" : "RADAR System Data",
            "RTE" : "Routes",
            "SFI" : "Scanning Frequency Information",
            "STN" : "Multiple Data ID",
            "TRF" : "Transit Fix Data",
            "TTM" : "Tracked Target Message",
            "VBW" : "Dual Ground/Water Speed",
            "VDR" : "Set and Drift",
            "VHW" : "Water Speed and Heading",
            "VLW" : "Distance Traveled through the Water",
            "VPW" : "Speed, Measured Parallel to Wind",
            "VTG" : "Track Made Good and Ground Speed",
            "WCV" : "Waypoint Closure Velocity",
            "WNC" : "Distance, Waypoint to Waypoint",
            "WPL" : "Waypoint Location",
            "XDR" : "Transducer Measurements",
            "XTE" : "Cross-Track Error, Measured",
            "XTR" : "Cross-Track Error, Dead Reckoning",
            "ZDA" : "Time & Date",
            "ZFO" : "UTC & Time from Origin Waypoint",
            "ZTG" : "UTC & Time to Destination Waypoint",
        }

