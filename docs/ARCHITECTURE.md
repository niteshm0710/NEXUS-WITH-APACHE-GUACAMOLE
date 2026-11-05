# System Architecture — Cloud4Green Nexus with Apache Guacamole

## Overview

Cloud4Green Nexus with Apache Guacamole is an enterprise-grade virtualization and browser-based remote access gateway. It unifies VMware vSphere / ESXi infrastructure management with clientless, high-performance remote desktop (RDP), terminal (SSH), and graphical session (VNC) access directly in any modern web browser.

---

## Architectural Diagram

```
+-------------------------------------------------------------------------+
|                              Web Browser                                |
|  - React 18 + TypeScript + Tailwind CSS                                 |
|  - Guacamole.Client & Guacamole.WebSocketTunnel (guacamole-common-js)    |
+------------------------------------+------------------------------------+
                                     |
                                     | HTTPS / WSS
                                     v
+-------------------------------------------------------------------------+
|                        Nginx Reverse Proxy / Port 80                    |
|  - Serves static compiled SPA assets                                    |
|  - Proxies /api/ and /api/v1/.../guac-ws to Nexus Backend               |
+------------------------------------+------------------------------------+
                                     |
                                     | HTTP / WS (Internal Network)
                                     v
+-------------------------------------------------------------------------+
|                   Cloud4Green Nexus Backend (FastAPI)                   |
|                                                                         |
|  [ Auth & Security ]                                                    |
|  - Argon2id Password Hasher                                             |
|  - JWT Access Tokens & Refresh Session Token Rotations                  |
|  - AES-256 (Fernet) Encryption of Remote Credentials                    |
|                                                                         |
|  [ Authorization & Anti-IDOR Engine ]                                   |
|  - Strict Role-Based Access Control (Admin vs Standard User)            |
|  - Server-side VM Assignment Verification on every request              |
|                                                                         |
|  [ Guacamole Protocol Broker & WebSocket Tunnel ]                       |
|  - Decrypts target VM credentials in memory only                        |
|  - Async TCP client to guacd daemon                                     |
|  - Native Guacamole protocol instruction parser & encoder               |
|                                                                         |
|  [ VMware Integration Engine ]                                          |
|  - pyVmomi SmartConnect over TLS/SSL                                    |
|  - Real inventory sync with stable UUID deduplication                   |
|  - Power state control (start / stop / restart)                         |
+-------------------+---------------------------------+-------------------+
                    |                                 |
                    | Guacamole Protocol              | PostgreSQL
                    | TCP 4822 (Internal)             | TCP 5432
                    v                                 v
+---------------------------------------+   +-----------------------------+
|   Apache Guacamole Proxy (guacd)      |   |       PostgreSQL 16         |
|  - Offloads RDP, SSH, and VNC stacks  |   |  - Users & Roles            |
|  - Renders visual frames to stream    |   |  - Virtual Machines         |
|  - Decodes client input events        |   |  - Encrypted Remote Configs |
+-------------------+-------------------+   |  - Assignments & Audit Logs |
                    |                       +-----------------------------+
                    | RDP (3389) / SSH (22) / VNC (5900)
                    v
+-------------------------------------------------------------------------+
|                  Target Virtual Machine (LAN / VLAN)                    |
|  - Windows / Windows Server (RDP)                                       |
|  - Linux / Ubuntu / Debian / RHEL (SSH)                                 |
|  - Graphical Workstations (VNC)                                         |
+-------------------------------------------------------------------------+
```

---

## Component Responsibilities

### 1. Frontend Web Application (`frontend/`)
- Single Page Application built with React 18, Vite, and Tailwind CSS.
- Integrates `guacamole-common-js` to render the remote canvas.
- Captures mouse, keyboard, and touch events and sends them through the Guacamole WebSocket tunnel.
- Provides accessibility controls: Send Ctrl+Alt+Del, Send Escape, Send Tab, Fullscreen, and Display Scaling.
- Dynamically adapts OS visual badges (Windows Server, Windows, Ubuntu, Enterprise Linux, macOS, ESXi, Generic VM).

### 2. Backend Gateway (`backend/app/`)
- High-performance asynchronous API powered by FastAPI and Uvicorn.
- **Strict Authorization**: Validates permissions server-side on every API call and WebSocket handshake (users can NEVER access another user's machine by tampering with IDs or parameters).
- **Credential Protection**: Remote passwords and SSH private keys are encrypted using symmetric Fernet keys derived from `SECRET_KEY` and never exposed to the frontend.
- **guacd WebSocket Tunnel**: Bi-directional asynchronous forwarding between browser WebSockets and `guacd` TCP socket.

### 3. Apache Guacamole Proxy (`guacd`)
- Native C daemon maintained by the Apache Software Foundation.
- Translates client-side Guacamole instructions into native remote desktop protocols (FreeRDP, libssh2, libvncclient).
- Runs securely in container isolation without exposing target protocol ports to the public internet.

### 4. Data Layer (`PostgreSQL 16`)
- Persistent relational database with indexed tables and foreign key constraints.
- Prevents VM record duplication across synchronization runs using unique hardware UUIDs.
- Enforces unique user assignments via composite unique keys (`user_id`, `vm_id`).

