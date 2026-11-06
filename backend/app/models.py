from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

def now():
    return datetime.now(timezone.utc)

class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(32), unique=True)

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255))
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)

    role: Mapped[Role] = relationship()

class VirtualMachine(Base):
    __tablename__ = "virtual_machines"
    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    guest_os: Mapped[str] = mapped_column(String(255), default="")
    power_state: Mapped[str] = mapped_column(String(32), default="off")
    cpu: Mapped[int] = mapped_column(Integer, default=1)
    ram_mb: Mapped[int] = mapped_column(Integer, default=1024)
    storage_gb: Mapped[int] = mapped_column(Integer, default=0)
    ip_address: Mapped[str] = mapped_column(String(64), default="")
    host: Mapped[str] = mapped_column(String(255), default="")
    datastore: Mapped[str] = mapped_column(String(255), default="")
    connection_state: Mapped[str] = mapped_column(String(32), default="connected")
    source: Mapped[str] = mapped_column(String(16), default="vmware")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)

    remote_config: Mapped["RemoteAccessConfig | None"] = relationship(
        back_populates="virtual_machine",
        uselist=False,
        cascade="all, delete-orphan"
    )

class RemoteAccessConfig(Base):
    __tablename__ = "remote_access_configs"
    id: Mapped[int] = mapped_column(primary_key=True)
    vm_id: Mapped[int] = mapped_column(
        ForeignKey("virtual_machines.id", ondelete="CASCADE"),
        unique=True,
        index=True
    )
    protocol: Mapped[str] = mapped_column(String(16), default="rdp")  # rdp | ssh | vnc
    host: Mapped[str] = mapped_column(String(255), default="")
    port: Mapped[int] = mapped_column(Integer, default=3389)
    username: Mapped[str] = mapped_column(String(255), default="")
    password_enc: Mapped[str] = mapped_column(Text, default="")
    private_key_enc: Mapped[str] = mapped_column(Text, default="")
    passphrase_enc: Mapped[str] = mapped_column(Text, default="")
    domain: Mapped[str] = mapped_column(String(255), default="")
    security: Mapped[str] = mapped_column(String(32), default="any")  # any, nla, tls, rdp
    ignore_cert: Mapped[bool] = mapped_column(Boolean, default=True)
    color_depth: Mapped[int] = mapped_column(Integer, default=24)
    resize_method: Mapped[str] = mapped_column(String(32), default="display-update")
    enable_audio: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_clipboard: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)

    virtual_machine: Mapped[VirtualMachine] = relationship(back_populates="remote_config")

class VmAssignment(Base):
    __tablename__ = "vm_assignments"
    __table_args__ = (UniqueConstraint("user_id", "vm_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    vm_id: Mapped[int] = mapped_column(ForeignKey("virtual_machines.id", ondelete="CASCADE"))
    assigned_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class VmwareConnection(Base):
    __tablename__ = "vmware_connections"
    id: Mapped[int] = mapped_column(primary_key=True)
    host: Mapped[str] = mapped_column(String(255))
    username: Mapped[str] = mapped_column(String(255))
    password_enc: Mapped[str] = mapped_column(Text)
    verify_tls: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(128), default="untested")
    last_sync: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(64), index=True)
    detail: Mapped[str] = mapped_column(Text, default="")
    ip: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)

class RemoteSessionLog(Base):
    __tablename__ = "remote_session_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    vm_id: Mapped[int] = mapped_column(ForeignKey("virtual_machines.id"), index=True)
    protocol: Mapped[str] = mapped_column(String(16))
    client_ip: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(32), default="connected")  # connected, disconnected, failed
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class SupportTicket(Base):
    __tablename__ = "support_tickets"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    subject: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)

class SupportTicketMessage(Base):
    __tablename__ = "support_ticket_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("support_tickets.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class UserSession(Base):
    __tablename__ = "user_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    refresh_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

