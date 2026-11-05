import React, { useEffect, useRef, useState, useCallback } from "react";
// @ts-ignore - guacamole-common-js does not ship official TS types
import Guacamole from "guacamole-common-js";
import {
  Maximize2,
  Minimize2,
  X,
  Keyboard,
  Shield,
  Monitor,
  Terminal,
  Activity,
  RotateCcw,
  AlertTriangle,
  CheckCircle2,
  Loader2,
  Wifi,
  WifiOff,
} from "lucide-react";
import { getAccess, VM } from "./api";

interface GuacamoleSessionProps {
  vm: VM;
  onClose: () => void;
}

export const GuacamoleSession: React.FC<GuacamoleSessionProps> = ({ vm, onClose }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const clientRef = useRef<any>(null);
  const tunnelRef = useRef<any>(null);
  const keyboardRef = useRef<any>(null);
  const mouseRef = useRef<any>(null);

  const [connectionState, setConnectionState] = useState<"connecting" | "connected" | "disconnected" | "error">("connecting");
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [scaleMode, setScaleMode] = useState<"fit" | "native">("fit");
  const [showToolbar, setShowToolbar] = useState<boolean>(true);

  const protocol = vm.remote_access?.protocol?.toUpperCase() || "RDP";

  const disconnectSession = useCallback(() => {
    if (clientRef.current) {
      try {
        clientRef.current.disconnect();
      } catch {}
      clientRef.current = null;
    }
    if (tunnelRef.current) {
      try {
        tunnelRef.current.disconnect();
      } catch {}
      tunnelRef.current = null;
    }
  }, []);

  const sendCtrlAltDel = () => {
    if (!clientRef.current) return;
    const client = clientRef.current;
    // Keysyms: Ctrl (0xFFE3), Alt (0xFFE9), Delete (0xFFFF)
    client.sendKeyEvent(1, 0xffe3); // Ctrl down
    client.sendKeyEvent(1, 0xffe9); // Alt down
    client.sendKeyEvent(1, 0xffff); // Delete down
    setTimeout(() => {
      client.sendKeyEvent(0, 0xffff); // Delete up
      client.sendKeyEvent(0, 0xffe9); // Alt up
      client.sendKeyEvent(0, 0xffe3); // Ctrl up
    }, 100);
  };

  const sendSpecialKey = (keysym: number) => {
    if (!clientRef.current) return;
    clientRef.current.sendKeyEvent(1, keysym);
    setTimeout(() => {
      clientRef.current?.sendKeyEvent(0, keysym);
    }, 80);
  };

  const toggleFullscreen = () => {
    const el = document.getElementById("guac-fullscreen-wrapper");
    if (!el) return;
    if (!document.fullscreenElement) {
      el.requestFullscreen().then(() => setIsFullscreen(true)).catch(() => {});
    } else {
      document.exitFullscreen().then(() => setIsFullscreen(false)).catch(() => {});
    }
  };

  useEffect(() => {
    const handleFsChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };
    document.addEventListener("fullscreenchange", handleFsChange);
    return () => document.removeEventListener("fullscreenchange", handleFsChange);
  }, []);

  useEffect(() => {
    const token = getAccess();
    if (!token) {
      setConnectionState("error");
      setErrorMessage("Authentication token is missing. Please sign in again.");
      return;
    }

    const host = window.location.host;
    const protocolScheme = window.location.protocol === "https:" ? "wss:" : "ws:";
    
    // In dev mode running on port 3001, connect directly to backend on 8000
    const targetHost = window.location.port === "3001" ? `${window.location.hostname}:8000` : host;
    
    const clientWidth = containerRef.current?.clientWidth || 1280;
    const clientHeight = containerRef.current?.clientHeight || 800;
    const wsUrl = `${protocolScheme}//${targetHost}/api/v1/vms/${vm.id}/guac-ws?token=${encodeURIComponent(token)}&width=${clientWidth}&height=${clientHeight}&dpi=96`;

    setConnectionState("connecting");
    setErrorMessage("");

    try {
      const tunnel = new Guacamole.WebSocketTunnel(wsUrl);
      tunnelRef.current = tunnel;

      const client = new Guacamole.Client(tunnel);
      clientRef.current = client;

      // Attach Guacamole display element to DOM
      const display = client.getDisplay();
      const displayEl = display.getElement();

      if (containerRef.current) {
        containerRef.current.innerHTML = "";
        containerRef.current.appendChild(displayEl);
      }

      // State changes
      client.onstatechange = (state: number) => {
        // Guacamole Client States: 0=IDLE, 1=CONNECTING, 2=WAITING, 3=CONNECTED, 4=DISCONNECTING, 5=DISCONNECTED
        if (state === 3) {
          setConnectionState("connected");
        } else if (state === 5) {
          setConnectionState((prev) => (prev === "error" ? "error" : "disconnected"));
        }
      };

      // Error handler
      client.onerror = (status: any) => {
        const msg = status?.message || "Remote connection failed or was closed by the target VM.";
        setConnectionState("error");
        setErrorMessage(msg);
      };

      // Mouse handler
      const mouse = new Guacamole.Mouse(displayEl);
      mouseRef.current = mouse;
      mouse.onmousedown = mouse.onmouseup = mouse.onmousemove = (mouseState: any) => {
        client.sendMouseState(mouseState);
      };

      // Keyboard handler
      const keyboard = new Guacamole.Keyboard(document);
      keyboardRef.current = keyboard;
      keyboard.onkeydown = (keysym: number) => {
        client.sendKeyEvent(1, keysym);
      };
      keyboard.onkeyup = (keysym: number) => {
        client.sendKeyEvent(0, keysym);
      };

      // Scale display to match container
      display.onresize = () => {
        if (!containerRef.current) return;
        const width = display.getWidth();
        const height = display.getHeight();
        if (width > 0 && height > 0) {
          const containerWidth = containerRef.current.clientWidth;
          const containerHeight = containerRef.current.clientHeight;
          const scale = Math.min(containerWidth / width, containerHeight / height);
          display.scale(scale);
        }
      };

      // Connect
      client.connect();

    } catch (err: any) {
      setConnectionState("error");
      setErrorMessage(err.message || "Failed to initialize Apache Guacamole client.");
    }

    return () => {
      if (keyboardRef.current) {
        keyboardRef.current.onkeydown = null;
        keyboardRef.current.onkeyup = null;
      }
      disconnectSession();
    };
  }, [vm.id, disconnectSession]);

  return (
    <div
      id="guac-fullscreen-wrapper"
      className="fixed inset-0 z-50 bg-slate-950 flex flex-col overflow-hidden text-slate-100 select-none"
    >
      {/* Top Header / Control Toolbar */}
      <div className="h-12 bg-slate-900 border-b border-slate-800 px-4 flex items-center justify-between shrink-0">
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2">
            {protocol === "SSH" ? (
              <Terminal className="w-5 h-5 text-emerald-400" />
            ) : (
              <Monitor className="w-5 h-5 text-sky-400" />
            )}
            <span className="font-semibold text-slate-100 tracking-wide">{vm.name}</span>
          </div>

          <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono font-medium border border-slate-700">
            {protocol} • Apache Guacamole
          </span>

          {connectionState === "connected" && (
            <span className="flex items-center space-x-1.5 text-xs text-emerald-400 bg-emerald-950/60 px-2.5 py-0.5 rounded-full border border-emerald-500/30">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>Connected</span>
            </span>
          )}
          {connectionState === "connecting" && (
            <span className="flex items-center space-x-1.5 text-xs text-amber-400 bg-amber-950/60 px-2.5 py-0.5 rounded-full border border-amber-500/30">
              <Loader2 className="w-3 h-3 animate-spin" />
              <span>Establishing Session...</span>
            </span>
          )}
          {connectionState === "disconnected" && (
            <span className="flex items-center space-x-1.5 text-xs text-slate-400 bg-slate-800 px-2.5 py-0.5 rounded-full">
              <WifiOff className="w-3 h-3" />
              <span>Disconnected</span>
            </span>
          )}
          {connectionState === "error" && (
            <span className="flex items-center space-x-1.5 text-xs text-rose-400 bg-rose-950/60 px-2.5 py-0.5 rounded-full border border-rose-500/30">
              <AlertTriangle className="w-3 h-3" />
              <span>Error</span>
            </span>
          )}
        </div>

        {/* Action Controls */}
        <div className="flex items-center space-x-2">
          {connectionState === "connected" && (
            <>
              {protocol === "RDP" && (
                <button
                  onClick={sendCtrlAltDel}
                  className="px-2.5 py-1 text-xs font-medium rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition flex items-center space-x-1.5"
                  title="Send Ctrl+Alt+Delete to remote host"
                >
                  <Keyboard className="w-3.5 h-3.5 text-slate-400" />
                  <span>Ctrl+Alt+Del</span>
                </button>
              )}
              <button
                onClick={() => sendSpecialKey(0xff1b)}
                className="px-2 py-1 text-xs font-medium rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
                title="Send Escape key"
              >
                Esc
              </button>
              <button
                onClick={() => sendSpecialKey(0xff09)}
                className="px-2 py-1 text-xs font-medium rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
                title="Send Tab key"
              >
                Tab
              </button>
            </>
          )}

          <button
            onClick={toggleFullscreen}
            className="p-1.5 rounded hover:bg-slate-800 text-slate-300 hover:text-white transition"
            title={isFullscreen ? "Exit Fullscreen" : "Fullscreen"}
          >
            {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>

          <button
            onClick={() => {
              disconnectSession();
              onClose();
            }}
            className="px-3 py-1 text-xs font-medium rounded bg-rose-600/80 hover:bg-rose-600 text-white transition flex items-center space-x-1"
            title="Disconnect and Close Session"
          >
            <X className="w-3.5 h-3.5" />
            <span>Close</span>
          </button>
        </div>
      </div>

      {/* Main Display Viewport */}
      <div className="relative flex-1 bg-black overflow-hidden flex items-center justify-center">
        {/* Guacamole Canvas Mount Container */}
        <div
          ref={containerRef}
          className="guac-viewport flex items-center justify-center"
          tabIndex={0}
        />

        {/* Overlay for Connecting State */}
        {connectionState === "connecting" && (
          <div className="absolute inset-0 bg-slate-950/85 backdrop-blur-sm flex flex-col items-center justify-center space-y-4 z-20">
            <div className="relative">
              <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                {protocol === "SSH" ? <Terminal className="w-8 h-8" /> : <Monitor className="w-8 h-8" />}
              </div>
              <Loader2 className="w-6 h-6 text-emerald-400 animate-spin absolute -bottom-1 -right-1" />
            </div>
            <div className="text-center">
              <h3 className="text-lg font-medium text-slate-100">Connecting to {vm.name}</h3>
              <p className="text-sm text-slate-400 mt-1 max-w-sm">
                Negotiating secure {protocol} session via Apache Guacamole proxy...
              </p>
            </div>
          </div>
        )}

        {/* Overlay for Error State */}
        {connectionState === "error" && (
          <div className="absolute inset-0 bg-slate-950/90 backdrop-blur-sm flex flex-col items-center justify-center space-y-4 p-6 z-20">
            <div className="w-16 h-16 rounded-2xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-400">
              <AlertTriangle className="w-8 h-8" />
            </div>
            <div className="text-center max-w-md">
              <h3 className="text-lg font-medium text-slate-100">Connection Failed</h3>
              <p className="text-sm text-slate-400 mt-2 bg-slate-900 border border-slate-800 p-3 rounded text-left font-mono">
                {errorMessage || "Unable to establish connection with remote virtual machine."}
              </p>
              <p className="text-xs text-slate-500 mt-3">
                Verify target machine is powered on, remote access credentials are correct, and target port is reachable.
              </p>
            </div>
            <div className="flex space-x-3 pt-2">
              <button
                onClick={() => {
                  disconnectSession();
                  onClose();
                }}
                className="px-4 py-2 text-sm font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
              >
                Back to Dashboard
              </button>
            </div>
          </div>
        )}

        {/* Overlay for Disconnected State */}
        {connectionState === "disconnected" && (
          <div className="absolute inset-0 bg-slate-950/90 backdrop-blur-sm flex flex-col items-center justify-center space-y-4 z-20">
            <div className="w-16 h-16 rounded-2xl bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-400">
              <WifiOff className="w-8 h-8" />
            </div>
            <div className="text-center">
              <h3 className="text-lg font-medium text-slate-100">Remote Session Ended</h3>
              <p className="text-sm text-slate-400 mt-1">
                Your connection to {vm.name} has been closed.
              </p>
            </div>
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white transition"
            >
              Return to Portal
            </button>
          </div>
        )}
      </div>

      {/* Footer Info Bar */}
      <div className="h-7 bg-slate-900 border-t border-slate-800 px-4 flex items-center justify-between text-xs text-slate-400 shrink-0">
        <div className="flex items-center space-x-4">
          <span>Target: <strong className="text-slate-300 font-mono">{vm.ip_address || "Internal IP"}</strong></span>
          <span>Protocol: <strong className="text-slate-300">{protocol}</strong></span>
          <span>Port: <strong className="text-slate-300 font-mono">{vm.remote_access?.port || (protocol === "SSH" ? 22 : 3389)}</strong></span>
        </div>
        <div>
          <span>Cloud4Green Nexus Secure Gateway</span>
        </div>
      </div>
    </div>
  );
};

