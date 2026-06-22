import React from "react";
import {
  AlertTriangle,
  Archive,
  BookOpen,
  Clock,
  Copy,
  Cpu,
  Database,
  Download,
  FileSearch,
  FileText,
  Fingerprint,
  FolderX,
  Gamepad2,
  Gauge,
  GitBranch,
  HardDrive,
  HelpCircle,
  History,
  Hourglass,
  Lock,
  LogOut,
  MessageCircle,
  Play,
  Plus,
  Printer,
  RefreshCw,
  Save,
  Search,
  Shield,
  ShieldCheck,
  Target,
  Terminal,
  Trash2,
  Users,
  X,
} from "lucide-react";

const ICON_MAP = {
  history: History,
  document_search: FileSearch,
  speed: Gauge,
  warning: AlertTriangle,
  schedule: Clock,
  sports_esports: Gamepad2,
  forum: MessageCircle,
  shield: Shield,
  terminal: Terminal,
  memory: Cpu,
  delete: Trash2,
  search: Search,
  play_arrow: Play,
  folder_off: FolderX,
  sd_card: HardDrive,
  fingerprint: Fingerprint,
  inventory_2: Archive,
  account_tree: GitBranch,
  add: Plus,
  close: X,
  download: Download,
  print: Printer,
  menu_book: BookOpen,
  description: FileText,
  hourglass_top: Hourglass,
  content_copy: Copy,
  admin_panel_settings: ShieldCheck,
  refresh: RefreshCw,
  logout: LogOut,
  save: Save,
  delete_sweep: Trash2,
  database: Database,
  group: Users,
  lock: Lock,
  track_changes: Target,
  groups: Users,
  delete_forever: Trash2,
  help: HelpCircle,
};

export function MaterialIcon({ name, size = 20, className = "", filled = false }) {
  const Icon = ICON_MAP[name];
  if (!Icon) {
    return (
      <span className={`ws-icon-fallback ${className}`.trim()} style={{ fontSize: size }} aria-hidden="true">
        •
      </span>
    );
  }
  return (
    <Icon
      size={size}
      className={className}
      strokeWidth={filled ? 2.25 : 1.75}
      aria-hidden="true"
    />
  );
}

export function renderIcon(icon, size = 20, className = "") {
  if (!icon) return null;
  if (typeof icon === "string") {
    return <MaterialIcon name={icon} size={size} className={className} />;
  }
  const Icon = icon;
  return <Icon size={size} className={className} strokeWidth={1.75} />;
}
