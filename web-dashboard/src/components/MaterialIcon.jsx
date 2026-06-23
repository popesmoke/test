import React from "react";
import {
  Activity,
  AlertTriangle,
  BookOpen,
  Box,
  Check,
  CheckCircle2,
  ChevronRight,
  Clock,
  Code2,
  Copy,
  Database,
  Download,
  FileText,
  Fingerprint,
  FolderOpen,
  GitBranch,
  Hash,
  HelpCircle,
  History,
  Hourglass,
  LayoutDashboard,
  ListChecks,
  Lock,
  LogOut,
  Play,
  Plus,
  Printer,
  RefreshCw,
  Save,
  Search,
  Shield,
  ShieldAlert,
  Target,
  Timer,
  Trash2,
  User,
  UserCircle,
  Users,
  X,
  Zap,
} from "lucide-react";

const ICONS = {
  history: History,
  document_search: Search,
  speed: Activity,
  warning: AlertTriangle,
  schedule: Clock,
  sports_esports: Play,
  forum: FileText,
  shield: Shield,
  terminal: Code2,
  memory: Database,
  delete: Trash2,
  search: Search,
  play_arrow: Play,
  folder_off: FolderOpen,
  sd_card: Database,
  fingerprint: Fingerprint,
  inventory_2: Box,
  account_tree: GitBranch,
  add: Plus,
  close: X,
  download: Download,
  print: Printer,
  menu_book: BookOpen,
  description: FileText,
  hourglass_top: Hourglass,
  content_copy: Copy,
  admin_panel_settings: User,
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
  radar: Activity,
  verified_user: Shield,
  timer: Timer,
  policy: Shield,
  dashboard: LayoutDashboard,
  bolt: Zap,
  registry: Database,
  timeline: History,
  hash: Hash,
  windows: LayoutDashboard,
  certificate: Shield,
  folder: FolderOpen,
  event_log: History,
  person: UserCircle,
  gpp_maybe: ShieldAlert,
  play: Play,
  list_checks: ListChecks,
  git_branch: GitBranch,
  file_code: Code2,
  file_down: Download,
  users: Users,
  shield_alert: ShieldAlert,
  alert_triangle: AlertTriangle,
  help_circle: HelpCircle,
  check_circle: CheckCircle2,
  chevron_right: ChevronRight,
};

export function MaterialIcon({ name, size = 20, className = "", filled = false }) {
  const Icon = ICONS[name];
  if (!Icon) {
    return (
      <span
        className={`icons8-icon icons8-icon--fallback ${className}`.trim()}
        style={{
          display: "inline-flex",
          width: size,
          height: size,
          alignItems: "center",
          justifyContent: "center",
          verticalAlign: "middle",
          flexShrink: 0,
          fontSize: Math.max(10, size - 6),
          fontWeight: 700,
          opacity: 0.55,
        }}
        aria-hidden="true"
      >
        ?
      </span>
    );
  }
  return (
    <Icon
      size={size}
      strokeWidth={filled ? 2.4 : 1.75}
      className={`icons8-icon ${className}`.trim()}
      aria-hidden="true"
      style={{ display: "inline-block", verticalAlign: "middle", flexShrink: 0 }}
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
