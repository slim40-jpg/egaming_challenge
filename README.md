# CSTAM — Intelligent eSports Venue Management Platform

CSTAM is an intelligent eSports venue management platform composed of:

- 🎮 **Gaming Agent** — runs on each gaming PC and collects hardware/system information.
- 🖥️ **Local Server** — manages PCs inside the gaming center.
- ☁️ **Cloud Server** — manages users and reservations.
- 🗄️ **PostgreSQL** — stores application data.
- 🌐 **Frontend** — web interface for users and administrators.
- 🔗 **ngrok** — exposes the cloud server when external access is required.

---

# 1. Architecture

The project is divided into two main parts:

```text
                    INTERNET
                       │
                       ▼
                    ngrok
                       │
                       ▼
                Cloud Server
                   :5000
                       │
                       ▼
                PostgreSQL
                  cloud_db
                       ▲
                       │
                 HTTP / HTTPS
                       │
                       ▼
                Local Server
                   :8003
                       │
                ┌──────┴──────┐
                │             │
                ▼             ▼
          Gaming Agent    Gaming Agent
             PC 1            PC 2
```

The local server communicates with the gaming PCs through the local network.

The gaming agent must run **directly on the gaming PC**, while the backend services run inside Docker.

---

# 2. Requirements

Before launching the project, install:

- Docker Desktop
- Docker Compose
- PowerShell
- Git
- The CSTAM Gaming Agent executable

Make sure Docker Desktop is running before starting the project.

Check Docker:

```powershell
docker --version
docker compose version
```

---

# 3. Project Structure

The important parts of the project are:

```text
egaming_challenge_cstam/
│
├── server/
│   ├── server.py
│   ├── models.py
│   └── ...
│
├── cloud_server/
│   ├── cloud_server.py
│   ├── models.py
│   └── ...
│
├── egaming-frontend/
│   ├── app/
│   ├── public/
│   ├── package.json
│   └── Dockerfile
│
├── gaming_agent/
│   └── gaming_agent.exe
│
├── docker-compose.yml
├── start.ps1
├── .env
└── README.md
```

---

# 4. Configuration

Before the first launch, configure the root `.env` file.

Example:

```env
LAN_IP=192.168.100.48
NGROK_AUTH_TOKEN=YOUR_NGROK_AUTH_TOKEN
```

## LAN_IP

`LAN_IP` must be the IP address of the computer running the CSTAM local server.

To find it:

```powershell
ipconfig
```

Look for the IPv4 address of the network adapter connected to the gaming-center network.

Example:

```text
IPv4 Address. . . . . . . . . . . : 192.168.100.48
```

Then:

```env
LAN_IP=192.168.100.48
```

Do not use the Docker IP such as:

```text
172.x.x.x
```

The gaming agents need the computer's actual LAN address.

---

# 5. Launching the Project

The project should be launched using **two terminals**.

## Terminal 1 — Gaming Agent

The Gaming Agent runs directly on the gaming PC.

Open PowerShell and go to the Gaming Agent directory:

```powershell
cd .\gaming_agent
```

Then launch the agent:

```powershell
.\gaming_agent.exe
```

The agent should start listening for the local server discovery message.

You should see messages similar to:

```text
[discovery] listening on UDP :9000
```

and later:

```text
SERVER:192.168.100.48:8003
```

The agent will then communicate with the local server.

### Important

Do **not** run the Gaming Agent inside Docker.

The agent needs direct access to the gaming PC's:

- CPU
- GPU
- RAM
- running processes
- window information
- installed games
- system state

Therefore, it runs directly on Windows.

---

# 6. Terminal 2 — Start Docker Services

Open a second PowerShell window.

Go to the project root:

```powershell
cd C:\Users\<USERNAME>\OneDrive\Documents\egaming_challenge_cstam
```

Then launch the project:

```powershell
.\start.ps1
```

The startup script is responsible for launching the Docker services.

Alternatively, if needed, Docker Compose can be started manually:

```powershell
docker compose up -d db cloud local frontend ngrok
```

---

# 7. Docker Services

The project uses several Docker services.

Check their status with:

```powershell
docker compose ps
```

You should see services similar to:

```text
NAME                         STATUS
gaming-db                    Up
gaming-cloud                 Up
gaming-local                 Up
egaming-frontend             Up
ngrok                        Up
```

The exact container names may differ depending on the Docker Compose configuration.

---

# 8. Accessing the Application

Once all services are running, the frontend is available on:

```text
http://localhost:3000
```

Open it in a browser:

```text
http://localhost:3000
```

The local backend runs on:

```text
http://<LAN_IP>:8003
```

For example:

```text
http://192.168.100.48:8003
```

The cloud backend runs internally on:

```text
http://cloud:5000
```

inside the Docker network.

If ngrok is enabled, the cloud server can also be accessed through the generated ngrok URL.

---

# 9. Verify the Gaming Agent

After starting both terminals, check the local server logs:

```powershell
docker compose logs -f local
```

You should see the agent being discovered and communicating with the local server.

Typical messages include:

```text
[discovery] broadcasting "SERVER:192.168.100.48:8003" on UDP :9000
```

and heartbeat requests:

```text
POST /api/heartbeat HTTP/1.1" 200
```

You can also check the agent's terminal.

The agent should send information such as:

```text
PC ID
Hostname
IP address
CPU usage
GPU usage
RAM usage
CPU temperature
GPU temperature
Current window
Installed games
```

---

# 10. Database

PostgreSQL runs inside Docker.

The project uses separate databases for the local and cloud components.

```text
PostgreSQL
│
├── gaming_house
│   └── Local server data
│
└── cloud_db
    └── Cloud server data
```

The PostgreSQL data is stored in a Docker volume.

Therefore, normally **do not delete Docker volumes** when restarting the project.

For example, avoid:

```powershell
docker compose down -v
```

because `-v` removes the Docker volumes and can delete the PostgreSQL data.

To stop the project without deleting the database:

```powershell
docker compose down
```

Then restart it with:

```powershell
docker compose up -d
```

---

# 11. Useful Docker Commands

## Start everything

```powershell
.\start.ps1
```

or:

```powershell
docker compose up -d
```

## Stop everything

```powershell
docker compose down
```

## Check running containers

```powershell
docker compose ps
```

## View all logs

```powershell
docker compose logs -f
```

## View local server logs

```powershell
docker compose logs -f local
```

## View cloud server logs

```powershell
docker compose logs -f cloud
```

## View frontend logs

```powershell
docker compose logs -f frontend
```

## View PostgreSQL logs

```powershell
docker compose logs -f db
```

## Rebuild the project

```powershell
docker compose up -d --build
```

If you only changed the frontend:

```powershell
docker compose up -d --build frontend
```

If you only changed the local server:

```powershell
docker compose up -d --build local
```

If you only changed the cloud server:

```powershell
docker compose up -d --build cloud
```

---

# 12. Restarting After Code Changes

After modifying backend code:

```powershell
docker compose up -d --build local cloud
```

After modifying frontend code:

```powershell
docker compose up -d --build frontend
```

After modifying Docker configuration:

```powershell
docker compose down
docker compose up -d --build
```

The Gaming Agent does not need Docker rebuilding because it runs directly on Windows.

Restart the agent if its executable or configuration changes.

---

# 13. Troubleshooting

## Docker is not running

If you see errors related to Docker Engine or BuildKit:

1. Open Docker Desktop.
2. Wait until Docker is fully started.
3. Check:

```powershell
docker info
```

Then retry:

```powershell
.\start.ps1
```

---

## Port 3000 is already in use

Check which process is using port 3000:

```powershell
netstat -ano | findstr :3000
```

You can also check Docker containers:

```powershell
docker ps
```

Stop the container using the port if appropriate.

---

## Port 8003 is already in use

Check:

```powershell
netstat -ano | findstr :8003
```

Make sure another local instance of the CSTAM server is not already running.

---

## Gaming Agent cannot find the server

Check the server logs:

```powershell
docker compose logs -f local
```

You should see:

```text
SERVER:<LAN_IP>:8003
```

Example:

```text
SERVER:192.168.100.48:8003
```

Check that the Gaming Agent and the Docker host are connected to the same LAN.

Also verify Windows Firewall rules if necessary.

---

## Agent is running but no PC appears

Verify that the agent is sending heartbeats.

The local server should show:

```text
POST /api/heartbeat ... 200
```

If the agent cannot communicate with the server, check:

- LAN connectivity
- `LAN_IP`
- UDP port `9000`
- TCP port `8003`
- Windows Firewall

---

## Frontend cannot connect to the backend

Check:

```powershell
docker compose ps
```

Then:

```powershell
docker compose logs -f local
```

and:

```powershell
docker compose logs -f cloud
```

A frontend error such as:

```text
Unexpected token '<'
```

often means that the backend returned an HTML error page instead of the expected JSON response.

Check the backend logs for the actual error.

---

# 14. Normal Startup Procedure

For a normal development session:

### Terminal 1

```powershell
cd .\gaming_agent
.\gaming_agent.exe
```

Keep this terminal running.

### Terminal 2

```powershell
cd C:\Users\<USERNAME>\OneDrive\Documents\egaming_challenge_cstam
.\start.ps1
```

Then open:

```text
http://localhost:3000
```

You now have:

```text
Terminal 1
└── Gaming Agent
       │
       │ UDP discovery :9000
       │ HTTP heartbeat
       ▼
Terminal 2
└── Docker Compose
       ├── Local Server :8003
       ├── Cloud Server :5000
       ├── PostgreSQL
       ├── Frontend :3000
       └── ngrok
```

---

# 15. Quick Start

For someone who already configured `.env`:

**Terminal 1:**

```powershell
cd .\gaming_agent
.\gaming_agent.exe
```

**Terminal 2:**

```powershell
on the root directory of the project
.\start.ps1
```

Then open:

```text
http://localhost:3000
```

That's it.
