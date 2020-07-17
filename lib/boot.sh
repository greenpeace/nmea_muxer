#! /bin/bash

#cd /var/www/nmea_muxer
cd $NMEA_HOME
$HOME/.local/bin/gunicorn web:app -w 1 --threads 2 --name nmea -b $NMEA_BIND_ADDRESS -p lib/app.pid 0<&- &> log/nmea_muxer.log &
sleep 1
curl $NMEA_BIND_ADDRESS &> /dev/null

