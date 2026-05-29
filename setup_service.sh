#!/bin/bash
sudo tee /etc/systemd/system/cachebot.service > /dev/null <<EOL
[Unit]
Description=Cache Discord Bot Service
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/venv/bin/python $(pwd)/collage.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOL

sudo systemctl daemon-reload
sudo systemctl enable cachebot.service
sudo systemctl start cachebot.service
echo "================================================="
echo "   Cache Bot Service is started and enabled!     "
echo "================================================="
