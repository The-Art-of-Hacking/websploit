# WebSploit Labs
WebSploit Labs is a learning environment created by Omar Santos for different Cybersecurity Ethical Hacking, Bug Hunting, Incident Response, Digital Forensics, and Threat Hunting training sessions. WebSploit Labs includes several intentionally vulnerable applications running in Docker containers on top of Kali Linux or Parrot Security OS, several additional tools, and over 9,000 cybersecurity resources.

WebSploit Labs has been used by many colleges and universities in different countries. It comes with over 500 distinct exercises!

You can obtain additional information about WebSploit Labs at: [https://websploit.org](https://websploit.org)

---

## Setting Up WebSploit Labs

### Step 1: Install Kali Linux or Parrot OS
Download and install **Kali Linux** or **Parrot OS** (whichever you prefer) in a virtual machine using the hypervisor of your choice, such as:
- VirtualBox
- VMware Workstation/Fusion
- KVM
- Proxmox (my favorite)

**Minimum VM Requirements:**
- **RAM:** 8 GB
- **CPU:** 2 vCPUs
- **Disk Space:** 50 GB

> ⚡ Tip: Make sure virtualization is enabled in your system BIOS for best performance.

---

### Step 2: Install WebSploit Labs
Once your Kali or Parrot VM is ready, open a terminal and run the following command to set up WebSploit Labs:

```bash
curl -sSL https://websploit.org/install.sh | sudo bash
```

This script will:
- Install all necessary tools
- Set up Docker
- Deploy intentionally vulnerable containers
- Add thousands of cybersecurity resources

---

### Important Notes
- **Apple M1/M2/M3 Macs are not supported** due to compatibility issues with hypervisors and Docker on ARM architecture.
- You can **verify the integrity** of the `install.sh` script by checking its SHA-512 checksum [here](https://websploit.org).
