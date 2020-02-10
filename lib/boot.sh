#! /bin/bash

ps aux |grep gunicorn |grep web| grep app | awk '{ print $2 }' |xargs kill -HUP

sleep 0.5

curl http://pipe.myez.gl3 > /dev/null

