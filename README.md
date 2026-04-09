# 🎫 Queue Management System (QMS)

A lightweight, Dockerized Queue Management System built with **Flask**, **Socket.IO**, and **SQLite**. This system is optimized for deployment on a Raspberry Pi to serve as a local kiosk or academic assistant.

---

## 🛠️ Prerequisites

* **Hardware:** Raspberry Pi (3, 4, or 5).
* **OS:** Raspberry Pi OS (64-bit recommended).
* **Network:** The Pi and client devices must be on the same local network to access the web interface.

---

## 📥 Step 1: Install Docker on Raspberry Pi

If you haven't installed Docker yet, run these commands in your Raspberry Pi terminal:

```bash
# 1. Update your system
sudo apt update && sudo apt upgrade -y

# 2. Download and run the official Docker install script
curl -fsSL [https://get.docker.com](https://get.docker.com) -o get-docker.sh
sudo sh get-docker.sh

# 3. Add your user to the docker group
sudo usermod -aG docker $USER

# 4. Install Docker Compose
sudo apt install -y docker-compose-plugin

Step 2: Running the QMS App
Prepare your Folder: Ensure your qms folder contains the following files:

app.py

Dockerfile

docker-compose.yml

requirements.txt

qms.db

templates/

static/

Start the System:
Navigate to your project folder and run:

Bash

docker compose up -d --build
Check the Logs:
To ensure everything started correctly and to verify the server status:

Bash

docker compose logs -f
