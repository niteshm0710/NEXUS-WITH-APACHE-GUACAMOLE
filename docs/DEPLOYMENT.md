# Production Deployment Guide

## Prerequisites

- Linux or macOS server with **Docker** (24.0+) and **Docker Compose** (v2.20+)
- Port `80` (or `3001`) and port `443` open for web traffic
- Target virtual machines reachable over internal network / VLAN from the Docker host

---

## 1. Clone & Setup Environment

```bash
# Clone the repository
git clone <NEW_REPOSITORY_URL>
cd "NEXUS WITH APACHE GUACAMOLE"

# Create production environment file from template
cp .env.example .env
```

Edit `.env` and configure your secure values:

```bash
# Generate a secure 64-character secret key:
openssl rand -hex 32

# Configure database credentials:
POSTGRES_USER=nexus
POSTGRES_PASSWORD=your-secure-postgres-password-here
DATABASE_URL=postgresql://nexus:your-secure-postgres-password-here@db:5432/nexus

# Configure initial administrator:
ADMIN_EMAIL=admin@yourcompany.com
ADMIN_PASSWORD=your-secure-admin-password-min-12-chars

# Guacamole Daemon Configuration:
GUACD_HOST=guacd
GUACD_PORT=4822
```

---

## 2. Launch Services with Docker Compose

```bash
docker compose up -d --build
```

Verify all 4 services are healthy:

```bash
docker compose ps
```

Expected output:
- `nexus-db`: Up (healthy)
- `nexus-guacd`: Up
- `nexus-backend`: Up
- `nexus-frontend`: Up

---

## 3. Initial Access & Verification

1. Open your browser and navigate to `http://<server-ip>:3001` (or your configured domain).
2. Sign in with the `ADMIN_EMAIL` and `ADMIN_PASSWORD` defined in `.env`.
3. Go to **Overview** to verify `guacd` connectivity status.
4. Go to **Virtual Machines** and click **Sync VMware Inventory** (if VMware is enabled).
5. For each VM that needs remote access, click the **Settings** icon on the VM card to configure RDP, SSH, or VNC credentials.
6. Create standard user accounts under the **Users** tab.
7. Assign VMs to users under the **Assignments** tab.
8. Log in as a standard user:
   - Verify you see only your assigned VMs.
   - Click the green **CONNECT** button to start your browser-based remote session!

