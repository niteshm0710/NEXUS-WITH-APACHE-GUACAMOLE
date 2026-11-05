import pytest
from app.guacamole import encode_element, encode_instruction, parse_instruction
from app import models as m, security as sec

def test_guacamole_encoding():
    assert encode_element("select") == "6.select"
    assert encode_element("rdp") == "3.rdp"
    assert encode_element("") == "0."
    assert encode_element("1024") == "4.1024"

    instr = encode_instruction("select", "rdp")
    assert instr == "6.select,3.rdp;"

    size_instr = encode_instruction("size", 1920, 1080, 96)
    assert size_instr == "4.size,4.1920,4.1080,2.96;"

def test_guacamole_parsing():
    opcode, args = parse_instruction("6.select,3.rdp;")
    assert opcode == "select"
    assert args == ["rdp"]

    opcode, args = parse_instruction("4.args,8.hostname,4.port,8.username,8.password;")
    assert opcode == "args"
    assert args == ["hostname", "port", "username", "password"]

    opcode, args = parse_instruction("5.ready,37.$260d8324-4f21-44c4-9e31-ae16297fb811;")
    assert opcode == "ready"
    assert args == ["$260d8324-4f21-44c4-9e31-ae16297fb811"]

def test_guac_ws_unauthorized(client):
    with pytest.raises(Exception):
        with client.websocket_connect("/api/v1/vms/999/guac-ws") as ws:
            pass

from starlette.websockets import WebSocketDisconnect

def test_guac_ws_unassigned_vm(client, db):
    # VM exists but is not assigned to user
    vm = m.VirtualMachine(
        uuid="vm-guac-test-1",
        name="Guac Test VM",
        guest_os="Windows 11",
        power_state="on"
    )
    db.add(vm)
    db.commit()

    user2 = db.query(m.User).filter_by(email="user2@nexus.test").first()
    token = sec.make_access(user2.id, "user")

    # Connect with user2's token to user1's unassigned VM
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(f"/api/v1/vms/{vm.id}/guac-ws?token={token}"):
            pass
    assert exc_info.value.code == 4404
