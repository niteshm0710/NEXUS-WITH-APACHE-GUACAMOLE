"""Apache Guacamole Protocol & guacd Tunnel Service for Cloud4Green Nexus.

Handles the native Guacamole protocol handshake and bidirectional WebSocket streaming
between browser clients and the guacd proxy daemon.
"""

import asyncio
import logging
from typing import AsyncGenerator

log = logging.getLogger("nexus.guacamole")

class GuacamoleError(Exception):
    """User-safe exception for Guacamole / guacd operations."""
    pass

def encode_element(element: str) -> str:
    """Encode a single element into Guacamole protocol format: <length>.<string>"""
    s = str(element)
    return f"{len(s.encode('utf-8'))}.{s}"

def encode_instruction(opcode: str, *args) -> str:
    """Encode an opcode and list of arguments into a Guacamole instruction string:
    <len>.<opcode>,<len>.<arg1>,...;
    """
    parts = [encode_element(opcode)]
    for a in args:
        parts.append(encode_element("" if a is None else str(a)))
    return ",".join(parts) + ";"

def parse_instruction(raw: str) -> tuple[str, list[str]]:
    """Parse a single complete Guacamole instruction string into (opcode, [args])."""
    raw = raw.strip()
    if raw.endswith(";"):
        raw = raw[:-1]
    tokens = []
    idx = 0
    while idx < len(raw):
        dot = raw.find(".", idx)
        if dot == -1:
            break
        try:
            length = int(raw[idx:dot])
        except ValueError:
            break
        val_start = dot + 1
        # Extract based on utf-8 byte length
        raw_bytes = raw[val_start:].encode("utf-8")
        val = raw_bytes[:length].decode("utf-8", errors="replace")
        tokens.append(val)
        # Advance index by dot + 1 + len(val) and optional comma
        idx = val_start + len(val)
        if idx < len(raw) and raw[idx] == ",":
            idx += 1

    if not tokens:
        return "", []
    return tokens[0], tokens[1:]

class GuacdClient:
    """Async client communicating directly with Apache Guacamole daemon (guacd)."""

    def __init__(self, host: str = "guacd", port: int = 4822, timeout: int = 10):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.reader: asyncio.StreamReader | None = None
        self.writer: asyncio.StreamWriter | None = None
        self.connection_id: str | None = None
        self._buffer = ""

    async def connect(self):
        try:
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.timeout
            )
        except asyncio.TimeoutError:
            raise GuacamoleError(f"Connection to guacd timed out ({self.host}:{self.port}).")
        except ConnectionRefusedError:
            raise GuacamoleError(f"Connection refused by guacd daemon ({self.host}:{self.port}). Is guacd running?")
        except OSError as e:
            raise GuacamoleError(f"Network error connecting to guacd daemon: {e}")

    async def send_instruction(self, opcode: str, *args):
        if not self.writer:
            raise GuacamoleError("guacd writer is not connected.")
        instr = encode_instruction(opcode, *args)
        self.writer.write(instr.encode("utf-8"))
        await self.writer.drain()

    async def read_instruction(self) -> tuple[str, list[str]]:
        """Read until a complete instruction ending with ';' is parsed."""
        if not self.reader:
            raise GuacamoleError("guacd reader is not connected.")

        while ";" not in self._buffer:
            chunk = await self.reader.read(4096)
            if not chunk:
                raise GuacamoleError("guacd closed the connection unexpectedly.")
            self._buffer += chunk.decode("utf-8", errors="replace")

        semicolon_pos = self._buffer.find(";")
        raw = self._buffer[:semicolon_pos]
        self._buffer = self._buffer[semicolon_pos + 1:]
        return parse_instruction(raw)

    async def handshake(
        self,
        protocol: str,
        params: dict[str, str],
        width: int = 1280,
        height: int = 800,
        dpi: int = 96
    ) -> str:
        """Perform the standard Guacamole protocol handshake with guacd."""
        # 1. Send select instruction
        await self.send_instruction("select", protocol)

        # 2. Receive args instruction from guacd
        opcode, arg_names = await self.read_instruction()
        if opcode != "args":
            raise GuacamoleError(f"Expected 'args' instruction from guacd, received '{opcode}'.")

        # 3. Send client display size
        await self.send_instruction("size", str(width), str(height), str(dpi))

        # 4. Send client audio capabilities
        await self.send_instruction("audio", "audio/ogg", "audio/mp3")

        # 5. Send client video capabilities
        await self.send_instruction("video")

        # 6. Send client image capabilities
        await self.send_instruction("image", "image/png", "image/jpeg", "image/webp")

        # 7. Send connect instruction with arguments matching the order received from guacd
        param_values = [params.get(arg_name, "") for arg_name in arg_names]
        await self.send_instruction("connect", *param_values)

        # 8. Receive ready instruction containing connection id
        opcode, ready_args = await self.read_instruction()
        if opcode != "ready":
            if opcode == "error":
                err_msg = ready_args[0] if ready_args else "Connection refused by target VM"
                raise GuacamoleError(f"Guacamole connection error: {err_msg}")
            raise GuacamoleError(f"Expected 'ready' from guacd, received '{opcode}'.")

        self.connection_id = ready_args[0] if ready_args else "guac-session"
        return self.connection_id

    async def read_raw_instructions(self) -> AsyncGenerator[str, None]:
        """Generator yielding raw instruction chunks from guacd for WebSocket forwarding."""
        if not self.reader:
            return
        while True:
            chunk = await self.reader.read(8192)
            if not chunk:
                break
            yield chunk.decode("utf-8", errors="replace")

    async def write_raw(self, data: str):
        if self.writer and not self.writer.is_closing():
            self.writer.write(data.encode("utf-8"))
            await self.writer.drain()

    async def close(self):
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception:
                pass
            self.writer = None
            self.reader = None

async def test_guacd(host: str, port: int, timeout: int = 5) -> dict:
    """Test connectivity to the Apache Guacamole daemon (guacd)."""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout
        )
        writer.close()
        await writer.wait_closed()
        return {"status": "connected", "host": host, "port": port, "healthy": True}
    except Exception as e:
        return {"status": "unreachable", "host": host, "port": port, "healthy": False, "error": str(e)}
