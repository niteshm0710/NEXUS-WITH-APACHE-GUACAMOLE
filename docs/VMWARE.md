# VMware vCenter & ESXi Integration Guide

## Overview

Cloud4Green Nexus integrates with VMware vSphere 7.x, 8.x, and standalone ESXi hosts via VMware's official `pyVmomi` Python SDK.

---

## Capabilities

1. **Inventory Synchronization**:
   - Discovers all powered-on, powered-off, and suspended virtual machines.
   - Extracts hardware specifications: vCPUs, configured RAM, committed storage, active IP address, ESXi host placement, and datastore.
   - Automatically detects Guest Operating System and maps it to platform visual identities.

2. **Duplicate VM Prevention**:
   - VMware virtual machines have persistent hardware UUIDs (`config.instanceUuid` and `config.uuid`).
   - The synchronization engine uses the hardware UUID as a natural key in PostgreSQL (`virtual_machines.uuid` with unique constraint).
   - Subsequent sync operations update existing VM attributes in place and never create duplicate database rows.

3. **Power Lifecycle Operations**:
   - `start`: Powers on the virtual machine via `PowerOnVM_Task()`.
   - `stop`: Powers off the virtual machine via `PowerOffVM_Task()`.
   - `restart`: Reboots the virtual machine via `ResetVM_Task()`.

---

## Configuration via Admin Portal

1. Log in as an Administrator.
2. Navigate to **Admin -> VMware Infrastructure**.
3. Enter your vCenter Host / IP, administrative username, and password.
4. Toggle **Verify TLS** (leave checked for production hosts with valid certificates; uncheck if connecting to internal development hosts with self-signed certificates).
5. Click **Test & Save Connection**.
6. Click **Sync VMware Inventory** to synchronize all virtual machines into Cloud4Green Nexus.

