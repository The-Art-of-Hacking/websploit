#!/bin/bash
# Author: Omar Santos @santosomar
# Lame script to display the running containers in WebSploit

clear
echo -e "\n\e[96mWebSploit\e[39m"
echo -e "by Omar Santos @santosomar"
echo -e "-------------------------------------"
echo -e "Internal Hacking Networks: 10.6.6.0/24 and 10.7.7.0/24"
echo -e "Your bridge networks:"
ip -c -brie a | grep 10.6.6.1
ip -c -brie a | grep 10.7.7.1

echo -e "
The following are the WebSploit vulnerable containers and associated IP addresses.
+------------------------+------------+
|     Container          | IP Address |
+------------------------+------------+
| webgoat                |  10.6.6.11 |
| juice-shop             |  10.6.6.12 |
| dvwa                   |  10.6.6.13 |
| mutillidae_2           |  10.6.6.14 |
| dvna                   |  10.6.6.15 |
| hackazon               |  10.6.6.16 |
| hackme-rtov            |  10.6.6.17 |
| mayhem                 |  10.6.6.18 |
| rtv-safemode           |  10.6.6.19 |
| galactic-archives      |  10.6.6.20 |
| yascon-hackme          |  10.6.6.21 |
| secretcorp-branch1     |  10.6.6.22 |
| gravemind              |  10.6.6.23 |
| dc30_01                |  10.6.6.24 |
| dc30_01                |  10.6.6.25 |
| y-wing                 |  10.6.6.26 |
| dc31_01                |  10.7.7.21 |
| dc31_02                |  10.7.7.22 |
| dc31_03                |  10.7.7.23 |
+------------------------+------------+ "

echo -e "The following are the \e[92mrunning \e[39mcontainers with their associated ports:"
docker ps --format "table {{.Names}}\t{{.Ports}}\t{{.Status}}"
