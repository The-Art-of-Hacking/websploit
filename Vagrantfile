# -*- mode: ruby -*-
# vi: set ft=ruby :

# Vagrant configuration file for setting up a Kali Linux VM with WebSploit Labs installed
Vagrant.configure("2") do |config|

  # Box Settings
  # Use the official Kali Linux rolling release Vagrant box
  config.vm.box = "kalilinux/rolling"

  # Provider Settings (VirtualBox)
  config.vm.provider "virtualbox" do |vb|
    # Enable the VirtualBox GUI during boot (set to 'false' for headless mode)
    vb.gui = true

    # Allocate memory (RAM) for the VM (in MB)
    vb.memory = "4096"

    # Allocate number of CPU cores for the VM
    vb.cpus = 4

    # Optional: Manually assign a private network IP if needed
    # Uncomment the following line if you want to use a static IP address
    # config.vm.network "private_network", ip: "10.1.1.1"
  end

  # Provisioning
  # Automatically run a shell script after the VM is up to install WebSploit Labs
  config.vm.provision "shell", inline: <<-SHELL
    curl -sSL https://websploit.org/install.sh | sudo bash
  SHELL

end
