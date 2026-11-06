from app import models as m, security as sec

def test_vm_assignment_and_anti_idor(client, db, admin_headers, user1_headers, user2_headers):
    # 1. Create a VM in database
    vm = m.VirtualMachine(
        uuid="vm-uuid-1111-2222-3333",
        name="Production Windows Server",
        guest_os="Microsoft Windows Server 2022 (64-bit)",
        power_state="on",
        cpu=4,
        ram_mb=8192,
        storage_gb=100,
        ip_address="192.168.1.100",
        source="vmware"
    )
    db.add(vm)
    db.commit()

    # User 1 and User 2 currently see 0 assigned VMs
    r1 = client.get("/api/v1/vms", headers=user1_headers)
    assert r1.status_code == 200
    assert len(r1.json()) == 0

    r2 = client.get("/api/v1/vms", headers=user2_headers)
    assert r2.status_code == 200
    assert len(r2.json()) == 0

    # User 1 attempts direct access via ID (Anti-IDOR test)
    r1_direct = client.get(f"/api/v1/vms/{vm.id}", headers=user1_headers)
    assert r1_direct.status_code == 404

    # 2. Admin assigns VM to User 1
    user1 = db.query(m.User).filter_by(email="user1@nexus.test").first()
    assign_res = client.post("/api/v1/admin/assignments", headers=admin_headers, json={
        "user_id": user1.id,
        "vm_ids": [vm.id]
    })
    assert assign_res.status_code == 201
    assert assign_res.json()["created"] == 1

    # 3. User 1 now sees the assigned VM
    r1_after = client.get("/api/v1/vms", headers=user1_headers)
    assert r1_after.status_code == 200
    assert len(r1_after.json()) == 1
    assert r1_after.json()[0]["id"] == vm.id
    assert r1_after.json()[0]["name"] == "Production Windows Server"

    # User 1 can view details
    r1_detail = client.get(f"/api/v1/vms/{vm.id}", headers=user1_headers)
    assert r1_detail.status_code == 200
    assert r1_detail.json()["id"] == vm.id

    # 4. User 2 STILL cannot see or access User 1's VM
    r2_after = client.get("/api/v1/vms", headers=user2_headers)
    assert r2_after.status_code == 200
    assert len(r2_after.json()) == 0

    r2_direct = client.get(f"/api/v1/vms/{vm.id}", headers=user2_headers)
    assert r2_direct.status_code == 404
    assert "not assigned to your account" in r2_direct.json()["detail"]

def test_remote_access_configuration_and_encryption(client, db, admin_headers, user1_headers):
    # Setup VM and assignment
    vm = m.VirtualMachine(
        uuid="vm-uuid-9999-8888-7777",
        name="Ubuntu Dev Host",
        guest_os="Ubuntu Linux (64-bit)",
        power_state="on",
        cpu=2,
        ram_mb=4096,
        ip_address="192.168.1.150",
        source="vmware"
    )
    db.add(vm)
    db.commit()

    user1 = db.query(m.User).filter_by(email="user1@nexus.test").first()
    db.add(m.VmAssignment(user_id=user1.id, vm_id=vm.id))
    db.commit()

    # Remote status before configuration
    status_before = client.get(f"/api/v1/vms/{vm.id}/remote-status", headers=user1_headers)
    assert status_before.status_code == 200
    assert status_before.json()["configured"] is False
    assert status_before.json()["can_connect"] is False

    # Admin configures remote access (SSH protocol)
    secret_pass = "P@ssw0rdSecureSSH!"
    save_res = client.put(f"/api/v1/admin/vms/{vm.id}/remote-config", headers=admin_headers, json={
        "protocol": "ssh",
        "host": "192.168.1.150",
        "port": 22,
        "username": "ubuntu",
        "password": secret_pass,
        "security": "any",
        "ignore_cert": True,
        "is_active": True
    })
    assert save_res.status_code == 200
    assert save_res.json()["ok"] is True

    # Verify password is encrypted in database (NEVER plaintext)
    cfg_db = db.query(m.RemoteAccessConfig).filter_by(vm_id=vm.id).first()
    assert cfg_db is not None
    assert cfg_db.password_enc != secret_pass
    assert sec.decrypt(cfg_db.password_enc) == secret_pass

    # Standard user checks remote status (verifies password is NOT leaked in API response)
    status_after = client.get(f"/api/v1/vms/{vm.id}/remote-status", headers=user1_headers)
    assert status_after.status_code == 200
    data = status_after.json()
    assert data["configured"] is True
    assert data["protocol"] == "ssh"
    assert data["port"] == 22
    assert data["can_connect"] is True
    assert "password" not in data
    assert "password_enc" not in data

def test_vm_deduplication(db):
    # Simulate VMware sync running multiple times with same UUID
    uuid = "vm-stable-uuid-abc-123"

    v1 = m.VirtualMachine(uuid=uuid, name="Sync Target VM", guest_os="CentOS 8", power_state="on")
    db.add(v1)
    db.commit()

    # Second sync: query existing by UUID and update instead of inserting duplicate
    existing = db.query(m.VirtualMachine).filter_by(uuid=uuid).first()
    assert existing is not None
    existing.name = "Sync Target VM Renamed"
    existing.power_state = "off"
    db.commit()

    total_vms = db.query(m.VirtualMachine).filter_by(uuid=uuid).count()
    assert total_vms == 1
    updated = db.query(m.VirtualMachine).filter_by(uuid=uuid).first()
    assert updated.name == "Sync Target VM Renamed"
    assert updated.power_state == "off"

def test_user_management_and_multi_assignment_workflow(client, db, admin_headers):
    # 1. Create two VMs
    vm1 = m.VirtualMachine(uuid="vm-u-101", name="Dev Win11", guest_os="Microsoft Windows 11 (64-bit)", power_state="on", ip_address="192.168.0.51")
    vm2 = m.VirtualMachine(uuid="vm-u-102", name="Prod Linux", guest_os="Ubuntu Linux (64-bit)", power_state="on", ip_address="192.168.0.52")
    db.add_all([vm1, vm2])
    db.commit()

    # 2. Admin creates a new standard user
    create_res = client.post("/api/v1/admin/users", headers=admin_headers, json={
        "full_name": "Dev Operator",
        "email": "dev.operator@cloud4green.com",
        "role": "user",
        "password": "SecurePassword123!"
    })
    assert create_res.status_code == 201
    user_data = create_res.json()
    new_uid = user_data["id"]
    assert user_data["full_name"] == "Dev Operator"
    assert user_data["assigned_vm_count"] == 0

    # 3. List users and verify assigned_vm_count
    users_res = client.get("/api/v1/admin/users", headers=admin_headers)
    assert users_res.status_code == 200
    found_user = next((u for u in users_res.json() if u["id"] == new_uid), None)
    assert found_user is not None
    assert found_user["assigned_vm_count"] == 0

    # 4. Multi-assign both VMs to this user
    assign_res = client.post("/api/v1/admin/assignments", headers=admin_headers, json={
        "user_id": new_uid,
        "vm_ids": [vm1.id, vm2.id]
    })
    assert assign_res.status_code == 201
    assert assign_res.json()["created"] == 2

    # Verify user now shows assigned_vm_count == 2
    users_res2 = client.get("/api/v1/admin/users", headers=admin_headers)
    found_user2 = next((u for u in users_res2.json() if u["id"] == new_uid), None)
    assert found_user2["assigned_vm_count"] == 2
    assert set(found_user2["assigned_vm_ids"]) == {vm1.id, vm2.id}

    # Verify VMs show this user in assigned_users
    vms_res = client.get("/api/v1/admin/vms", headers=admin_headers)
    v1_out = next(v for v in vms_res.json() if v["id"] == vm1.id)
    assert any(u["user_id"] == new_uid for u in v1_out.get("assigned_users", []))

    # 5. Revoke vm1 assignment using DELETE /admin/users/{uid}/vms/{vid}
    del_res1 = client.delete(f"/api/v1/admin/users/{new_uid}/vms/{vm1.id}", headers=admin_headers)
    assert del_res1.status_code == 200
    assert del_res1.json()["ok"] is True

    # User now has 1 assigned VM
    users_res3 = client.get("/api/v1/admin/users", headers=admin_headers)
    found_user3 = next((u for u in users_res3.json() if u["id"] == new_uid), None)
    assert found_user3["assigned_vm_count"] == 1
    assert found_user3["assigned_vm_ids"] == [vm2.id]

    # 6. Revoke remaining assignment via /admin/assignments/{id}
    asgs_res = client.get("/api/v1/admin/assignments", headers=admin_headers)
    user_asg = next(a for a in asgs_res.json() if a["user_id"] == new_uid and a["vm_id"] == vm2.id)
    del_res2 = client.delete(f"/api/v1/admin/assignments/{user_asg['id']}", headers=admin_headers)
    assert del_res2.status_code == 200

    # User now has 0 assigned VMs
    users_res4 = client.get("/api/v1/admin/users", headers=admin_headers)
    found_user4 = next((u for u in users_res4.json() if u["id"] == new_uid), None)
    assert found_user4["assigned_vm_count"] == 0

    # 7. Edit user details
    update_res = client.put(f"/api/v1/admin/users/{new_uid}", headers=admin_headers, json={
        "full_name": "Senior Dev Operator",
        "role": "user"
    })
    assert update_res.status_code == 200
    assert update_res.json()["full_name"] == "Senior Dev Operator"

    # 8. Disable user and re-enable user
    disable_res = client.delete(f"/api/v1/admin/users/{new_uid}", headers=admin_headers)
    assert disable_res.status_code == 200
    assert disable_res.json()["ok"] is True

    enable_res = client.put(f"/api/v1/admin/users/{new_uid}", headers=admin_headers, json={"is_active": True})
    assert enable_res.status_code == 200
    assert enable_res.json()["is_active"] is True


