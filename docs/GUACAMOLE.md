# Apache Guacamole Integration & Remote Access Protocol

## Overview

Apache Guacamole is an HTML5 clientless remote desktop gateway. In Cloud4Green Nexus, Guacamole is integrated directly into the core platform using a dedicated `guacd` proxy daemon and an in-backend protocol tunnel.

---

## Connection Sequence

```
User Browser                  Nexus Backend API              guacd (Port 4822)           Target VM
     |                               |                              |                        |
     | 1. GET /vms/{id}/remote-status |                              |                        |
     |------------------------------>|                              |                        |
     | 2. Status: can_connect=true   |                              |                        |
     |<------------------------------|                              |                        |
     |                               |                              |                        |
     | 3. WS Connect /guac-ws?token  |                              |                        |
     |------------------------------>|                              |                        |
     |                               | 4. Validate user assignment  |                        |
     |                               |    & decrypt credentials     |                        |
     |                               |                              |                        |
     |                               | 5. TCP Connect               |                        |
     |                               |----------------------------->|                        |
     |                               | 6. select,rdp;               |                        |
     |                               |----------------------------->|                        |
     |                               | 7. args,hostname,port,...;   |                        |
     |                               |<-----------------------------|                        |
     |                               | 8. size,audio,image,...;     |                        |
     |                               |    connect,192.168.1.50,...; |                        |
     |                               |----------------------------->|                        |
     |                               |                              | 9. Native RDP/SSH/VNC  |
     |                               |                              |----------------------->|
     |                               | 10. ready,$session-id;       |                        |
     |                               |<-----------------------------|                        |
     | 11. WS Accept + ready instr   |                              |                        |
     |<------------------------------|                              |                        |
     |                               |                              |                        |
     | 12. Bi-directional Guacamole  |  13. Stream raw instructions |                        |
     |     Instructions (sync, mouse,|      between WebSocket and   |                        |
     |     key, rect, png, etc.)     |      guacd TCP socket        |                        |
     |<=============================>|<============================>|<======================>|
```

---

## Supported Protocols & Parameters

### 1. Windows Remote Desktop (RDP)
- **Protocol**: `rdp`
- **Default Port**: `3389`
- **Parameters**:
  - `hostname`: Target IP address or hostname
  - `port`: RDP port
  - `username`: Windows local or domain username
  - `password`: Decrypted password
  - `domain`: Windows domain (optional)
  - `security`: `any` | `nla` | `tls` | `rdp`
  - `ignore-cert`: `true` (allows self-signed certificates on internal enterprise networks)
  - `color-depth`: 24-bit TrueColor
  - `resize-method`: `display-update` (dynamic client display resolution adjustment)
  - `enable-audio`: `true`
  - `enable-font-smoothing`: `true`

### 2. Secure Shell (SSH)
- **Protocol**: `ssh`
- **Default Port**: `22`
- **Parameters**:
  - `hostname`: Target IP address
  - `port`: SSH port
  - `username`: Linux username
  - `password`: Decrypted password (for password authentication)
  - `private-key`: Decrypted PEM private key (for key-based authentication)
  - `passphrase`: Decrypted passphrase (if private key is encrypted)
  - `font-name`: Monospace font
  - `font-size`: 14px
  - `color-scheme`: `black-white`

### 3. Virtual Network Computing (VNC)
- **Protocol**: `vnc`
- **Default Port**: `5900`
- **Parameters**:
  - `hostname`: Target IP address
  - `port`: VNC display port
  - `password`: Decrypted VNC password
  - `color-depth`: 24-bit

---

## Security Guarantees

1. **No Credentials in Frontend**: Passwords, private keys, and passphrases are NEVER returned by any API endpoint or sent to client browsers.
2. **Anti-IDOR Enforcement**: Every remote connection attempt performs database authorization checks. If an attacker attempts to connect to `/api/v1/vms/999/guac-ws`, the backend closes the WebSocket with error code `4404` or `4401`.
3. **Internal Network Isolation**: `guacd` communicates with target VMs inside the local network or VLAN. The target VM's RDP/SSH ports do not need to be exposed to the public internet.
