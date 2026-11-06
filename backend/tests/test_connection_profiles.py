import pytest
from app import models as m, security as sec

def test_connection_profiles_management_and_auto_resolution(client, db, admin_headers, user1_headers):
    # 1. Create a shared Windows Connection Profile
    win_profile_payload = {
        "name": "Default Windows Fleet Policy",
        "description": "Enterprise Domain Policy for Windows Server VMs",
        "os_family": "windows",
        "protocol": "rdp",
        "port": 3389,
        "username": "Administrator",
        "password": "WinSecurePassword123!",
        "domain": "vclass.local",
        "security": "any",
        "ignore_cert": True,
        "is_default": True
    }
    res = client.post("/api/v1/admin/connection-profiles", headers=admin_headers, json=win_profile_payload)
    assert res.status_code == 200
    p_data = res.json()
    assert p_data["name"] == "Default Windows Fleet Policy"
    assert p_data["has_password"] is True
    assert "password" not in p_data  # Never leaked

    # 2. Create a Windows VM without per-VM credentials, but with discovered IP
    win_vm = m.VirtualMachine(
        uuid="vm-win-auto-1",
        name="Win_DC_AutoTest",
        guest_os="Windows Server 2022 (64-bit)",
        power_state="on",
        ip_address="192.168.0.3"
    )
    db.add(win_vm)
    db.commit()

    user1 = db.query(m.User).filter_by(email="user1@nexus.test").first()
    db.add(m.VmAssignment(user_id=user1.id, vm_id=win_vm.id))
    db.commit()

    # 3. Standard user checks remote-status: Automatically resolved from shared policy!
    status_res = client.get(f"/api/v1/vms/{win_vm.id}/remote-status", headers=user1_headers)
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["configured"] is True
    assert status_data["can_connect"] is True
    assert status_data["protocol"] == "rdp"
    assert status_data["host"] == "192.168.0.3"
    assert status_data["port"] == 3389
    assert status_data["profile_name"] == "Default Windows Fleet Policy"
    assert status_data["source_type"] == "shared_profile"
    assert "password" not in status_data

    # 4. Normal users list VMs: remote_access indicates one-click ready
    vms_res = client.get("/api/v1/vms", headers=user1_headers)
    assert vms_res.status_code == 200
    vm_item = next(v for v in vms_res.json() if v["id"] == win_vm.id)
    assert vm_item["remote_access"]["configured"] is True
    assert vm_item["remote_access"]["can_connect"] is True
    assert vm_item["remote_access"]["protocol"] == "rdp"
    assert vm_item["remote_access"]["profile_name"] == "Default Windows Fleet Policy"

    # 5. Overriding with per-VM custom config takes precedence
    override_payload = {
        "protocol": "rdp",
        "host": "192.168.0.33",
        "port": 3390,
        "username": "custom_admin",
        "password": "CustomPassword!",
        "domain": "CUSTOM_DOMAIN",
        "security": "nla",
        "ignore_cert": True,
        "is_active": True
    }
    save_res = client.put(f"/api/v1/admin/vms/{win_vm.id}/remote-config", headers=admin_headers, json=override_payload)
    assert save_res.status_code == 200

    # Check status again: per-VM override is used
    status_res2 = client.get(f"/api/v1/vms/{win_vm.id}/remote-status", headers=user1_headers)
    assert status_res2.status_code == 200
    status_data2 = status_res2.json()
    assert status_data2["port"] == 3390
    assert status_data2["host"] == "192.168.0.33"
    assert status_data2["source_type"] == "per_vm"


def test_user_one_click_assigned_vm_connect_flow(client, db, admin_headers, user1_headers, user2_headers):
    """Verifies that a standard user (role: 'user'):
    1. Only sees VMs assigned to them.
    2. Receives one-click resolvable connection status without having to provide IP/port/credentials.
    3. Cannot access any VM assigned to another user (anti-IDOR).
    4. Profile credentials and sensitive data are strictly protected.
    """
    # Create Linux Profile
    res = client.post("/api/v1/admin/connection-profiles", headers=admin_headers, json={
        "name": "Default Linux Fleet Policy",
        "description": "Ubuntu and Debian Fleet Policy",
        "os_family": "linux",
        "protocol": "ssh",
        "port": 22,
        "username": "ubuntu",
        "password": "UbuntuFleetPassword!",
        "is_default": True
    })
    assert res.status_code == 200

    # Create 2 VMs
    linux_vm1 = m.VirtualMachine(
        uuid="vm-linux-101",
        name="User1_Ubuntu_Server",
        guest_os="Ubuntu Linux (64-bit)",
        power_state="on",
        ip_address="192.168.0.18"
    )
    linux_vm2 = m.VirtualMachine(
        uuid="vm-linux-102",
        name="User2_Ubuntu_Server",
        guest_os="Ubuntu Linux (64-bit)",
        power_state="on",
        ip_address="192.168.0.19"
    )
    db.add_all([linux_vm1, linux_vm2])
    db.commit()

    user1 = db.query(m.User).filter_by(email="user1@nexus.test").first()
    user2 = db.query(m.User).filter_by(email="user2@nexus.test").first()

    # Assign vm1 to user1, vm2 to user2
    db.add(m.VmAssignment(user_id=user1.id, vm_id=linux_vm1.id))
    db.add(m.VmAssignment(user_id=user2.id, vm_id=linux_vm2.id))
    db.commit()

    # User 1 lists VMs: sees ONLY vm1
    u1_vms = client.get("/api/v1/vms", headers=user1_headers).json()
    u1_vm_ids = [v["id"] for v in u1_vms]
    assert linux_vm1.id in u1_vm_ids
    assert linux_vm2.id not in u1_vm_ids

    # User 1 checks vm1 remote-status: one-click connection ready!
    vm1_info = next(v for v in u1_vms if v["id"] == linux_vm1.id)
    assert vm1_info["remote_access"]["can_connect"] is True
    assert vm1_info["remote_access"]["protocol"] == "ssh"
    assert vm1_info["remote_access"]["port"] == 22
    assert vm1_info["remote_access"]["has_credentials"] is True
    # Zero plaintext secrets returned
    assert "password" not in vm1_info["remote_access"]

    # User 1 attempts anti-IDOR access to User 2's VM -> 404 Not Found (OWASP anti-IDOR protection)
    idor_res = client.get(f"/api/v1/vms/{linux_vm2.id}/remote-status", headers=user1_headers)
    assert idor_res.status_code == 404
