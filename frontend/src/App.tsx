import React, { useEffect, useState, useMemo } from "react";
import {
  Server,
  LifeBuoy,
  User as UserIcon,
  LogOut,
  Play,
  Square,
  RotateCw,
  MonitorPlay,
  Users,
  Link2,
  Cloud,
  ScrollText,
  LayoutDashboard,
  Eye,
  EyeOff,
  X,
  ArrowRight,
  Mail,
  Calendar,
  Clock,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  RefreshCw,
  Plus,
  Search,
  ExternalLink,
  Shield,
  HardDrive,
  Cpu,
  Layers,
  Activity,
  Check,
  Maximize2,
  Minimize2,
  Keyboard,
  Cast,
  Settings,
  Lock,
  Terminal,
  Monitor,
  Key,
} from "lucide-react";
import {
  api,
  setTokens,
  clearTokens,
  getRefresh,
  getAccess,
  User,
  VM,
  Assignment,
  AuditItem,
  SupportTicketItem,
  OverviewData,
  RemoteStatus,
  RemoteConfigDetail,
  RemoteSessionItem,
} from "./api";
import { GuacamoleSession } from "./GuacamoleSession";

const BRAND_NAME = "Cloud4Green Nexus";
const APP_TAGLINE = "Enterprise Remote Infrastructure & Virtualization Portal";
const FOOTER_TEXT = "Powered by Cloud4green Technologies & Apache Guacamole";

// ---------- Formatters & Helpers ----------
function parseUtcDate(iso?: string | null): Date | null {
  if (!iso) return null;
  let s = iso.trim();
  if (!s.endsWith("Z") && !/[+-]\d{2}(:\d{2})?$/.test(s)) {
    s = s.replace(" ", "T") + "Z";
  }
  const d = new Date(s);
  return isNaN(d.getTime()) ? null : d;
}

function formatDate(iso?: string | null): string {
  if (!iso) return "—";
  try {
    const d = parseUtcDate(iso);
    if (!d) return iso;
    return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  } catch {
    return iso;
  }
}

function formatDateTime(iso?: string | null): string {
  if (!iso) return "—";
  try {
    const d = parseUtcDate(iso);
    if (!d) return iso;
    return new Intl.DateTimeFormat(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
      timeZoneName: "short",
    }).format(d);
  } catch {
    return iso;
  }
}

// ---------- OS Visual Identity & Detection ----------
function WindowsIcon({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className} aria-hidden="true">
      <path d="M0 3.449L9.75 2.1v9.451H0m10.949-9.602L24 0v11.4H10.949M0 12.6h9.75v9.451L0 20.699M10.949 12.6H24V24l-13.051-1.802" />
    </svg>
  );
}

function UbuntuIcon({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className} aria-hidden="true">
      <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm-7.05 9.176a1.59 1.59 0 1 1 0 3.178 1.59 1.59 0 0 1 0-3.178zm15.485 5.92a1.59 1.59 0 1 1 0-3.18 1.59 1.59 0 0 1 0 3.18zm-4.735 4.887a1.59 1.59 0 1 1-3.178 0 1.59 1.59 0 0 1 3.178 0zM12 2.769c3.992 0 7.37 2.616 8.52 6.273a3.524 3.524 0 0 0-2.316 2.054A6.877 6.877 0 0 0 12 6.892c-3.18 0-5.876 2.16-6.67 5.108a3.535 3.535 0 0 0-2.327-2.07C4.167 6.002 7.695 2.769 12 2.769zm-6.67 8.338a3.54 3.54 0 0 0 2.327 2.07A6.877 6.877 0 0 0 12 17.108c2.42 0 4.54-1.246 5.76-3.14a3.524 3.524 0 0 0 2.316 2.054C18.92 19.384 15.69 21.23 12 21.23c-4.305 0-7.833-2.767-8.996-6.646.993-.82 1.626-2.05 1.626-3.477z" />
    </svg>
  );
}

function LinuxIcon({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className} aria-hidden="true">
      <path d="M12.002 2c-2.4 0-4.002 1.8-4.002 4.4 0 1.5.6 3.1 1.2 4.1-.3.5-.8 1.1-1.4 1.7-1.8 1.8-3.8 4.3-3.8 7.3 0 1.3.9 2.5 2.2 2.5 2.3 0 3.7-1.4 5.8-1.4 2.1 0 3.5 1.4 5.8 1.4 1.3 0 2.2-1.2 2.2-2.5 0-3-2-5.5-3.8-7.3-.6-.6-1.1-1.2-1.4-1.7.6-1 1.2-2.6 1.2-4.1 0-2.6-1.6-4.4-4-4.4zm-1.5 4.5a.8.8 0 1 1 0 1.6.8.8 0 0 1 0-1.6zm3 0a.8.8 0 1 1 0 1.6.8.8 0 0 1 0-1.6zm-2.2 2.2h1.4c.2 0 .4.2.3.4-.2.5-.5.9-.7.9s-.5-.4-.7-.9c-.1-.2.1-.4.3-.4z" />
    </svg>
  );
}

function AppleIcon({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className} aria-hidden="true">
      <path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.81-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M15.97 6.37c.61-.75 1.04-1.8 0.92-2.87-.92.04-2.02.62-2.67 1.38-.56.65-1.05 1.71-.92 2.74 1.03.08 2.06-.5 2.67-1.25" />
    </svg>
  );
}

interface OsMeta {
  type: "windows-server" | "windows" | "ubuntu" | "linux" | "macos" | "esxi" | "generic";
  label: string;
  badge: string;
  icon: React.ComponentType<{ className?: string }>;
  iconBg: string;
  iconColor: string;
  badgeBg: string;
  accentBorder: string;
}

function detectOs(osName?: string): OsMeta {
  const s = (osName || "").toLowerCase();
  if (s.includes("server") && s.includes("windows")) {
    return {
      type: "windows-server",
      label: "Windows Server",
      badge: "Win Server",
      icon: WindowsIcon,
      iconBg: "bg-blue-500/10 border-blue-500/30",
      iconColor: "text-blue-400",
      badgeBg: "bg-blue-950 text-blue-300 border-blue-800",
      accentBorder: "hover:border-blue-500/50",
    };
  }
  if (s.includes("windows")) {
    return {
      type: "windows",
      label: "Windows",
      badge: "Windows",
      icon: WindowsIcon,
      iconBg: "bg-sky-500/10 border-sky-500/30",
      iconColor: "text-sky-400",
      badgeBg: "bg-sky-950 text-sky-300 border-sky-800",
      accentBorder: "hover:border-sky-500/50",
    };
  }
  if (s.includes("ubuntu")) {
    return {
      type: "ubuntu",
      label: "Ubuntu Linux",
      badge: "Ubuntu",
      icon: UbuntuIcon,
      iconBg: "bg-orange-500/10 border-orange-500/30",
      iconColor: "text-orange-400",
      badgeBg: "bg-orange-950 text-orange-300 border-orange-800",
      accentBorder: "hover:border-orange-500/50",
    };
  }
  if (s.includes("linux") || s.includes("debian") || s.includes("centos") || s.includes("rhel") || s.includes("fedora")) {
    return {
      type: "linux",
      label: "Enterprise Linux",
      badge: "Linux",
      icon: LinuxIcon,
      iconBg: "bg-emerald-500/10 border-emerald-500/30",
      iconColor: "text-emerald-400",
      badgeBg: "bg-emerald-950 text-emerald-300 border-emerald-800",
      accentBorder: "hover:border-emerald-500/50",
    };
  }
  if (s.includes("mac") || s.includes("darwin") || s.includes("osx")) {
    return {
      type: "macos",
      label: "macOS",
      badge: "macOS",
      icon: AppleIcon,
      iconBg: "bg-slate-500/10 border-slate-500/30",
      iconColor: "text-slate-300",
      badgeBg: "bg-slate-800 text-slate-300 border-slate-700",
      accentBorder: "hover:border-slate-500/50",
    };
  }
  if (s.includes("esxi") || s.includes("vmware")) {
    return {
      type: "esxi",
      label: "VMware ESXi",
      badge: "ESXi",
      icon: Server,
      iconBg: "bg-indigo-500/10 border-indigo-500/30",
      iconColor: "text-indigo-400",
      badgeBg: "bg-indigo-950 text-indigo-300 border-indigo-800",
      accentBorder: "hover:border-indigo-500/50",
    };
  }
  return {
    type: "generic",
    label: "Virtual Machine",
    badge: "Virtual Machine",
    icon: Server,
    iconBg: "bg-slate-800 border-slate-700",
    iconColor: "text-slate-400",
    badgeBg: "bg-slate-800 text-slate-300 border-slate-700",
    accentBorder: "hover:border-slate-600",
  };
}

export default function App() {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [loadingInitial, setLoadingInitial] = useState(true);

  // Login form state
  const [emailInput, setEmailInput] = useState("");
  const [passwordInput, setPasswordInput] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loginError, setLoginError] = useState("");
  const [loginLoading, setLoginLoading] = useState(false);

  // App navigation
  const [activeTab, setActiveTab] = useState<"vms" | "overview" | "users" | "assignments" | "vmware" | "sessions" | "audit" | "support">("vms");

  // Real Data states
  const [vms, setVms] = useState<VM[]>([]);
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [usersList, setUsersList] = useState<User[]>([]);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditItem[]>([]);
  const [remoteSessions, setRemoteSessions] = useState<RemoteSessionItem[]>([]);
  const [tickets, setTickets] = useState<SupportTicketItem[]>([]);

  // Search & filter
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "on" | "off">("all");

  // Active Guacamole Session
  const [activeGuacVm, setActiveGuacVm] = useState<VM | null>(null);

  // Admin Remote Access Config Modal
  const [configModalVm, setConfigModalVm] = useState<VM | null>(null);
  const [configForm, setConfigForm] = useState<Partial<RemoteConfigDetail>>({
    protocol: "rdp",
    port: 3389,
    host: "",
    username: "",
    domain: "",
    security: "any",
    ignore_cert: true,
  });
  const [configPassword, setConfigPassword] = useState("");
  const [configPrivateKey, setConfigPrivateKey] = useState("");
  const [configSaveLoading, setConfigSaveLoading] = useState(false);
  const [configModalMsg, setConfigModalMsg] = useState("");

  // Sync state
  const [syncLoading, setSyncLoading] = useState(false);
  const [syncResult, setSyncResult] = useState<string | null>(null);

  // Notification banners
  const [banner, setBanner] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const showBanner = (text: string, type: "success" | "error" = "success") => {
    setBanner({ type, text });
    setTimeout(() => setBanner(null), 5000);
  };

  // Check initial session
  useEffect(() => {
    async function initAuth() {
      const token = getAccess();
      if (!token) {
        setLoadingInitial(false);
        return;
      }
      try {
        const u = await api<User>("/auth/me");
        setCurrentUser(u);
      } catch {
        clearTokens();
        setCurrentUser(null);
      } finally {
        setLoadingInitial(false);
      }
    }
    initAuth();
  }, []);

  // Fetch data based on active tab
  const refreshData = async () => {
    if (!currentUser) return;
    try {
      if (activeTab === "vms") {
        const data = await api<VM[]>("/vms");
        setVms(data);
      } else if (activeTab === "overview" && currentUser.role === "admin") {
        const data = await api<OverviewData>("/admin/overview");
        setOverview(data);
      } else if (activeTab === "users" && currentUser.role === "admin") {
        const data = await api<User[]>("/admin/users");
        setUsersList(data);
      } else if (activeTab === "assignments" && currentUser.role === "admin") {
        const [asgs, allVms, allUsers] = await Promise.all([
          api<Assignment[]>("/admin/assignments"),
          api<VM[]>("/admin/vms"),
          api<User[]>("/admin/users"),
        ]);
        setAssignments(asgs);
        setVms(allVms);
        setUsersList(allUsers);
      } else if (activeTab === "sessions" && currentUser.role === "admin") {
        const data = await api<RemoteSessionItem[]>("/admin/remote-sessions");
        setRemoteSessions(data);
      } else if (activeTab === "audit" && currentUser.role === "admin") {
        const data = await api<AuditItem[]>("/admin/audit-logs");
        setAuditLogs(data);
      } else if (activeTab === "support") {
        const data = await api<SupportTicketItem[]>("/support/tickets");
        setTickets(data);
      }
    } catch (err: any) {
      showBanner(err.message || "Failed to load data.", "error");
    }
  };

  useEffect(() => {
    if (currentUser) {
      refreshData();
    }
  }, [currentUser, activeTab]);

  // Login handler
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginError("");
    setLoginLoading(true);
    try {
      const res = await api<{ access_token: string; refresh_token: string; user: User }>("/auth/login", "POST", {
        email: emailInput,
        password: passwordInput,
      });
      setTokens(res.access_token, res.refresh_token);
      setCurrentUser(res.user);
      setActiveTab("vms");
    } catch (err: any) {
      setLoginError(err.message || "Sign in failed.");
    } finally {
      setLoginLoading(false);
    }
  };

  const handleLogout = async () => {
    const rf = getRefresh();
    if (rf) {
      await api("/auth/logout", "POST", { refresh_token: rf }).catch(() => {});
    }
    clearTokens();
    setCurrentUser(null);
    setActiveGuacVm(null);
  };

  // Power action handler
  const handlePower = async (vmId: number, action: "start" | "stop" | "restart") => {
    try {
      await api(`/vms/${vmId}/power`, "POST", { action });
      showBanner(`Power command '${action}' sent to VM #${vmId}.`);
      refreshData();
    } catch (err: any) {
      showBanner(err.message || "Power operation failed.", "error");
    }
  };

  // VM Inventory Sync handler (Real VMware)
  const handleSync = async () => {
    setSyncLoading(true);
    setSyncResult(null);
    try {
      const res = await api<{ message: string; synced: number }>("/admin/vms/sync", "POST");
      setSyncResult(res.message);
      showBanner(res.message, "success");
      refreshData();
    } catch (err: any) {
      showBanner(err.message || "VMware synchronization failed.", "error");
    } finally {
      setSyncLoading(false);
    }
  };

  // Open Remote Config modal for Admin
  const openRemoteConfigModal = async (vm: VM) => {
    setConfigModalVm(vm);
    setConfigModalMsg("");
    setConfigPassword("");
    setConfigPrivateKey("");
    try {
      const detail = await api<RemoteConfigDetail>(`/admin/vms/${vm.id}/remote-config`);
      setConfigForm({
        ...detail,
        host: detail.host || vm.ip_address || "",
        port: detail.port || (detail.protocol === "ssh" ? 22 : 3389),
      });
    } catch {
      setConfigForm({
        protocol: "rdp",
        port: 3389,
        host: vm.ip_address || "",
        username: "",
        domain: "",
        security: "any",
        ignore_cert: true,
      });
    }
  };

  const saveRemoteConfig = async () => {
    if (!configModalVm) return;
    setConfigSaveLoading(true);
    setConfigModalMsg("");
    try {
      const payload: any = {
        protocol: configForm.protocol,
        host: configForm.host,
        port: Number(configForm.port),
        username: configForm.username || "",
        domain: configForm.domain || "",
        security: configForm.security || "any",
        ignore_cert: configForm.ignore_cert ?? true,
        is_active: true,
      };
      if (configPassword.trim()) {
        payload.password = configPassword.trim();
      }
      if (configPrivateKey.trim()) {
        payload.private_key = configPrivateKey.trim();
      }

      await api(`/admin/vms/${configModalVm.id}/remote-config`, "PUT", payload);
      showBanner(`Remote access configuration saved for ${configModalVm.name}.`);
      setConfigModalVm(null);
      refreshData();
    } catch (err: any) {
      setConfigModalMsg(err.message || "Failed to save configuration.");
    } finally {
      setConfigSaveLoading(false);
    }
  };

  // Filtered VM list
  const filteredVms = useMemo(() => {
    return vms.filter((v) => {
      const matchSearch =
        v.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        v.guest_os.toLowerCase().includes(searchQuery.toLowerCase()) ||
        v.ip_address.includes(searchQuery);
      const matchStatus = statusFilter === "all" || v.power_state === statusFilter;
      return matchSearch && matchStatus;
    });
  }, [vms, searchQuery, statusFilter]);

  // Loading screen
  if (loadingInitial) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center text-slate-300">
        <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 animate-spin mb-4">
          <RefreshCw className="w-6 h-6" />
        </div>
        <p className="text-sm font-medium tracking-wide">Initializing Cloud4Green Nexus...</p>
      </div>
    );
  }

  // Login View
  if (!currentUser) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col justify-between selection:bg-emerald-500 selection:text-white">
        <div className="flex-1 flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-slate-900/80 backdrop-blur-xl border border-slate-800 rounded-2xl p-8 shadow-2xl">
            {/* Header / Logo */}
            <div className="flex items-center space-x-3 mb-6">
              <img
                src="/assets/cloud4green-logo.png"
                alt="Cloud4Green Logo"
                className="h-10 w-auto object-contain"
                onError={(e) => {
                  (e.target as HTMLElement).style.display = "none";
                }}
              />
              <div>
                <h1 className="text-xl font-bold text-white tracking-tight">{BRAND_NAME}</h1>
                <p className="text-xs text-emerald-400 font-medium">with Apache Guacamole</p>
              </div>
            </div>

            <p className="text-sm text-slate-400 mb-6 leading-relaxed">
              Sign in with your enterprise credentials to access your assigned virtual machines.
            </p>

            {loginError && (
              <div className="mb-6 p-3 rounded-lg bg-rose-950/60 border border-rose-500/30 text-rose-300 text-xs flex items-center space-x-2">
                <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
                <span>{loginError}</span>
              </div>
            )}

            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Email Address or Username
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                  <input
                    type="text"
                    required
                    value={emailInput}
                    onChange={(e) => setEmailInput(e.target.value)}
                    placeholder="user@cloud4green.com"
                    className="w-full pl-9 pr-3 py-2.5 bg-slate-950 border border-slate-700 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Password
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                  <input
                    type={showPassword ? "text" : "password"}
                    required
                    value={passwordInput}
                    onChange={(e) => setPasswordInput(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full pl-9 pr-10 py-2.5 bg-slate-950 border border-slate-700 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-3 text-slate-500 hover:text-slate-300"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={loginLoading}
                className="w-full py-2.5 px-4 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-sm transition shadow-lg shadow-emerald-950/50 flex items-center justify-center space-x-2 disabled:opacity-50 mt-2"
              >
                {loginLoading ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Signing in...</span>
                  </>
                ) : (
                  <>
                    <span>Sign In</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>

            <div className="mt-6 pt-6 border-t border-slate-800 text-center">
              <p className="text-xs text-slate-500">
                Browser-based high-performance RDP, SSH, and VNC remote access.
              </p>
            </div>
          </div>
        </div>

        {/* Footer */}
        <footer className="text-center py-4 text-xs text-slate-600 border-t border-slate-900">
          {FOOTER_TEXT}
        </footer>
      </div>
    );
  }

  // Main Authenticated Portal
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Banner Notifications */}
      {banner && (
        <div
          className={`px-4 py-2 text-sm font-medium flex items-center justify-between transition-all ${
            banner.type === "success"
              ? "bg-emerald-900/80 border-b border-emerald-500/30 text-emerald-200"
              : "bg-rose-900/80 border-b border-rose-500/30 text-rose-200"
          }`}
        >
          <div className="flex items-center space-x-2">
            {banner.type === "success" ? <CheckCircle2 className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
            <span>{banner.text}</span>
          </div>
          <button onClick={() => setBanner(null)} className="hover:opacity-75">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Top Navbar */}
      <header className="h-16 bg-slate-900/90 backdrop-blur-md border-b border-slate-800 px-6 flex items-center justify-between sticky top-0 z-40">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-3">
            <img
              src="/assets/cloud4green-logo.png"
              alt="Cloud4Green Logo"
              className="h-8 w-auto object-contain"
              onError={(e) => {
                (e.target as HTMLElement).style.display = "none";
              }}
            />
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-base text-white tracking-tight">{BRAND_NAME}</span>
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800 uppercase tracking-wider">
                  Guacamole
                </span>
              </div>
              <p className="text-[11px] text-slate-400 hidden sm:block">{APP_TAGLINE}</p>
            </div>
          </div>
        </div>

        {/* User info & Logout */}
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-3 text-right">
            <div>
              <div className="text-sm font-medium text-slate-200">{currentUser.full_name}</div>
              <div className="text-xs text-slate-400 flex items-center justify-end space-x-1">
                <span>{currentUser.email}</span>
                <span className="capitalize text-emerald-400 font-medium">({currentUser.role})</span>
              </div>
            </div>
            <div className="w-9 h-9 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 font-semibold">
              {currentUser.full_name.charAt(0).toUpperCase()}
            </div>
          </div>

          <button
            onClick={handleLogout}
            className="p-2 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-slate-800 transition"
            title="Sign Out"
          >
            <LogOut className="w-5 h-5" />
          </button>
        </div>
      </header>

      {/* Main Body with Subnav */}
      <div className="flex-1 flex flex-col max-w-7xl w-full mx-auto p-6 space-y-6">
        {/* Navigation Tabs */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-2">
          <div className="flex items-center space-x-1">
            <button
              onClick={() => setActiveTab("vms")}
              className={`px-3.5 py-2 rounded-lg text-sm font-medium transition flex items-center space-x-2 ${
                activeTab === "vms"
                  ? "bg-emerald-600/20 text-emerald-400 border border-emerald-500/30"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
              }`}
            >
              <Server className="w-4 h-4" />
              <span>Virtual Machines</span>
              <span className="text-xs px-1.5 py-0.2 rounded bg-slate-800 text-slate-300 ml-1">
                {vms.length}
              </span>
            </button>

            {currentUser.role === "admin" && (
              <>
                <button
                  onClick={() => setActiveTab("overview")}
                  className={`px-3.5 py-2 rounded-lg text-sm font-medium transition flex items-center space-x-2 ${
                    activeTab === "overview"
                      ? "bg-emerald-600/20 text-emerald-400 border border-emerald-500/30"
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
                  }`}
                >
                  <LayoutDashboard className="w-4 h-4" />
                  <span>Overview</span>
                </button>

                <button
                  onClick={() => setActiveTab("assignments")}
                  className={`px-3.5 py-2 rounded-lg text-sm font-medium transition flex items-center space-x-2 ${
                    activeTab === "assignments"
                      ? "bg-emerald-600/20 text-emerald-400 border border-emerald-500/30"
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
                  }`}
                >
                  <Link2 className="w-4 h-4" />
                  <span>Assignments</span>
                </button>

                <button
                  onClick={() => setActiveTab("users")}
                  className={`px-3.5 py-2 rounded-lg text-sm font-medium transition flex items-center space-x-2 ${
                    activeTab === "users"
                      ? "bg-emerald-600/20 text-emerald-400 border border-emerald-500/30"
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
                  }`}
                >
                  <Users className="w-4 h-4" />
                  <span>Users</span>
                </button>

                <button
                  onClick={() => setActiveTab("sessions")}
                  className={`px-3.5 py-2 rounded-lg text-sm font-medium transition flex items-center space-x-2 ${
                    activeTab === "sessions"
                      ? "bg-emerald-600/20 text-emerald-400 border border-emerald-500/30"
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
                  }`}
                >
                  <Activity className="w-4 h-4" />
                  <span>Remote Sessions</span>
                </button>

                <button
                  onClick={() => setActiveTab("audit")}
                  className={`px-3.5 py-2 rounded-lg text-sm font-medium transition flex items-center space-x-2 ${
                    activeTab === "audit"
                      ? "bg-emerald-600/20 text-emerald-400 border border-emerald-500/30"
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
                  }`}
                >
                  <ScrollText className="w-4 h-4" />
                  <span>Audit Logs</span>
                </button>
              </>
            )}

            <button
              onClick={() => setActiveTab("support")}
              className={`px-3.5 py-2 rounded-lg text-sm font-medium transition flex items-center space-x-2 ${
                activeTab === "support"
                  ? "bg-emerald-600/20 text-emerald-400 border border-emerald-500/30"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
              }`}
            >
              <LifeBuoy className="w-4 h-4" />
              <span>Support</span>
            </button>
          </div>

          {/* Sync button for Admins */}
          {currentUser.role === "admin" && (
            <button
              onClick={handleSync}
              disabled={syncLoading}
              className="px-3.5 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-700 text-xs font-medium transition flex items-center space-x-2 disabled:opacity-50"
              title="Synchronize real VM inventory from VMware vCenter"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${syncLoading ? "animate-spin text-emerald-400" : ""}`} />
              <span>{syncLoading ? "Syncing..." : "Sync VMware Inventory"}</span>
            </button>
          )}
        </div>

        {/* =========================================================================
            TAB: VIRTUAL MACHINES
        ========================================================================= */}
        {activeTab === "vms" && (
          <div className="space-y-6">
            {/* Search & Status Filters */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-slate-900/60 p-4 rounded-xl border border-slate-800">
              <div className="relative w-full sm:w-80">
                <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                <input
                  type="text"
                  placeholder="Filter by name, OS, or IP..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition"
                />
              </div>

              <div className="flex items-center space-x-2 w-full sm:w-auto">
                <button
                  onClick={() => setStatusFilter("all")}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                    statusFilter === "all"
                      ? "bg-slate-800 text-white border border-slate-700"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  All ({vms.length})
                </button>
                <button
                  onClick={() => setStatusFilter("on")}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                    statusFilter === "on"
                      ? "bg-emerald-950 text-emerald-300 border border-emerald-700"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  Running ({vms.filter((v) => v.power_state === "on").length})
                </button>
                <button
                  onClick={() => setStatusFilter("off")}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                    statusFilter === "off"
                      ? "bg-slate-800 text-slate-300 border border-slate-700"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  Stopped ({vms.filter((v) => v.power_state !== "on").length})
                </button>
              </div>
            </div>

            {/* Empty State */}
            {filteredVms.length === 0 && (
              <div className="py-16 text-center bg-slate-900/30 rounded-2xl border border-slate-800/80 p-8">
                <div className="w-16 h-16 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-500 mx-auto mb-4">
                  <Server className="w-8 h-8" />
                </div>
                <h3 className="text-base font-semibold text-slate-200">
                  {currentUser.role === "admin"
                    ? "No virtual machines have been synchronized yet."
                    : "No virtual machines are assigned to your account."}
                </h3>
                <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
                  {currentUser.role === "admin"
                    ? "Connect your VMware vCenter host in the administration settings and click 'Sync VMware Inventory' to import your real infrastructure."
                    : "Please contact your system administrator to assign virtual machines to your account."}
                </p>
                {currentUser.role === "admin" && (
                  <button
                    onClick={handleSync}
                    disabled={syncLoading}
                    className="mt-4 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium transition inline-flex items-center space-x-2"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${syncLoading ? "animate-spin" : ""}`} />
                    <span>Synchronize VMware Now</span>
                  </button>
                )}
              </div>
            )}

            {/* VM Cards Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredVms.map((vm) => {
                const os = detectOs(vm.guest_os);
                const isRunning = vm.power_state === "on";
                const isConfigured = vm.remote_access?.configured ?? false;
                const proto = vm.remote_access?.protocol?.toUpperCase();

                return (
                  <div
                    key={vm.id}
                    className={`bg-slate-900/80 backdrop-blur border border-slate-800 rounded-xl p-5 flex flex-col justify-between transition duration-200 hover:shadow-xl hover:shadow-slate-950/50 ${os.accentBorder}`}
                  >
                    <div>
                      {/* Top Bar: OS Badge & Power Status */}
                      <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center space-x-2.5">
                          <div className={`p-2 rounded-lg border ${os.iconBg} ${os.iconColor}`}>
                            <os.icon className="w-5 h-5" />
                          </div>
                          <div>
                            <span className="text-[11px] font-semibold text-slate-400 block tracking-wide">
                              {os.label}
                            </span>
                            <span className="text-sm font-bold text-white tracking-tight line-clamp-1">
                              {vm.name}
                            </span>
                          </div>
                        </div>

                        {/* Power Badge */}
                        <div className="flex items-center space-x-1.5">
                          <span
                            className={`w-2 h-2 rounded-full ${
                              isRunning ? "bg-emerald-400 animate-pulse" : "bg-slate-600"
                            }`}
                          />
                          <span
                            className={`text-xs font-medium uppercase tracking-wider ${
                              isRunning ? "text-emerald-400" : "text-slate-500"
                            }`}
                          >
                            {vm.power_state}
                          </span>
                        </div>
                      </div>

                      {/* Specs info */}
                      <div className="grid grid-cols-3 gap-2 py-3 px-3 rounded-lg bg-slate-950/70 border border-slate-800/80 mb-4 text-center">
                        <div>
                          <div className="text-[10px] text-slate-500 font-medium uppercase">vCPU</div>
                          <div className="text-xs font-mono font-semibold text-slate-200">{vm.cpu} Core</div>
                        </div>
                        <div>
                          <div className="text-[10px] text-slate-500 font-medium uppercase">RAM</div>
                          <div className="text-xs font-mono font-semibold text-slate-200">
                            {Math.round(vm.ram_mb / 1024)} GB
                          </div>
                        </div>
                        <div>
                          <div className="text-[10px] text-slate-500 font-medium uppercase">Disk</div>
                          <div className="text-xs font-mono font-semibold text-slate-200">
                            {vm.storage_gb || "—"} GB
                          </div>
                        </div>
                      </div>

                      {/* Network & Host details */}
                      <div className="space-y-1.5 text-xs text-slate-400 mb-4">
                        <div className="flex justify-between">
                          <span className="text-slate-500">IP Address:</span>
                          <span className="font-mono text-slate-300 font-medium">
                            {vm.ip_address || "None reported"}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-500">ESXi Host:</span>
                          <span className="text-slate-300 truncate max-w-[180px]">
                            {vm.host || "VMware Cluster"}
                          </span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-slate-500">Remote Access:</span>
                          {isConfigured ? (
                            <span className="inline-flex items-center space-x-1 text-[11px] font-semibold text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800/60">
                              <span>{proto}</span>
                              <Check className="w-3 h-3 text-emerald-400" />
                            </span>
                          ) : (
                            <span className="text-[11px] text-slate-500 bg-slate-800 px-2 py-0.5 rounded">
                              Not Configured
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Actions Toolbar */}
                    <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between gap-2">
                      {/* CONNECT Button */}
                      {isRunning && isConfigured ? (
                        <button
                          onClick={() => setActiveGuacVm(vm)}
                          className="flex-1 py-2 px-3 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold tracking-wide transition shadow-md shadow-emerald-950/50 flex items-center justify-center space-x-1.5"
                          title={`Connect via ${proto} using Apache Guacamole`}
                        >
                          <MonitorPlay className="w-4 h-4" />
                          <span>CONNECT ({proto})</span>
                        </button>
                      ) : !isRunning ? (
                        <div className="flex-1 py-2 px-3 rounded-lg bg-slate-800/50 text-slate-500 text-xs text-center border border-slate-800">
                          Power on to connect
                        </div>
                      ) : (
                        <div className="flex-1 py-2 px-3 rounded-lg bg-slate-800/50 text-slate-500 text-xs text-center border border-slate-800">
                          Remote access not configured
                        </div>
                      )}

                      {/* Power Controls */}
                      <div className="flex items-center space-x-1">
                        {isRunning ? (
                          <button
                            onClick={() => handlePower(vm.id, "stop")}
                            className="p-2 rounded-lg bg-slate-800 hover:bg-rose-950/80 hover:text-rose-400 text-slate-400 border border-slate-700/80 transition"
                            title="Power Off VM"
                          >
                            <Square className="w-3.5 h-3.5" />
                          </button>
                        ) : (
                          <button
                            onClick={() => handlePower(vm.id, "start")}
                            className="p-2 rounded-lg bg-slate-800 hover:bg-emerald-950/80 hover:text-emerald-400 text-slate-400 border border-slate-700/80 transition"
                            title="Power On VM"
                          >
                            <Play className="w-3.5 h-3.5" />
                          </button>
                        )}

                        {/* Admin Configure Remote Access */}
                        {currentUser.role === "admin" && (
                          <button
                            onClick={() => openRemoteConfigModal(vm)}
                            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white border border-slate-700/80 transition"
                            title="Configure Remote Access Protocol & Credentials"
                          >
                            <Settings className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* =========================================================================
            TAB: OVERVIEW (ADMIN ONLY)
        ========================================================================= */}
        {activeTab === "overview" && currentUser.role === "admin" && overview && (
          <div className="space-y-6">
            {/* Top Metric Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                <div className="text-xs font-medium text-slate-400 uppercase tracking-wide">Total Users</div>
                <div className="text-2xl font-bold text-white mt-1">{overview.total_users}</div>
                <div className="text-xs text-slate-500 mt-1">Enterprise accounts</div>
              </div>

              <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                <div className="text-xs font-medium text-slate-400 uppercase tracking-wide">Synchronized VMs</div>
                <div className="text-2xl font-bold text-white mt-1">{overview.total_vms}</div>
                <div className="text-xs text-emerald-400 mt-1">
                  {overview.running_vms} running • {overview.stopped_vms} stopped
                </div>
              </div>

              <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                <div className="text-xs font-medium text-slate-400 uppercase tracking-wide">Active Assignments</div>
                <div className="text-2xl font-bold text-white mt-1">{overview.total_assignments}</div>
                <div className="text-xs text-slate-500 mt-1">Controlled VM access</div>
              </div>

              <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                <div className="text-xs font-medium text-slate-400 uppercase tracking-wide">Remote Access</div>
                <div className="text-2xl font-bold text-emerald-400 mt-1">{overview.configured_remote}</div>
                <div className="text-xs text-slate-500 mt-1">Guacamole enabled machines</div>
              </div>
            </div>

            {/* Service Status Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Apache Guacamole Daemon Status */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center space-x-2">
                    <Monitor className="w-5 h-5 text-emerald-400" />
                    <h3 className="font-semibold text-white">Apache Guacamole (guacd)</h3>
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-medium ${
                      overview.guacamole.healthy
                        ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                        : "bg-amber-950 text-amber-300 border border-amber-800"
                    }`}
                  >
                    {overview.guacamole.healthy ? "Connected & Healthy" : "Daemon Standby"}
                  </span>
                </div>
                <div className="space-y-2 text-xs text-slate-400">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Service Endpoint:</span>
                    <span className="font-mono text-slate-300">{overview.guacamole.host}:{overview.guacamole.port}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Supported Protocols:</span>
                    <span className="text-slate-300 font-semibold">RDP, SSH, VNC</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Client Protocol:</span>
                    <span className="text-slate-300 font-mono">guacamole-common-js v1.5.0</span>
                  </div>
                </div>
              </div>

              {/* VMware vCenter Status */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center space-x-2">
                    <Cloud className="w-5 h-5 text-sky-400" />
                    <h3 className="font-semibold text-white">VMware vCenter Integration</h3>
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-medium ${
                      overview.vmware.configured
                        ? "bg-sky-950 text-sky-300 border border-sky-800"
                        : "bg-slate-800 text-slate-400"
                    }`}
                  >
                    {overview.vmware.configured ? overview.vmware.status : "Not Configured"}
                  </span>
                </div>
                <div className="space-y-2 text-xs text-slate-400">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Host:</span>
                    <span className="font-mono text-slate-300">{overview.vmware.host || "None configured"}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Last Inventory Sync:</span>
                    <span className="text-slate-300">{formatDateTime(overview.vmware.last_sync)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">pyVmomi Engine:</span>
                    <span className="text-slate-300 font-semibold">Active</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Recent Audit Activity */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <h3 className="font-semibold text-white mb-4 flex items-center space-x-2">
                <ScrollText className="w-4 h-4 text-emerald-400" />
                <span>Recent System Activity</span>
              </h3>
              {overview.recent_logs.length === 0 ? (
                <p className="text-xs text-slate-500">No activity recorded yet.</p>
              ) : (
                <div className="space-y-2">
                  {overview.recent_logs.map((log) => (
                    <div
                      key={log.id}
                      className="flex items-center justify-between py-2 border-b border-slate-800/60 text-xs"
                    >
                      <div className="flex items-center space-x-3">
                        <span className="font-mono text-emerald-400 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                          {log.action}
                        </span>
                        <span className="text-slate-300">{log.detail || log.user_email}</span>
                      </div>
                      <span className="text-slate-500">{formatDateTime(log.at)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* =========================================================================
            TAB: ASSIGNMENTS (ADMIN ONLY)
        ========================================================================= */}
        {activeTab === "assignments" && currentUser.role === "admin" && (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-semibold text-white">VM User Assignments</h2>
                <p className="text-xs text-slate-400">
                  Standard users can ONLY see and access VMs that are explicitly assigned to them.
                </p>
              </div>
            </div>

            {assignments.length === 0 ? (
              <div className="py-12 text-center">
                <Link2 className="w-10 h-10 text-slate-600 mx-auto mb-3" />
                <p className="text-sm text-slate-300 font-medium">No active assignments yet.</p>
                <p className="text-xs text-slate-500 mt-1">Assign virtual machines to users to grant browser access.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="bg-slate-950 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
                    <tr>
                      <th className="py-3 px-4">User</th>
                      <th className="py-3 px-4">Virtual Machine</th>
                      <th className="py-3 px-4">Power</th>
                      <th className="py-3 px-4">Remote Protocol</th>
                      <th className="py-3 px-4">Assigned At</th>
                      <th className="py-3 px-4 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {assignments.map((asg) => (
                      <tr key={asg.id} className="hover:bg-slate-800/30">
                        <td className="py-3 px-4">
                          <div className="font-semibold text-white">{asg.user_name}</div>
                          <div className="text-slate-500">{asg.user_email}</div>
                        </td>
                        <td className="py-3 px-4 font-medium text-slate-200">{asg.vm_name}</td>
                        <td className="py-3 px-4">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                              asg.vm_power_state === "on" ? "text-emerald-400 bg-emerald-950" : "text-slate-400 bg-slate-800"
                            }`}
                          >
                            {asg.vm_power_state}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <span className="font-mono text-slate-300">{asg.vm_remote_protocol?.toUpperCase() || "None"}</span>
                        </td>
                        <td className="py-3 px-4 text-slate-400">{formatDateTime(asg.created_at)}</td>
                        <td className="py-3 px-4 text-right">
                          <button
                            onClick={async () => {
                              try {
                                await api(`/admin/assignments/${asg.id}`, "DELETE");
                                showBanner("Assignment revoked.");
                                refreshData();
                              } catch (err: any) {
                                showBanner(err.message, "error");
                              }
                            }}
                            className="px-2.5 py-1 rounded bg-rose-950/80 hover:bg-rose-900 text-rose-300 border border-rose-800 transition"
                          >
                            Revoke
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* =========================================================================
            TAB: USERS (ADMIN ONLY)
        ========================================================================= */}
        {activeTab === "users" && currentUser.role === "admin" && (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-semibold text-white">User Accounts</h2>
                <p className="text-xs text-slate-400">Manage administrator and standard user privileges.</p>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-950 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
                  <tr>
                    <th className="py-3 px-4">Name</th>
                    <th className="py-3 px-4">Email</th>
                    <th className="py-3 px-4">Role</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Last Login</th>
                    <th className="py-3 px-4">Created</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {usersList.map((u) => (
                    <tr key={u.id} className="hover:bg-slate-800/30">
                      <td className="py-3 px-4 font-semibold text-white">{u.full_name}</td>
                      <td className="py-3 px-4 font-mono text-slate-300">{u.email}</td>
                      <td className="py-3 px-4">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                            u.role === "admin"
                              ? "bg-purple-950 text-purple-300 border border-purple-800"
                              : "bg-slate-800 text-slate-300"
                          }`}
                        >
                          {u.role}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                            u.is_active ? "text-emerald-400 bg-emerald-950" : "text-slate-500 bg-slate-800"
                          }`}
                        >
                          {u.is_active ? "Active" : "Disabled"}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-400">{formatDateTime(u.last_login)}</td>
                      <td className="py-3 px-4 text-slate-400">{formatDate(u.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* =========================================================================
            TAB: REMOTE SESSIONS (ADMIN ONLY)
        ========================================================================= */}
        {activeTab === "sessions" && currentUser.role === "admin" && (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6">
            <div>
              <h2 className="text-base font-semibold text-white">Apache Guacamole Remote Session Logs</h2>
              <p className="text-xs text-slate-400">
                Audited connection history and durations for browser-based remote desktop sessions.
              </p>
            </div>

            {remoteSessions.length === 0 ? (
              <div className="py-12 text-center text-slate-500 text-xs">
                No remote sessions logged yet.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="bg-slate-950 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
                    <tr>
                      <th className="py-3 px-4">User</th>
                      <th className="py-3 px-4">Virtual Machine</th>
                      <th className="py-3 px-4">Protocol</th>
                      <th className="py-3 px-4">Client IP</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-4">Duration</th>
                      <th className="py-3 px-4">Started At</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {remoteSessions.map((s) => (
                      <tr key={s.id} className="hover:bg-slate-800/30">
                        <td className="py-3 px-4 font-semibold text-white">{s.user_email}</td>
                        <td className="py-3 px-4 font-medium text-slate-200">{s.vm_name}</td>
                        <td className="py-3 px-4 font-mono uppercase text-emerald-400">{s.protocol}</td>
                        <td className="py-3 px-4 font-mono text-slate-400">{s.client_ip}</td>
                        <td className="py-3 px-4">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                              s.status === "connected"
                                ? "text-emerald-400 bg-emerald-950"
                                : s.status === "failed"
                                ? "text-rose-400 bg-rose-950"
                                : "text-slate-400 bg-slate-800"
                            }`}
                          >
                            {s.status}
                          </span>
                        </td>
                        <td className="py-3 px-4 font-mono">{s.duration_seconds}s</td>
                        <td className="py-3 px-4 text-slate-400">{formatDateTime(s.started_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* =========================================================================
            TAB: AUDIT LOGS (ADMIN ONLY)
        ========================================================================= */}
        {activeTab === "audit" && currentUser.role === "admin" && (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6">
            <div>
              <h2 className="text-base font-semibold text-white">System Audit Trail</h2>
              <p className="text-xs text-slate-400">Immutable server-side record of authentication and actions.</p>
            </div>

            {auditLogs.length === 0 ? (
              <div className="py-12 text-center text-slate-500 text-xs">
                No audit events recorded yet.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="bg-slate-950 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
                    <tr>
                      <th className="py-3 px-4">Timestamp</th>
                      <th className="py-3 px-4">User</th>
                      <th className="py-3 px-4">Action</th>
                      <th className="py-3 px-4">Detail</th>
                      <th className="py-3 px-4">IP Address</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono">
                    {auditLogs.map((log) => (
                      <tr key={log.id} className="hover:bg-slate-800/30">
                        <td className="py-2.5 px-4 text-slate-400">{formatDateTime(log.at)}</td>
                        <td className="py-2.5 px-4 text-slate-200">{log.user_email}</td>
                        <td className="py-2.5 px-4 text-emerald-400 font-semibold">{log.action}</td>
                        <td className="py-2.5 px-4 text-slate-300 font-sans">{log.detail}</td>
                        <td className="py-2.5 px-4 text-slate-500">{log.ip || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* =========================================================================
            TAB: SUPPORT TICKETS
        ========================================================================= */}
        {activeTab === "support" && (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6">
            <div>
              <h2 className="text-base font-semibold text-white">Enterprise Support Center</h2>
              <p className="text-xs text-slate-400">
                Submit help requests or communicate with system administrators regarding your virtual machines.
              </p>
            </div>

            {tickets.length === 0 ? (
              <div className="py-12 text-center text-slate-500 text-xs">
                No support tickets submitted yet.
              </div>
            ) : (
              <div className="space-y-3">
                {tickets.map((t) => (
                  <div key={t.id} className="p-4 rounded-lg bg-slate-950 border border-slate-800 flex justify-between items-center">
                    <div>
                      <h4 className="font-semibold text-sm text-slate-200">{t.subject}</h4>
                      <p className="text-xs text-slate-500 mt-0.5">Submitted by {t.user_email} • {formatDateTime(t.created_at)}</p>
                    </div>
                    <span className="px-2.5 py-0.5 rounded text-xs font-semibold uppercase bg-emerald-950 text-emerald-300 border border-emerald-800">
                      {t.status}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* =========================================================================
          MODAL: ADMIN REMOTE ACCESS CONFIGURATION
      ========================================================================= */}
      {configModalVm && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center space-x-2">
                <Settings className="w-5 h-5 text-emerald-400" />
                <h3 className="font-bold text-base text-white">Configure Apache Guacamole Remote Access</h3>
              </div>
              <button
                onClick={() => setConfigModalVm(null)}
                className="text-slate-500 hover:text-slate-300"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="bg-slate-950 p-3 rounded-lg border border-slate-800/80 text-xs text-slate-400">
              Target VM: <strong className="text-slate-200">{configModalVm.name}</strong> ({configModalVm.guest_os})
            </div>

            {configModalMsg && (
              <div className="p-3 rounded-lg bg-rose-950/60 border border-rose-500/30 text-rose-300 text-xs flex items-center space-x-2">
                <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
                <span>{configModalMsg}</span>
              </div>
            )}

            <div className="space-y-4 text-xs">
              {/* Protocol selector */}
              <div>
                <label className="block font-medium text-slate-300 mb-1.5">Remote Protocol</label>
                <div className="grid grid-cols-3 gap-2">
                  {(["rdp", "ssh", "vnc"] as const).map((p) => (
                    <button
                      key={p}
                      type="button"
                      onClick={() => {
                        const defaultPort = p === "rdp" ? 3389 : p === "ssh" ? 22 : 5900;
                        setConfigForm({ ...configForm, protocol: p, port: defaultPort });
                      }}
                      className={`py-2 px-3 rounded-lg border font-semibold uppercase text-xs transition ${
                        configForm.protocol === p
                          ? "bg-emerald-600/20 border-emerald-500 text-emerald-300"
                          : "bg-slate-950 border-slate-800 text-slate-400 hover:text-white"
                      }`}
                    >
                      {p}
                    </button>
                  ))}
                </div>
              </div>

              {/* Host and Port */}
              <div className="grid grid-cols-3 gap-3">
                <div className="col-span-2">
                  <label className="block font-medium text-slate-300 mb-1">Target Host or IP</label>
                  <input
                    type="text"
                    required
                    value={configForm.host || ""}
                    onChange={(e) => setConfigForm({ ...configForm, host: e.target.value })}
                    placeholder="192.168.1.50"
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-white font-mono focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <div>
                  <label className="block font-medium text-slate-300 mb-1">Port</label>
                  <input
                    type="number"
                    required
                    value={configForm.port || 3389}
                    onChange={(e) => setConfigForm({ ...configForm, port: Number(e.target.value) })}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-white font-mono focus:outline-none focus:border-emerald-500"
                  />
                </div>
              </div>

              {/* Username & Domain (for RDP) */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-medium text-slate-300 mb-1">Username</label>
                  <input
                    type="text"
                    value={configForm.username || ""}
                    onChange={(e) => setConfigForm({ ...configForm, username: e.target.value })}
                    placeholder="Administrator / user"
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-emerald-500"
                  />
                </div>
                {configForm.protocol === "rdp" && (
                  <div>
                    <label className="block font-medium text-slate-300 mb-1">Windows Domain</label>
                    <input
                      type="text"
                      value={configForm.domain || ""}
                      onChange={(e) => setConfigForm({ ...configForm, domain: e.target.value })}
                      placeholder="Optional domain / WORKGROUP"
                      className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-emerald-500"
                    />
                  </div>
                )}
              </div>

              {/* Password */}
              <div>
                <label className="block font-medium text-slate-300 mb-1">
                  Password {configForm.has_password && <span className="text-emerald-400 font-normal">(Encrypted password currently saved)</span>}
                </label>
                <input
                  type="password"
                  value={configPassword}
                  onChange={(e) => setConfigPassword(e.target.value)}
                  placeholder={configForm.has_password ? "Leave blank to keep existing password" : "Enter remote machine password"}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-emerald-500"
                />
              </div>

              {/* SSH Private Key (for SSH) */}
              {configForm.protocol === "ssh" && (
                <div>
                  <label className="block font-medium text-slate-300 mb-1">
                    SSH Private Key (Optional for Key Auth)
                  </label>
                  <textarea
                    rows={3}
                    value={configPrivateKey}
                    onChange={(e) => setConfigPrivateKey(e.target.value)}
                    placeholder="-----BEGIN OPENSSH PRIVATE KEY-----"
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-white font-mono text-xs focus:outline-none focus:border-emerald-500"
                  />
                </div>
              )}

              {/* Ignore Cert checkbox */}
              <div className="flex items-center space-x-2 pt-1">
                <input
                  type="checkbox"
                  id="ignore_cert"
                  checked={configForm.ignore_cert ?? true}
                  onChange={(e) => setConfigForm({ ...configForm, ignore_cert: e.target.checked })}
                  className="rounded bg-slate-950 border-slate-700 text-emerald-500 focus:ring-emerald-500"
                />
                <label htmlFor="ignore_cert" className="text-slate-400 text-xs">
                  Ignore self-signed SSL/TLS certificates (Recommended for internal VMs)
                </label>
              </div>
            </div>

            <div className="pt-3 border-t border-slate-800 flex justify-end space-x-3">
              <button
                type="button"
                onClick={() => setConfigModalVm(null)}
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={saveRemoteConfig}
                disabled={configSaveLoading}
                className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition flex items-center space-x-2 disabled:opacity-50"
              >
                {configSaveLoading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                <span>Save Configuration</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* =========================================================================
          INTERACTIVE APACHE GUACAMOLE SESSION OVERLAY
      ========================================================================= */}
      {activeGuacVm && (
        <GuacamoleSession
          vm={activeGuacVm}
          onClose={() => {
            setActiveGuacVm(null);
            refreshData();
          }}
        />
      )}
    </div>
  );
}
