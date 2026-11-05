# Cloud4Green Nexus with Apache Guacamole

> Enterprise Virtualization & Browser-Based Remote Access Gateway

Cloud4Green Nexus with Apache Guacamole is a production-ready infrastructure portal that combines live VMware vCenter / ESXi virtual machine inventory with secure, clientless, browser-based remote access (RDP, SSH, and VNC) powered by Apache Guacamole.

---

## Key Features

- **Apache Guacamole Browser-Based Remote Access**:
  - Connect to Windows VMs via **RDP** (FreeRDP engine).
  - Connect to Linux VMs via **SSH** with interactive terminal.
  - Connect to graphical workstations via **VNC**.
  - No client plugins, software, or VPNs required — runs directly in modern web browsers.
  - Interactive toolbar with Ctrl+Alt+Del injection, key transmission, fullscreen, and responsive display scaling.
- **Enterprise Security & Anti-IDOR Authorization**:
  - Strict server-side authorization: Standard users can **only** view and access virtual machines explicitly assigned to them by administrators.
  - Sensitive passwords, private keys, and vCenter secrets are encrypted using AES-256 (Fernet) server-side and never leaked to the frontend.
  - Immutable audit logs and remote session tracking.
- **Real VMware vCenter / ESXi Integration**:
  - Automatic hardware and power state discovery via `pyVmomi`.
  - Duplicate VM prevention using persistent hardware UUID deduplication.
  - Live power operations (Power On, Power Off, Reset).
- **OS-Specific Visual Identities**:
  - Distinctive visual badges and icons for Windows Server, Windows 10/11, Ubuntu, Linux (Debian/CentOS/RHEL), macOS, and VMware ESXi.
- **Zero Dummy Data Guarantee**:
  - Clean, professional empty states when real infrastructure is not yet connected. No fake metrics, mock logs, or placeholder production records.
- **Production Container Architecture**:
  - Docker Compose orchestration with isolated services: Frontend (Nginx), Backend (FastAPI), Apache Guacamole daemon (`guacd`), and PostgreSQL 16.

---

## Target Workflow

```
User logs into Cloud4Green Nexus
        ↓
System authenticates user (Argon2id + JWT)
        ↓
User sees ONLY their assigned virtual machines
        ↓
User selects a VM
        ↓
Backend verifies authorization (Anti-IDOR)
        ↓
User clicks CONNECT
        ↓
Nexus negotiates secure session with Apache Guacamole (guacd)
        ↓
User interacts with VM desktop/terminal in the browser
```

---

## Quickstart (Development & Local Test)

### 1. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run test suite
pytest tests -v

# Start development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend

```bash
cd frontend
npm install
npm run build
npm run dev
```

The web application will be accessible at `http://localhost:3001`.

---

## Production Deployment (Docker Compose)

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Configure production passwords in .env
# Edit POSTGRES_PASSWORD, SECRET_KEY, ADMIN_PASSWORD, etc.

# 3. Start all services
docker compose up -d --build
```

---

## Documentation

- [Architecture Overview](docs/ARCHITECTURE.md)
- [Apache Guacamole Integration Guide](docs/GUACAMOLE.md)
- [VMware vCenter Integration](docs/VMWARE.md)
- [Production Deployment Guide](docs/DEPLOYMENT.md)

---

## License

Proprietary & Confidential — Cloud4green Technologies. All rights reserved.

