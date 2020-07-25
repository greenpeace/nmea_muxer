#! /bin/bash

$HOME/.local/bin/gunicorn web:app --config $NMEA_HOME/gunicorn_config.py 0<&- &> log/nmea_muxer.log &

