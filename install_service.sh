#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

echo "[Unit]
Description=Brew monitor
After=network-online.target
[Service]
ExecStart=/usr/bin/python3 $DIR/chiller.py
WorkingDirectory=$DIR
StandardOutput=inherit
StandardError=inherit
Restart=always
User=pi
[Install]
WantedBy=multi-user.target" > /lib/systemd/system/BeerPi.service 

sudo systemctl enable BeerPi.service
sudo systemctl start BeerPi.service

