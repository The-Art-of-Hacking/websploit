#!/bin/bash
# WebSploit installation script
# Author: Omar Ωr Santos
# Web: https://websploit.h4cker.org
# Version: 2.0


clear
echo "

██╗    ██╗███████╗██████╗ ███████╗██████╗ ██╗      ██████╗ ██╗████████╗
██║    ██║██╔════╝██╔══██╗██╔════╝██╔══██╗██║     ██╔═══██╗██║╚══██╔══╝
██║ █╗ ██║█████╗  ██████╔╝███████╗██████╔╝██║     ██║   ██║██║   ██║
██║███╗██║██╔══╝  ██╔══██╗╚════██║██╔═══╝ ██║     ██║   ██║██║   ██║
╚███╔███╔╝███████╗██████╔╝███████║██║     ███████╗╚██████╔╝██║   ██║
 ╚══╝╚══╝ ╚══════╝╚═════╝ ╚══════╝╚═╝     ╚══════╝ ╚═════╝ ╚═╝   ╚═╝

https://websploit.h4cker.org
Author: Omar Ωr Santos
Version: 2.0

A collection of intentionally vulnerable applications running in
Docker containers. These include over 400 exercises to learn and
practice ethical hacking (penetration testing) skills.

"
read -n 1 -s -r -p "Press any key to continue the setup..."

echo " "


apt-get update
#installing Docker
apt-get install -y docker.io

#instantiating Docker containers
docker run --name hackazon -d --restart unless-stopped -p 80:80 santosomar/hackazon
docker run --name webgoat -d --restart unless-stopped -p 6661:8080 -t santosomar/webgoat
docker run --name juice-shop --restart unless-stopped -d -p 6662:3000 santosomar/juice-shop
docker run --name dvwa --restart unless-stopped -itd -p 6663:80 santosomar/dvwa
docker run --name mutillidae_2 --restart unless-stopped -d -p 6664:80 santosomar/mutillidae_2
docker run --name bwapp2 --restart unless-stopped -d -p 8081:80 santosomar/bwapp

#bwapp - go to /install.php then user/pass is bee/bug
#docker run --name vapp2 --restart unless-stopped -d -p 9090:80 santosomar/vuln_app

#setting up look and feel

cd /root/Pictures
wget https://h4cker.org/img/h4cker_wallpaper.png
gsettings set org.gnome.desktop.background picture-uri "file:///root/Pictures/h4cker_wallpaper.png"

#cloning H4cker github
cd /root
git clone https://github.com/The-Art-of-Hacking/h4cker.git

#getting test ssl script
curl -L https://testssl.sh --output testssl.sh
chmod +x testssl.sh
