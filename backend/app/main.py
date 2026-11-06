import asyncio
import logging
import ssl
import time
from datetime import datetime, timedelta, timezone

from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field, model_validator
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from . import models as m, security as sec
from .config import BRAND, get_settings
from .db import Base, SessionLocal, engine, get_db
from .guacamole import GuacdClient, GuacamoleError, encode_instruction, test_guacd
from .vmware import PyVmomiProvider, VMwareError

log = logging.getLogger("nexus")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

S = get_settings()

app = FastAPI(
    title=BRAND["product"],
    description=BRAND["tagline"],
    version=BRAND["version"],
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=S.cors,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

def get_session():
    if get_db in app.dependency_overrides:
        gen = app.dependency_overrides[get_db]()
        return next(gen)
    return SessionLocal()

# ---------- Security Headers Middleware ----------
@app.middleware("http")
async def sec_headers(req: Request, call_next):
    start = time.time()
    response = await call_next(req)
    response.headers.update({
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "no-referrer",
        "Cache-Control": "no-store" if req.url.path.startswith("/api/v1") else "public",
    })
    elapsed_ms = (time.time() - start) * 1000
    log.info("%s %s %s %.1fms", req.method, req.url.path, response.status_code, elapsed_ms)
    return response

# ---------- Exception Handlers ----------
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(req: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        loc = [str(l) for l in err.get("loc", []) if l != "body"]
        field = " -> ".join(loc)
        msg = err.get("msg", "Invalid value")
        errors.append(f"{field}: {msg}" if field else msg)
    return JSONResponse(
        status_code=422,
        content={"detail": ", ".join(errors) or "Validation failed"},
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(req: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content={"detail": detail},
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(req: Request, exc: Exception):
    log.exception("Unhandled server exception on %s %s: %s", req.method, req.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected server error occurred. Please try again or contact your administrator."},
    )

# ---------- Helper Functions ----------
def audit(db: Session, user: m.User | None, action: str, detail: str = "", req: Request | None = None):
    ip = req.client.host if req and req.client else ""
    db.add(m.AuditLog(
        user_id=user.id if user else None,
        action=action,
        detail=detail,
        ip=ip,
    ))
    db.commit()

def to_utc_iso(dt: datetime | None) -> str | None:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()

def password_ok(p: str):
    if len(p) < 12:
        raise HTTPException(422, "Password must be at least 12 characters long.")

@app.on_event("startup")
def startup():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        for role_name in ("admin", "user"):
            if not db.scalar(select(m.Role).where(m.Role.name == role_name)):
                db.add(m.Role(name=role_name))
        db.commit()

        if S.admin_email and S.admin_password:
            admin_role_id = db.scalar(select(m.Role.id).where(m.Role.name == "admin"))
            existing_admin = db.scalar(select(m.User).where(m.User.email == S.admin_email.lower()))
            if not existing_admin:
                password_ok(S.admin_password)
                db.add(m.User(
                    email=S.admin_email.lower(),
                    full_name="System Administrator",
                    password_hash=sec.hash_password(S.admin_password),
                    role_id=admin_role_id,
                ))
                db.commit()
                log.info("Initial system administrator created for %s", S.admin_email)

# ---------- Auth Dependencies ----------
def current_user(req: Request, db: Session = Depends(get_db)) -> m.User:
    auth = req.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    try:
        payload = sec.decode_access(auth[7:])
    except Exception:
        raise HTTPException(401, "Invalid or expired session token")

    user = db.get(m.User, int(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(401, "Account disabled or not found")
    return user

def admin_user(u: m.User = Depends(current_user)) -> m.User:
    if u.role.name != "admin":
        raise HTTPException(403, "Administrator access required")
    return u

def assigned_vm(db: Session, user: m.User, vm_id: int) -> m.VirtualMachine:
    """Anti-IDOR validation: Standard users can ONLY access VMs assigned to them.
    Administrators can access any VM.
    """
    if getattr(user, "role", None) and user.role.name == "admin":
        v = db.get(m.VirtualMachine, vm_id)
    else:
        v = db.scalar(
            select(m.VirtualMachine)
            .join(m.VmAssignment, m.VmAssignment.vm_id == m.VirtualMachine.id)
            .where(m.VmAssignment.user_id == user.id, m.VirtualMachine.id == vm_id)
        )
    if not v:
        raise HTTPException(404, "Virtual machine not found or not assigned to your account.")
    return v

def provider(db: Session) -> PyVmomiProvider:
    if not S.vmware_enabled:
        raise HTTPException(503, "VMware integration is disabled in system configuration (VMWARE_ENABLED=false).")
    c = db.scalar(select(m.VmwareConnection).order_by(m.VmwareConnection.id.desc()))
    if not c:
        raise HTTPException(409, "VMware connection is not configured yet. Configure connection in Admin -> VMware Infrastructure.")
    return PyVmomiProvider(c.host, c.username, sec.decrypt(c.password_enc), c.verify_tls)

def vm_out(v: m.VirtualMachine, include_remote_meta: bool = True):
    res = {
        "id": v.id,
        "uuid": v.uuid,
        "name": v.name,
        "guest_os": v.guest_os,
        "power_state": v.power_state,
        "cpu": v.cpu,
        "ram_mb": v.ram_mb,
        "storage_gb": v.storage_gb,
        "ip_address": v.ip_address,
        "host": v.host,
        "datastore": v.datastore,
        "connection_state": getattr(v, "connection_state", "connected") or "connected",
        "source": v.source,
        "created_at": to_utc_iso(v.created_at),
        "updated_at": to_utc_iso(v.updated_at),
    }
    if include_remote_meta:
        cfg = v.remote_config
        res["remote_access"] = {
            "configured": bool(cfg and cfg.is_active),
            "protocol": cfg.protocol if cfg and cfg.is_active else None,
            "port": cfg.port if cfg and cfg.is_active else None,
            "has_credentials": bool(cfg and (cfg.password_enc or cfg.private_key_enc)) if cfg else False,
        }
    return res

def user_out(u: m.User, db: Session | None = None):
    last_login = None
    if db:
        ll = db.scalar(
            select(m.AuditLog.created_at)
            .where(m.AuditLog.user_id == u.id, m.AuditLog.action == "login")
            .order_by(m.AuditLog.id.desc())
            .limit(1)
        )
        if ll:
            last_login = to_utc_iso(ll)
    return {
        "id": u.id,
        "email": u.email,
        "full_name": u.full_name,
        "role": u.role.name,
        "is_active": u.is_active,
        "created_at": to_utc_iso(u.created_at),
        "last_login": last_login,
    }

def issue_token(db: Session, u: m.User):
    rt, h = sec.new_refresh()
    db.add(m.UserSession(
        user_id=u.id,
        refresh_hash=h,
        expires_at=datetime.now(timezone.utc) + timedelta(days=S.refresh_days),
    ))
    db.commit()
    return {
        "access_token": sec.make_access(u.id, u.role.name),
        "refresh_token": rt,
        "token_type": "bearer",
        "user": user_out(u, db),
    }

# ---------- Schemas ----------
class Login(BaseModel):
    email: str | None = None
    username: str | None = None
    password: str

    @property
    def identifier(self) -> str:
        return (self.email or self.username or "").strip()

    @model_validator(mode="after")
    def check_identifier(self):
        if not self.identifier:
            raise ValueError("Email or username is required")
        return self

class Refresh(BaseModel):
    refresh_token: str

class UserIn(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    password: str
    role: str = "user"

class UserUpd(BaseModel):
    full_name: str | None = None
    role: str | None = None
    is_active: bool | None = None
    password: str | None = None

class Power(BaseModel):
    action: str = Field(pattern="^(start|stop|restart)$")

class AssignIn(BaseModel):
    user_id: int
    vm_ids: list[int] = Field(min_length=1)

class VmwareIn(BaseModel):
    host: str
    username: str
    password: str
    verify_tls: bool = True

class RemoteConfigIn(BaseModel):
    protocol: str = Field(pattern="^(rdp|ssh|vnc)$")
    host: str = Field(min_length=1, max_length=255)
    port: int = Field(ge=1, le=65535)
    username: str = Field(default="", max_length=255)
    password: str | None = None
    private_key: str | None = None
    passphrase: str | None = None
    domain: str = Field(default="", max_length=255)
    security: str = Field(default="any", max_length=32)
    ignore_cert: bool = True
    color_depth: int = 24
    resize_method: str = "display-update"
    enable_audio: bool = True
    enable_clipboard: bool = True
    is_active: bool = True

class TicketIn(BaseModel):
    subject: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1)

class MsgIn(BaseModel):
    body: str = Field(min_length=1)

# ---------- Core Routers ----------
api = APIRouter(prefix="/api/v1")

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "brand": BRAND,
        "vmware_enabled": S.vmware_enabled,
        "guacd_configured": {
            "host": S.guacd_host,
            "port": S.guacd_port,
        },
    }

# ---------- Auth Endpoints ----------
@api.post("/auth/login")
def login(b: Login, req: Request, db: Session = Depends(get_db)):
    client_ip = req.client.host if req.client else "unknown"
    if sec.rate_limited(f"login:{client_ip}"):
        raise HTTPException(429, "Too many login attempts. Please wait 60 seconds.")

    ident = b.identifier.lower()
    candidates = db.scalars(
        select(m.User).where(
            or_(
                func.lower(m.User.email) == ident,
                func.lower(m.User.full_name) == ident,
                func.lower(m.User.email).startswith(f"{ident}@"),
            )
        )
    ).all()

    u = next((c for c in candidates if c.email.lower() == ident), None)
    if not u or not sec.verify_password(u.password_hash, b.password):
        matched = next((c for c in candidates if c.is_active and sec.verify_password(c.password_hash, b.password)), None)
        if matched:
            u = matched

    if not u or not u.is_active or not sec.verify_password(u.password_hash, b.password):
        audit(db, u, "login_failed", ident, req)
        raise HTTPException(401, "Invalid email, username, or password.")

    audit(db, u, "login", "", req)
    return issue_token(db, u)

@api.post("/auth/refresh")
def refresh(b: Refresh, db: Session = Depends(get_db)):
    s = db.scalar(select(m.UserSession).where(m.UserSession.refresh_hash == sec.hash_refresh(b.refresh_token)))
    if not s or s.revoked or s.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(401, "Invalid or expired session token. Please sign in again.")
    s.revoked = True
    u = db.get(m.User, s.user_id)
    if not u or not u.is_active:
        raise HTTPException(401, "Account disabled or not found.")
    return issue_token(db, u)

@api.post("/auth/logout")
def logout(b: Refresh, u: m.User = Depends(current_user), db: Session = Depends(get_db)):
    s = db.scalar(select(m.UserSession).where(
        m.UserSession.refresh_hash == sec.hash_refresh(b.refresh_token),
        m.UserSession.user_id == u.id
    ))
    if s:
        s.revoked = True
    audit(db, u, "logout")
    return {"ok": True}

@api.get("/auth/me")
def me(u: m.User = Depends(current_user), db: Session = Depends(get_db)):
    return user_out(u, db)

@api.get("/users/me")
def users_me(u: m.User = Depends(current_user), db: Session = Depends(get_db)):
    return user_out(u, db)

# ---------- User VM Endpoints ----------
@api.get("/vms")
def my_vms(u: m.User = Depends(current_user), db: Session = Depends(get_db)):
    """Standard users see ONLY VMs assigned to them.
    Admins see assigned VMs (or can query all via admin endpoint).
    """
    if u.role.name == "admin":
        rows = db.scalars(select(m.VirtualMachine).order_by(m.VirtualMachine.name)).all()
    else:
        rows = db.scalars(
            select(m.VirtualMachine)
            .join(m.VmAssignment, m.VmAssignment.vm_id == m.VirtualMachine.id)
            .where(m.VmAssignment.user_id == u.id)
            .order_by(m.VirtualMachine.name)
        ).all()
    return [vm_out(v) for v in rows]

@api.get("/vms/{vm_id}")
def vm_get(vm_id: int, u: m.User = Depends(current_user), db: Session = Depends(get_db)):
    v = assigned_vm(db, u, vm_id)
    acts = db.scalars(
        select(m.AuditLog)
        .where(m.AuditLog.detail.like(f"vm={v.id} %") | (m.AuditLog.detail == f"vm={v.id}"))
        .order_by(m.AuditLog.id.desc())
        .limit(10)
    ).all()
    return vm_out(v) | {
        "recent_activity": [{"action": a.action, "detail": a.detail, "at": to_utc_iso(a.created_at)} for a in acts]
    }

@api.get("/vms/{vm_id}/remote-status")
def vm_remote_status(vm_id: int, u: m.User = Depends(current_user), db: Session = Depends(get_db)):
    """Safe check for remote access readiness: returns protocol and power state, NEVER passwords."""
    v = assigned_vm(db, u, vm_id)
    cfg = v.remote_config
    is_configured = bool(cfg and cfg.is_active and cfg.host)
    return {
        "vm_id": v.id,
        "vm_name": v.name,
        "power_state": v.power_state,
        "configured": is_configured,
        "protocol": cfg.protocol if is_configured else None,
        "host": cfg.host if is_configured else None,
        "port": cfg.port if is_configured else None,
        "can_connect": bool(is_configured and v.power_state == "on"),
        "reason": None if (is_configured and v.power_state == "on") else (
            "VM is powered off. Please power on the machine first." if v.power_state != "on" else "Remote access is not configured for this machine. Contact your administrator."
        ),
    }

@api.post("/vms/{vm_id}/power")
def vm_power(vm_id: int, b: Power, req: Request, u: m.User = Depends(current_user), db: Session = Depends(get_db)):
    v = assigned_vm(db, u, vm_id)
    try:
        v.power_state = provider(db).power(v, b.action)
    except VMwareError as e:
        raise HTTPException(502, str(e))
    audit(db, u, f"power_{b.action}", f"vm={v.id}", req)
    return vm_out(v)

# ---------- Apache Guacamole Browser Remote Access WebSocket Tunnel ----------
@api.websocket("/vms/{vm_id}/guac-ws")
async def guac_websocket_tunnel(
    websocket: WebSocket,
    vm_id: int,
    token: str | None = None,
    width: int = 1280,
    height: int = 800,
    dpi: int = 96,
):
    """Secure Apache Guacamole WebSocket Tunnel.
    1. Authenticates session token.
    2. Validates backend authorization and VM assignment.
    3. Verifies VM is powered on and remote access is configured.
    4. Connects to guacd daemon and executes protocol handshake.
    5. Streams Guacamole instructions bi-directionally between browser and target VM.
    """
    # 1. Resolve auth token
    if not token:
        token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401, reason="Authentication token required")
        return

    db = get_session()
    user = None
    vm = None
    cfg = None
    session_log_id = None
    client_ip = websocket.client.host if websocket.client else "unknown"

    try:
        payload = sec.decode_access(token)
        user_id = int(payload.get("sub", 0))
        user = db.get(m.User, user_id)
        if not user or not user.is_active:
            await websocket.close(code=4401, reason="Invalid or inactive user session")
            return

        # 2. Authorization check (Anti-IDOR)
        if user.role.name == "admin":
            vm = db.get(m.VirtualMachine, vm_id)
        else:
            vm = db.scalar(
                select(m.VirtualMachine)
                .join(m.VmAssignment, m.VmAssignment.vm_id == m.VirtualMachine.id)
                .where(m.VmAssignment.user_id == user.id, m.VirtualMachine.id == vm_id)
            )

        if not vm:
            await websocket.close(code=4404, reason=f"Virtual machine #{vm_id} not found or not assigned to your account")
            return

        # 3. Power state check
        if vm.power_state != "on":
            await websocket.close(code=4400, reason=f"VM '{vm.name}' is currently powered off. Please power it on first.")
            return

        # 4. Remote configuration check
        cfg = vm.remote_config
        if not cfg or not cfg.is_active:
            await websocket.close(
                code=4404,
                reason=f"Remote access has not been configured for VM '{vm.name}'. Please contact your administrator."
            )
            return

        # 5. Extract target host and decrypted credentials safely server-side
        protocol = cfg.protocol.lower()
        target_host = cfg.host.strip() or vm.ip_address.strip()
        if not target_host:
            await websocket.close(
                code=4400,
                reason=f"Target host address is not configured for VM '{vm.name}', and no IP was reported by VMware Tools."
            )
            return

        target_port = cfg.port or (3389 if protocol == "rdp" else (22 if protocol == "ssh" else 5900))
        password = sec.decrypt(cfg.password_enc) if cfg.password_enc else ""
        private_key = sec.decrypt(cfg.private_key_enc) if cfg.private_key_enc else ""
        passphrase = sec.decrypt(cfg.passphrase_enc) if cfg.passphrase_enc else ""

        # Build guacd parameters map based on protocol
        params: dict[str, str] = {
            "hostname": target_host,
            "port": str(target_port),
            "width": str(width),
            "height": str(height),
            "dpi": str(dpi),
        }

        if protocol == "rdp":
            params.update({
                "username": cfg.username,
                "password": password,
                "domain": cfg.domain,
                "security": cfg.security or "any",
                "ignore-cert": "true" if cfg.ignore_cert else "false",
                "color-depth": str(cfg.color_depth or 24),
                "resize-method": cfg.resize_method or "display-update",
                "enable-font-smoothing": "true",
                "enable-wallpaper": "false",
                "enable-theming": "true",
                "enable-full-window-drag": "false",
                "enable-audio": "true" if cfg.enable_audio else "false",
                "disable-audio": "false" if cfg.enable_audio else "true",
            })
        elif protocol == "ssh":
            params.update({
                "username": cfg.username,
                "password": password,
                "private-key": private_key,
                "passphrase": passphrase,
                "font-name": "monospace",
                "font-size": "14",
                "color-scheme": "black-white",
            })
        elif protocol == "vnc":
            params.update({
                "password": password,
                "color-depth": str(cfg.color_depth or 24),
            })

        # Record session log entry
        sess_log = m.RemoteSessionLog(
            user_id=user.id,
            vm_id=vm.id,
            protocol=protocol,
            client_ip=client_ip,
            status="connected",
        )
        db.add(sess_log)
        db.commit()
        session_log_id = sess_log.id

        audit(db, user, "remote_connect_started", f"vm={vm.id} protocol={protocol} ip={client_ip}")

    except Exception as e:
        log.exception("Guacamole pre-connection validation failed: %s", e)
        await websocket.close(code=4500, reason=f"Remote session validation failed: {str(e)[:100]}")
        db.close()
        return

    # Accept client WebSocket connection with subprotocol guacamole once validated
    client_subprotocols = websocket.scope.get("subprotocols", [])
    selected_subprotocol = "guacamole" if "guacamole" in client_subprotocols else (client_subprotocols[0] if client_subprotocols else None)
    await websocket.accept(subprotocol=selected_subprotocol)

    async def abort_with_diagnostic(message: str, code: str = "514"):
        log.warning("Guacamole session rejected: %s", message)
        try:
            await websocket.send_text(encode_instruction("error", message, code))
            await asyncio.sleep(0.05)
            await websocket.close(code=1000)
        except Exception:
            pass
        if session_log_id:
            s_log = db.get(m.RemoteSessionLog, session_log_id)
            if s_log:
                s_log.status = "failed"
                s_log.ended_at = m.now()
                db.commit()
        db.close()

    # 6. Connect to guacd daemon and complete handshake
    guac_client = GuacdClient(host=S.guacd_host, port=S.guacd_port, timeout=S.guacd_timeout)

    try:
        await guac_client.connect()
    except Exception as exc:
        log.error("Failed to connect to guacd at %s:%s: %s", S.guacd_host, S.guacd_port, exc)
        await abort_with_diagnostic(
            f"Apache Guacamole proxy service (guacd at {S.guacd_host}:{S.guacd_port}) is unreachable.",
            "514"
        )
        return

    try:
        await guac_client.handshake(
            protocol=protocol,
            params=params,
            width=width,
            height=height,
            dpi=dpi,
        )
    except GuacamoleError as ge:
        err_text = str(ge)
        log.warning("guacd handshake failed for vm=%s (%s): %s", vm_id, protocol, err_text)
        if "timeout" in err_text.lower():
            friendly = f"Connection to {target_host}:{target_port} timed out. Verify the VM is powered on and {protocol.upper()} port is reachable."
        elif "refused" in err_text.lower() or "reset" in err_text.lower():
            friendly = f"Connection refused on {target_host}:{target_port}. Verify that the {protocol.upper()} service is running."
        elif "auth" in err_text.lower() or "credential" in err_text.lower():
            friendly = f"Authentication rejected by target VM {target_host}. Verify the username and password in Remote Access configuration."
        else:
            friendly = f"Guacamole remote session failed: {err_text}"
        await abort_with_diagnostic(friendly, "797")
        return
    except Exception as exc:
        log.exception("Unexpected error during guacd handshake: %s", exc)
        await abort_with_diagnostic("Guacamole remote session negotiation failed.", "514")
        return

    # Inform client that connection is ready
    ready_instr = encode_instruction("ready", guac_client.connection_id or "guac-session")
    await websocket.send_text(ready_instr)

    # 7. Bi-directional async pipe between WebSocket and guacd
    async def forward_client_to_guacd():
        """Reads instructions from browser WebSocket and forwards them to guacd."""
        try:
            while True:
                msg = await websocket.receive()
                if "text" in msg and msg["text"]:
                    await guac_client.write_raw(msg["text"])
                elif "bytes" in msg and msg["bytes"]:
                    text = msg["bytes"].decode("utf-8", errors="replace")
                    await guac_client.write_raw(text)
        except (WebSocketDisconnect, asyncio.CancelledError):
            pass
        except Exception as e:
            log.debug("Client to guacd stream closed: %s", e)

    async def forward_guacd_to_client():
        """Reads raw instruction chunks from guacd and forwards them to browser WebSocket."""
        try:
            async for chunk in guac_client.read_raw_instructions():
                await websocket.send_text(chunk)
        except (WebSocketDisconnect, asyncio.CancelledError):
            pass
        except Exception as e:
            log.debug("guacd to client stream closed: %s", e)

    task_client = asyncio.create_task(forward_client_to_guacd())
    task_guacd = asyncio.create_task(forward_guacd_to_client())

    done, pending = await asyncio.wait(
        [task_client, task_guacd],
        return_when=asyncio.FIRST_COMPLETED,
    )
    for p_task in pending:
        p_task.cancel()

    # Clean teardown
    await guac_client.close()
    duration = int(time.time() - connect_start)

    try:
        if session_log_id:
            s_log = db.get(m.RemoteSessionLog, session_log_id)
            if s_log:
                s_log.status = "closed"
                s_log.ended_at = m.now()
                s_log.duration_seconds = duration
                db.commit()
        audit(db, user, "remote_connect_ended", f"vm={vm.id} duration={duration}s")
    except Exception as e:
        log.warning("Audit record update failed: %s", e)
    finally:
        db.close()

# ---------- WebMKS Console Fallback Endpoints ----------
@api.post("/vms/{vm_id}/console-ticket")
def console_ticket(vm_id: int, req: Request, u: m.User = Depends(current_user), db: Session = Depends(get_db)):
    v = assigned_vm(db, u, vm_id)
    try:
        if v.power_state != "on":
            raise VMwareError(f"Cannot acquire console ticket: VM '{v.name}' is currently powered off.")
        t = provider(db).console_ticket(v)
    except VMwareError as e:
        raise HTTPException(503, str(e))
    audit(db, u, "console_access", f"vm={v.id}", req)
    t["ws_proxy_path"] = f"/api/v1/vms/{v.id}/console-ws"
    return t

@api.websocket("/vms/{vm_id}/console-ws")
async def console_ws(websocket: WebSocket, vm_id: int, token: str | None = None):
    if not token:
        token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401, reason="Authentication token required")
        return

    db = get_session()
    try:
        payload = sec.decode_access(token)
        user_id = int(payload.get("sub", 0))
        user = db.get(m.User, user_id)
        if not user or not user.is_active:
            await websocket.close(code=4401, reason="Invalid or inactive user session")
            return

        if user.role.name == "admin":
            v = db.get(m.VirtualMachine, vm_id)
        else:
            v = db.scalar(
                select(m.VirtualMachine)
                .join(m.VmAssignment, m.VmAssignment.vm_id == m.VirtualMachine.id)
                .where(m.VmAssignment.user_id == user.id, m.VirtualMachine.id == vm_id)
            )
        if not v:
            await websocket.close(code=4404, reason="VM not assigned to your account")
            return

        if v.power_state != "on":
            await websocket.close(code=4400, reason="VM is powered off. Power on VM first.")
            return

        p = provider(db)
        t = p.console_ticket(v)
    except Exception as e:
        await websocket.close(code=4500, reason=f"Console initialization failed: {str(e)[:100]}")
        return
    finally:
        db.close()

    remote_url = t["url"]
    ssl_ctx = ssl.create_default_context() if p.verify else ssl._create_unverified_context()
    client_subprotocols = websocket.scope.get("subprotocols", [])
    selected_subprotocol = "binary" if "binary" in client_subprotocols else (client_subprotocols[0] if client_subprotocols else None)

    await websocket.accept(subprotocol=selected_subprotocol)

    try:
        import websockets
        async with websockets.connect(
            remote_url,
            ssl=ssl_ctx,
            subprotocols=["binary", "uint8utf8"],
            max_size=10 * 1024 * 1024,
            ping_interval=20,
            ping_timeout=20,
        ) as remote_ws:
            async def fwd_client():
                try:
                    while True:
                        data = await websocket.receive()
                        if "bytes" in data and data["bytes"]:
                            await remote_ws.send(data["bytes"])
                        elif "text" in data and data["text"]:
                            await remote_ws.send(data["text"])
                except Exception:
                    pass

            async def fwd_remote():
                try:
                    async for msg in remote_ws:
                        if isinstance(msg, bytes):
                            await websocket.send_bytes(msg)
                        else:
                            await websocket.send_text(msg)
                except Exception:
                    pass

            t1 = asyncio.create_task(fwd_client())
            t2 = asyncio.create_task(fwd_remote())
            done, pending = await asyncio.wait([t1, t2], return_when=asyncio.FIRST_COMPLETED)
            for pt in pending:
                pt.cancel()
    except Exception as e:
        log.warning(f"WebMKS console proxy error for vm={vm_id}: {e}")
        try:
            await websocket.close(code=1011, reason="Remote ESXi connection error")
        except Exception:
            pass

# ---------- Admin Endpoints ----------
adm = APIRouter(prefix="/api/v1/admin", dependencies=[Depends(admin_user)])

def get_role_id(db: Session, name: str) -> int:
    r = db.scalar(select(m.Role).where(m.Role.name == name))
    if not r:
        raise HTTPException(422, f"Unknown role '{name}'")
    return r.id

@adm.get("/overview")
async def a_overview(db: Session = Depends(get_db)):
    total_users = db.scalar(select(func.count(m.User.id))) or 0
    total_vms = db.scalar(select(func.count(m.VirtualMachine.id))) or 0
    running_vms = db.scalar(select(func.count(m.VirtualMachine.id)).where(m.VirtualMachine.power_state == "on")) or 0
    total_asg = db.scalar(select(func.count(m.VmAssignment.id))) or 0
    open_tickets = db.scalar(select(func.count(m.SupportTicket.id)).where(m.SupportTicket.status == "open")) or 0
    configured_remote = db.scalar(select(func.count(m.RemoteAccessConfig.id)).where(m.RemoteAccessConfig.is_active == True)) or 0
    c = db.scalar(select(m.VmwareConnection).order_by(m.VmwareConnection.id.desc()))

    # Real audit logs
    recent_logs = []
    for l in db.scalars(select(m.AuditLog).order_by(m.AuditLog.id.desc()).limit(8)):
        u = db.get(m.User, l.user_id) if l.user_id else None
        recent_logs.append({
            "id": l.id,
            "user_email": u.email if u else ("System" if not l.user_id else f"User #{l.user_id}"),
            "action": l.action,
            "detail": l.detail,
            "at": to_utc_iso(l.created_at),
        })

    # Test guacd status
    guac_health = await test_guacd(S.guacd_host, S.guacd_port, timeout=2)

    return {
        "total_users": total_users,
        "total_vms": total_vms,
        "running_vms": running_vms,
        "stopped_vms": max(0, total_vms - running_vms),
        "total_assignments": total_asg,
        "configured_remote": configured_remote,
        "open_tickets": open_tickets,
        "vmware": {
            "enabled": S.vmware_enabled,
            "configured": bool(c),
            "host": c.host if c else None,
            "status": c.status if c else "not configured",
            "last_sync": to_utc_iso(c.last_sync) if c else None,
        },
        "guacamole": guac_health,
        "recent_logs": recent_logs,
    }

@adm.get("/users")
def a_users(db: Session = Depends(get_db)):
    return [user_out(u, db) for u in db.scalars(select(m.User).order_by(m.User.id))]

@adm.post("/users", status_code=201)
def a_user_new(b: UserIn, req: Request, a: m.User = Depends(admin_user), db: Session = Depends(get_db)):
    password_ok(b.password)
    if db.scalar(select(m.User).where(m.User.email == b.email.lower())):
        raise HTTPException(409, "A user account with this email address already exists.")
    u = m.User(
        email=b.email.lower(),
        full_name=b.full_name,
        password_hash=sec.hash_password(b.password),
        role_id=get_role_id(db, b.role),
    )
    db.add(u)
    db.commit()
    audit(db, a, "user_create", u.email, req)
    return user_out(u)

@adm.put("/users/{uid}")
def a_user_upd(uid: int, b: UserUpd, req: Request, a: m.User = Depends(admin_user), db: Session = Depends(get_db)):
    u = db.get(m.User, uid)
    if not u:
        raise HTTPException(404, "User not found")
    if u.id == a.id and b.is_active is False:
        raise HTTPException(400, "Cannot disable your own administrator account")
    if b.full_name:
        u.full_name = b.full_name
    if b.role:
        u.role_id = get_role_id(db, b.role)
    if b.is_active is not None:
        u.is_active = b.is_active
    if b.password:
        password_ok(b.password)
        u.password_hash = sec.hash_password(b.password)
    db.commit()
    audit(db, a, "user_update", u.email, req)
    return user_out(db.get(m.User, uid))

@adm.delete("/users/{uid}")
def a_user_del(uid: int, req: Request, a: m.User = Depends(admin_user), db: Session = Depends(get_db)):
    u = db.get(m.User, uid)
    if not u:
        raise HTTPException(404, "User not found")
    if u.id == a.id:
        raise HTTPException(400, "Cannot disable your own administrator account")
    u.is_active = False
    db.commit()
    audit(db, a, "user_disable", u.email, req)
    return {"ok": True, "message": f"User {u.email} disabled successfully."}

@adm.get("/vms")
def a_vms(name: str | None = None, power_state: str | None = None, db: Session = Depends(get_db)):
    q = select(m.VirtualMachine).order_by(m.VirtualMachine.name)
    if name:
        q = q.where(m.VirtualMachine.name.ilike(f"%{name}%"))
    if power_state:
        q = q.where(m.VirtualMachine.power_state == power_state)
    return [vm_out(v) for v in db.scalars(q)]

def do_sync(db: Session, a: m.User, req: Request):
    """Real VMware synchronization with UUID deduplication."""
    p = provider(db)
    try:
        infos = p.list_vms()
    except VMwareError as e:
        raise HTTPException(502, str(e))

    synced_count = 0
    updated_count = 0
    for i in infos:
        existing = db.scalar(select(m.VirtualMachine).where(m.VirtualMachine.uuid == i.uuid))
        if existing:
            v = existing
            updated_count += 1
        else:
            v = m.VirtualMachine(uuid=i.uuid, source="vmware")
            db.add(v)
            synced_count += 1

        v.name = i.name
        v.guest_os = i.guest_os
        v.power_state = i.power_state
        v.cpu = i.cpu
        v.ram_mb = i.ram_mb
        v.storage_gb = i.storage_gb
        v.ip_address = i.ip_address
        v.host = i.host
        v.datastore = i.datastore
        v.connection_state = getattr(i, "connection_state", "connected")

    c = db.scalar(select(m.VmwareConnection).order_by(m.VmwareConnection.id.desc()))
    if c:
        c.last_sync = m.now()
        c.status = "connected"

    db.commit()
    total = synced_count + updated_count
    audit(db, a, "vm_sync", f"{total} VMs processed ({synced_count} added, {updated_count} updated)", req)
    return {
        "synced": total,
        "added": synced_count,
        "updated": updated_count,
        "message": f"Successfully synchronized {total} virtual machine(s) from VMware ({synced_count} new, {updated_count} refreshed).",
    }

@adm.post("/vms/sync")
def a_sync(req: Request, a: m.User = Depends(admin_user), db: Session = Depends(get_db)):
    return do_sync(db, a, req)

@adm.post("/vms/{vm_id}/power")
def a_vm_power(vm_id: int, b: Power, req: Request, a: m.User = Depends(admin_user), db: Session = Depends(get_db)):
    v = db.get(m.VirtualMachine, vm_id)
    if not v:
        raise HTTPException(404, "Virtual machine not found")
    try:
        v.power_state = provider(db).power(v, b.action)
    except VMwareError as e:
        raise HTTPException(502, str(e))
    audit(db, a, f"admin_power_{b.action}", f"vm={v.id}", req)
    return vm_out(v)

# ---------- Admin Remote Access Configuration Endpoints ----------
@adm.get("/vms/{vm_id}/remote-config")
def a_get_remote_config(vm_id: int, db: Session = Depends(get_db)):
    v = db.get(m.VirtualMachine, vm_id)
    if not v:
        raise HTTPException(404, "Virtual machine not found")
    cfg = v.remote_config
    if not cfg:
        is_win = "windows" in (v.guest_os or "").lower() or "win" in (v.name or "").lower()
        default_proto = "rdp" if is_win else "ssh"
        default_port = 3389 if is_win else 22
        return {
            "configured": False,
            "vm_id": v.id,
            "vm_name": v.name,
            "protocol": default_proto,
            "host": v.ip_address or "",
            "port": default_port,
            "username": "Administrator" if is_win else "",
            "has_password": False,
            "has_private_key": False,
            "domain": "",
            "security": "any",
            "ignore_cert": True,
            "is_active": True,
        }
    return {
        "configured": True,
        "vm_id": v.id,
        "vm_name": v.name,
        "protocol": cfg.protocol,
        "host": cfg.host or v.ip_address or "",
        "port": cfg.port,
        "username": cfg.username,
        "has_password": bool(cfg.password_enc),
        "has_private_key": bool(cfg.private_key_enc),
        "domain": cfg.domain,
        "security": cfg.security,
        "ignore_cert": cfg.ignore_cert,
        "color_depth": cfg.color_depth,
        "resize_method": cfg.resize_method,
        "enable_audio": cfg.enable_audio,
        "enable_clipboard": cfg.enable_clipboard,
        "is_active": cfg.is_active,
        "updated_at": to_utc_iso(cfg.updated_at),
    }

@adm.put("/vms/{vm_id}/remote-config")
def a_save_remote_config(
    vm_id: int,
    b: RemoteConfigIn,
    req: Request,
    a: m.User = Depends(admin_user),
    db: Session = Depends(get_db)
):
    v = db.get(m.VirtualMachine, vm_id)
    if not v:
        raise HTTPException(404, "Virtual machine not found")

    cfg = v.remote_config
    if not cfg:
        cfg = m.RemoteAccessConfig(vm_id=v.id)
        db.add(cfg)

    cfg.protocol = b.protocol.lower()
    cfg.host = b.host.strip()
    cfg.port = b.port
    cfg.username = b.username.strip()
    cfg.domain = b.domain.strip()
    cfg.security = b.security
    cfg.ignore_cert = b.ignore_cert
    cfg.color_depth = b.color_depth
    cfg.resize_method = b.resize_method
    cfg.enable_audio = b.enable_audio
    cfg.enable_clipboard = b.enable_clipboard
    cfg.is_active = b.is_active

    # Sensitive server-side secret handling
    if b.password is not None and b.password.strip():
        cfg.password_enc = sec.encrypt(b.password)
    if b.private_key is not None and b.private_key.strip():
        cfg.private_key_enc = sec.encrypt(b.private_key)
    if b.passphrase is not None and b.passphrase.strip():
        cfg.passphrase_enc = sec.encrypt(b.passphrase)

    db.commit()
    audit(db, a, "remote_config_saved", f"vm={v.id} proto={cfg.protocol} host={cfg.host}:{cfg.port}", req)
    return {
        "ok": True,
        "message": f"Remote access configuration for '{v.name}' saved successfully.",
        "config": a_get_remote_config(vm_id, db),
    }

@adm.delete("/vms/{vm_id}/remote-config")
def a_delete_remote_config(vm_id: int, req: Request, a: m.User = Depends(admin_user), db: Session = Depends(get_db)):
    v = db.get(m.VirtualMachine, vm_id)
    if not v:
        raise HTTPException(404, "Virtual machine not found")
    if v.remote_config:
        db.delete(v.remote_config)
        db.commit()
        audit(db, a, "remote_config_deleted", f"vm={v.id}", req)
    return {"ok": True, "message": f"Remote access configuration for '{v.name}' removed."}

# ---------- Admin Assignment Endpoints ----------
@adm.get("/assignments")
def a_assign_list(db: Session = Depends(get_db)):
    out = []
    for x in db.scalars(select(m.VmAssignment)):
        u = db.get(m.User, x.user_id)
        v = db.get(m.VirtualMachine, x.vm_id)
        out.append({
            "id": x.id,
            "user_id": x.user_id,
            "user_email": u.email if u else "Unknown User",
            "user_name": u.full_name if u else "Unknown User",
            "vm_id": x.vm_id,
            "vm_name": v.name if v else f"VM #{x.vm_id}",
            "vm_power_state": v.power_state if v else "unknown",
            "vm_remote_protocol": v.remote_config.protocol if (v and v.remote_config and v.remote_config.is_active) else None,
            "created_at": to_utc_iso(x.created_at),
        })
    return out

@adm.post("/assignments", status_code=201)
def a_assign(b: AssignIn, req: Request, a: m.User = Depends(admin_user), db: Session = Depends(get_db)):
    target_user = db.get(m.User, b.user_id)
    if not target_user:
        raise HTTPException(404, "Target user not found")
    made = []
    for vid in set(b.vm_ids):
        vm_obj = db.get(m.VirtualMachine, vid)
        if not vm_obj:
            raise HTTPException(404, f"Virtual Machine #{vid} not found")
        if not db.scalar(select(m.VmAssignment).where(m.VmAssignment.user_id == b.user_id, m.VmAssignment.vm_id == vid)):
            x = m.VmAssignment(user_id=b.user_id, vm_id=vid, assigned_by=a.id)
            db.add(x)
            made.append(x)
    db.commit()
    audit(db, a, "assign", f"user={b.user_id} vms={sorted(set(b.vm_ids))}", req)
    return {
        "created": len(made),
        "message": f"Successfully assigned {len(made)} virtual machine(s) to {target_user.full_name}.",
    }

@adm.delete("/assignments/{aid}")
def a_revoke(aid: int, req: Request, a: m.User = Depends(admin_user), db: Session = Depends(get_db)):
    x = db.get(m.VmAssignment, aid)
    if not x:
        raise HTTPException(404, "Assignment not found")
    user_id = x.user_id
    vm_id = x.vm_id
    db.delete(x)
    db.commit()
    audit(db, a, "revoke", f"user={user_id} vm={vm_id}", req)
    return {"ok": True, "message": "Assignment revoked successfully."}

@adm.get("/audit-logs")
def a_audit(limit: int = 200, db: Session = Depends(get_db)):
    out = []
    for l in db.scalars(select(m.AuditLog).order_by(m.AuditLog.id.desc()).limit(min(limit, 1000))):
        u = db.get(m.User, l.user_id) if l.user_id else None
        out.append({
            "id": l.id,
            "user_id": l.user_id,
            "user_email": u.email if u else ("System" if not l.user_id else f"User #{l.user_id}"),
            "user_name": u.full_name if u else ("System" if not l.user_id else "User"),
            "action": l.action,
            "detail": l.detail,
            "ip": l.ip,
            "at": to_utc_iso(l.created_at),
        })
    return out

@adm.get("/remote-sessions")
def a_remote_sessions(limit: int = 100, db: Session = Depends(get_db)):
    out = []
    for s in db.scalars(select(m.RemoteSessionLog).order_by(m.RemoteSessionLog.id.desc()).limit(limit)):
        u = db.get(m.User, s.user_id)
        v = db.get(m.VirtualMachine, s.vm_id)
        out.append({
            "id": s.id,
            "user_email": u.email if u else f"User #{s.user_id}",
            "vm_name": v.name if v else f"VM #{s.vm_id}",
            "protocol": s.protocol,
            "client_ip": s.client_ip,
            "status": s.status,
            "duration_seconds": s.duration_seconds,
            "started_at": to_utc_iso(s.created_at),
            "ended_at": to_utc_iso(s.ended_at),
        })
    return out

@adm.post("/vmware/test-connection")
def a_vm_test(b: VmwareIn, req: Request, a: m.User = Depends(admin_user), db: Session = Depends(get_db)):
    if not S.vmware_enabled:
        raise HTTPException(503, "VMware integration is disabled in system configuration (VMWARE_ENABLED=false).")
    try:
        ver = PyVmomiProvider(b.host, b.username, b.password, b.verify_tls).test()
    except VMwareError as e:
        raise HTTPException(502, str(e))

    c = m.VmwareConnection(
        host=b.host,
        username=b.username,
        password_enc=sec.encrypt(b.password),
        verify_tls=b.verify_tls,
        status="connected",
    )
    db.add(c)
    db.commit()
    audit(db, a, "vmware_configure", b.host, req)
    return {
        "ok": True,
        "detail": ver,
        "message": f"Successfully connected to VMware host: {ver}",
    }

@adm.post("/vmware/sync")
def a_vm_sync(req: Request, a: m.User = Depends(admin_user), db: Session = Depends(get_db)):
    return do_sync(db, a, req)

@adm.get("/vmware/status")
def a_vm_status(db: Session = Depends(get_db)):
    c = db.scalar(select(m.VmwareConnection).order_by(m.VmwareConnection.id.desc()))
    return {
        "vmware_enabled": S.vmware_enabled,
        "configured": bool(c),
        "host": c.host if c else None,
        "status": c.status if c else "not configured",
        "last_sync": to_utc_iso(c.last_sync) if c else None,
    }

@adm.get("/guacamole/status")
async def a_guacamole_status():
    res = await test_guacd(S.guacd_host, S.guacd_port, timeout=3)
    return res

# ---------- Support Endpoints ----------
sup = APIRouter(prefix="/api/v1/support")

def ticket_for(db: Session, u: m.User, tid: int) -> m.SupportTicket:
    t = db.get(m.SupportTicket, tid)
    if not t or (t.user_id != u.id and u.role.name != "admin"):
        raise HTTPException(404, "Support ticket not found")
    return t

@sup.get("/tickets")
def s_list(u: m.User = Depends(current_user), db: Session = Depends(get_db)):
    q = select(m.SupportTicket).order_by(m.SupportTicket.id.desc())
    if u.role.name != "admin":
        q = q.where(m.SupportTicket.user_id == u.id)
    out = []
    for t in db.scalars(q):
        owner = db.get(m.User, t.user_id)
        out.append({
            "id": t.id,
            "user_id": t.user_id,
            "user_email": owner.email if owner else "Unknown",
            "user_name": owner.full_name if owner else "Unknown",
            "subject": t.subject,
            "status": t.status,
            "created_at": to_utc_iso(t.created_at),
        })
    return out

@sup.post("/tickets", status_code=201)
def s_new(b: TicketIn, req: Request, u: m.User = Depends(current_user), db: Session = Depends(get_db)):
    t = m.SupportTicket(user_id=u.id, subject=b.subject)
    db.add(t)
    db.flush()
    db.add(m.SupportTicketMessage(ticket_id=t.id, user_id=u.id, body=b.body))
    db.commit()
    audit(db, u, "ticket_create", f"ticket={t.id}", req)
    return {
        "id": t.id,
        "subject": t.subject,
        "status": t.status,
        "message": "Support request submitted successfully.",
    }

@sup.get("/tickets/{tid}")
def s_get(tid: int, u: m.User = Depends(current_user), db: Session = Depends(get_db)):
    t = ticket_for(db, u, tid)
    ms = db.scalars(
        select(m.SupportTicketMessage)
        .where(m.SupportTicketMessage.ticket_id == tid)
        .order_by(m.SupportTicketMessage.id)
    ).all()
    owner = db.get(m.User, t.user_id)
    messages = []
    for x in ms:
        sender = db.get(m.User, x.user_id)
        messages.append({
            "id": x.id,
            "user_id": x.user_id,
            "user_email": sender.email if sender else "Unknown",
            "user_name": sender.full_name if sender else "User",
            "body": x.body,
            "at": to_utc_iso(x.created_at),
        })
    return {
        "id": t.id,
        "subject": t.subject,
        "status": t.status,
        "user_email": owner.email if owner else "Unknown",
        "created_at": to_utc_iso(t.created_at),
        "messages": messages,
    }

@sup.post("/tickets/{tid}/messages", status_code=201)
def s_msg(tid: int, b: MsgIn, u: m.User = Depends(current_user), db: Session = Depends(get_db)):
    t = ticket_for(db, u, tid)
    db.add(m.SupportTicketMessage(ticket_id=tid, user_id=u.id, body=b.body))
    t.status = "answered" if u.role.name == "admin" else "open"
    db.commit()
    return {"ok": True, "message": "Message sent."}

for r in (api, adm, sup):
    app.include_router(r)
