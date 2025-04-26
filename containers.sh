#!/bin/bash
# Author: Omar Santos (@santosomar)
# Dynamic script to display running WebSploit containers and their IP addresses.

# Clear the screen
clear

# Header
echo -e "\n\e[96mWebSploit Lab Environment\e[39m"
echo -e "by Omar Santos (@santosomar)"
echo -e "-------------------------------------------"
echo -e "Internal Hacking Networks: \e[93m10.6.6.0/24\e[39m and \e[93m10.7.7.0/24\e[39m\n"

# Show bridge networks
echo -e "Your configured bridge network interfaces:"
ip -c -brie a | grep -E "10\.6\.6\.1|10\.7\.7\.1" || echo -e "\e[91mNo matching interfaces found.\e[39m"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "\n\e[91mDocker is not installed or not in your PATH.\e[39m"
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    echo -e "\n\e[91mDocker is not running. Please start Docker.\e[39m"
    exit 1
fi

# Function to get IP address of a container
get_container_ip() {
    local container_name=$1
    docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$container_name"
}

# List all WebSploit containers (you could filter with a prefix/tag if needed)
echo -e "\n\e[96mDetected WebSploit Containers:\e[39m"
printf "+------------------------+---------------+\n"
printf "| %-22s | %-13s |\n" "Container" "IP Address"
printf "+------------------------+---------------+\n"

# Loop through running containers
docker ps --format "{{.Names}}" | while read -r container; do
    ip=$(get_container_ip "$container")
    if [[ $ip == 10.6.6.* || $ip == 10.7.7.* ]]; then
        printf "| %-22s | %-13s |\n" "$container" "$ip"
    fi
done

printf "+------------------------+---------------+\n"

# Show running containers with ports and status
echo -e "\n\e[96mRunning Containers and Port Mappings:\e[39m"
docker ps --format "table {{.Names}}\t{{.Ports}}\t{{.Status}}"

echo -e "\n\e[92mDone.\e[39m"
