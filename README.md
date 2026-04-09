🎫 Queue Management System (QMS)A lightweight, Dockerized academic assistant kiosk designed to run on a Raspberry Pi using Flask, SocketIO, and SQLite.🛠 PrerequisitesHardware: Raspberry Pi (Recommended: RPi 4 or 5 with 64-bit OS).OS: Raspberry Pi OS (64-bit is highly recommended for Docker compatibility).Network: Both the Pi and the devices accessing it must be on the same Wi-Fi/LAN.📥 Step 1: Install Docker on Raspberry PiRun these commands in your Raspberry Pi terminal to install Docker and Docker Compose.Bash# Update the system
sudo apt update && sudo apt upgrade -y

# Download and run the official Docker install script
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to the docker group so you don't need 'sudo' every time
sudo usermod -aG docker $USER

# Install Docker Compose dependencies
sudo apt install -y libffi-dev python3-pip
sudo pip3 install docker-compose
Note: You may need to logout and log back in (or restart the Pi) for the usermod changes to take effect.🚀 Step 2: Running the QMS AppTransfer the Files: Move your qms folder to the Raspberry Pi.Navigate to the folder:Bashcd qms
Start the Container:Run the following command. This will build your Python environment and start the database.Bashdocker compose up -d --build
🖥️ How to Access the SystemOnce the logs show wsgi starting up, you can access the interface using your Pi's IP address.Admin/Login: http://<YOUR_PI_IP>:5002/Public Join Page: http://<YOUR_PI_IP>:5002/joinDisplay Screen: http://<YOUR_PI_IP>:5002/displayTip: To find your Raspberry Pi's IP address, type hostname -I in the terminal.📝 Maintenance CommandsActionCommandView Live Logsdocker compose logs -fUpdate Code Changesdocker compose up -d --buildStop the Appdocker compose downCheck Statusdocker compose psCheck Resource Usagedocker stats📁 Project Structureapp.py: Main Flask application logic.qms.db: SQLite database file (Persistent via Docker volumes).templates/: HTML files for the UI.static/: CSS and generated QR codes.Dockerfile: Instructions for the Python container.docker-compose.yml: Orchestration for the app and networking.
