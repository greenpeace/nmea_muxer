import web
import os

bind = os.environ['NMEA_BIND_ADDRESS']
workers = 1
threads = 2
proc_name = "nmea"
pidfile = "lib/app.pid"
loglevel = "info"
timeout = 10

post_worker_init = web.ignition

