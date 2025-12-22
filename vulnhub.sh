#!/bin/bash

# vulnhub.sh - A menu-driven script to manage Vulhub exercises
# Location: websploit/vulnhub.sh

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

VULHUB_REPO="https://github.com/vulhub/vulhub.git"
VULHUB_DIR="./vulhub"

# Helper: Print banner
function print_banner() {
    clear
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}       Vulhub Exercise Manager          ${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Helper: Check dependencies
function check_deps() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: docker is not installed.${NC}"
        exit 1
    fi
    if ! command -v git &> /dev/null; then
        echo -e "${RED}Error: git is not installed.${NC}"
        exit 1
    fi
}

# Helper: Ensure Vulhub is cloned
function ensure_vulhub() {
    if [ ! -d "$VULHUB_DIR" ]; then
        echo -e "${YELLOW}Vulhub repository not found in $VULHUB_DIR${NC}"
        read -p "Do you want to clone it now? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${GREEN}Cloning Vulhub...${NC}"
            git clone "$VULHUB_REPO" "$VULHUB_DIR"
        else
            echo -e "${RED}Vulhub is required. Exiting.${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}Vulhub repository found.${NC}"
        read -p "Do you want to pull the latest changes? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            cd "$VULHUB_DIR" && git pull && cd ..
        fi
    fi
}

# Helper: List apps (directories in vulhub root)
function list_apps() {
    # Find directories, ignore hidden/base files
    apps=($(ls -d "$VULHUB_DIR"/*/ | xargs -n 1 basename | grep -vE "^(\.|base|docker-compose)"))
}

# Helper: List vulnerabilities for an app
function list_vulns() {
    local app=$1
    vulns=($(ls -d "$VULHUB_DIR/$app"/*/ | xargs -n 1 basename))
}

# Main Menu
function main_menu() {
    while true; do
        print_banner
        echo -e "${YELLOW}Available Applications:${NC}"
        
        list_apps
        
        PS3="Select an application (or 'q' to quit): "
        select app in "${apps[@]}"; do
            if [[ "$REPLY" == "q" ]]; then
                exit 0
            elif [[ -n "$app" ]]; then
                app_menu "$app"
                break
            else
                echo -e "${RED}Invalid selection.${NC}"
            fi
        done
    done
}

# App Menu
function app_menu() {
    local app=$1
    while true; do
        print_banner
        echo -e "Application: ${GREEN}$app${NC}"
        echo -e "${YELLOW}Available Vulnerabilities:${NC}"
        
        list_vulns "$app"
        
        if [ ${#vulns[@]} -eq 0 ]; then
            echo -e "${RED}No vulnerabilities found for $app.${NC}"
            read -p "Press Enter to go back..."
            return
        fi

        PS3="Select a vulnerability (or 'b' to back, 'q' to quit): "
        select vuln in "${vulns[@]}"; do
            if [[ "$REPLY" == "q" ]]; then
                exit 0
            elif [[ "$REPLY" == "b" ]]; then
                return
            elif [[ -n "$vuln" ]]; then
                vuln_action_menu "$app" "$vuln"
                break 
            else
                echo -e "${RED}Invalid selection.${NC}"
            fi
        done
    done
}

# Action Menu
function vuln_action_menu() {
    local app=$1
    local vuln=$2
    local target_dir="$VULHUB_DIR/$app/$vuln"
    
    while true; do
        print_banner
        echo -e "Target: ${GREEN}$app/$vuln${NC}"
        echo -e "Directory: $target_dir"
        echo
        echo -e "1) ${GREEN}Start Lab${NC} (docker compose up -d)"
        echo -e "2) ${RED}Stop Lab${NC} (docker compose down)"
        echo -e "3) View Logs (docker compose logs)"
        echo -e "4) View README (cat README.md)"
        echo -e "5) Shell Access (if applicable)"
        echo -e "b) Back to Vulnerabilities"
        echo -e "q) Quit"
        
        read -p "Select an action: " action
        
        case $action in
            1)
                echo -e "${GREEN}Starting lab...${NC}"
                (cd "$target_dir" && docker compose up -d)
                read -p "Press Enter to continue..."
                ;;
            2)
                echo -e "${RED}Stopping lab...${NC}"
                (cd "$target_dir" && docker compose down)
                read -p "Press Enter to continue..."
                ;;
            3)
                (cd "$target_dir" && docker compose logs)
                read -p "Press Enter to continue..."
                ;;
            4)
                if [ -f "$target_dir/README.md" ]; then
                    # Use less if available, else cat
                    if command -v less &> /dev/null; then
                        less "$target_dir/README.md"
                    else
                        cat "$target_dir/README.md"
                    fi
                else
                    echo -e "${RED}No README.md found.${NC}"
                fi
                read -p "Press Enter to continue..."
                ;;
            5)
                # Attempt to find a running container for this lab and exec into it
                # This is tricky as we don't know the service name, usually 'web' or similar.
                # We'll list containers and ask user.
                echo -e "${YELLOW}Running containers for this project:${NC}"
                (cd "$target_dir" && docker compose ps)
                read -p "Enter service name to exec into (e.g. web) or empty to cancel: " svc
                if [ -n "$svc" ]; then
                     (cd "$target_dir" && docker compose exec "$svc" /bin/bash || docker compose exec "$svc" /bin/sh)
                fi
                ;;
            b)
                return
                ;;
            q)
                exit 0
                ;;
            *)
                echo -e "${RED}Invalid option.${NC}"
                sleep 1
                ;;
        esac
    done
}

# --- Main Execution ---
check_deps
ensure_vulhub
main_menu

