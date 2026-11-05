from app import models as m

def test_support_tickets_isolation(client, db, user1_headers, user2_headers, admin_headers):
    # User 1 creates a ticket
    r_create = client.post("/api/v1/support/tickets", headers=user1_headers, json={
        "subject": "Need help configuring RDP",
        "body": "Hello, my Windows server does not accept my domain login."
    })
    assert r_create.status_code == 201
    tid = r_create.json()["id"]

    # User 1 can view their own ticket
    r1_list = client.get("/api/v1/support/tickets", headers=user1_headers)
    assert r1_list.status_code == 200
    assert len(r1_list.json()) == 1
    assert r1_list.json()[0]["id"] == tid

    # User 2 CANNOT see User 1's ticket in the list
    r2_list = client.get("/api/v1/support/tickets", headers=user2_headers)
    assert r2_list.status_code == 200
    assert len(r2_list.json()) == 0

    # User 2 CANNOT access User 1's ticket directly (404)
    r2_get = client.get(f"/api/v1/support/tickets/{tid}", headers=user2_headers)
    assert r2_get.status_code == 404

    # Admin CAN see all tickets
    r_adm = client.get("/api/v1/support/tickets", headers=admin_headers)
    assert r_adm.status_code == 200
    assert any(t["id"] == tid for t in r_adm.json())

    # Admin replies to ticket
    r_reply = client.post(f"/api/v1/support/tickets/{tid}/messages", headers=admin_headers, json={
        "body": "Administrator response: We have verified your Active Directory credentials."
    })
    assert r_reply.status_code == 201

    # User 1 views thread and sees admin reply
    r1_get = client.get(f"/api/v1/support/tickets/{tid}", headers=user1_headers)
    assert r1_get.status_code == 200
    assert len(r1_get.json()["messages"]) == 2
    assert "Administrator response" in r1_get.json()["messages"][1]["body"]

def test_audit_logs_contain_real_system_actions(client, admin_headers):
    r = client.get("/api/v1/admin/audit-logs", headers=admin_headers)
    assert r.status_code == 200
    logs = r.json()
    assert isinstance(logs, list)
    # Verify no fake dummy actions exist
    for log in logs:
        assert "fake" not in log["action"].lower()
        assert "dummy" not in log["action"].lower()
