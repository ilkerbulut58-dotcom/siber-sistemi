"use client";

import Link from "next/link";
import {
  Activity,
  BarChart3,
  FileText,
  Globe,
  LayoutDashboard,
  Lock,
  Monitor,
  Radar,
  Server,
  Settings,
  Shield,
  Users,
} from "lucide-react";
import { cn } from "@/lib/utils";

export type ScanSection =
  | "overview"
  | "findings"
  | "all-findings"
  | "site-profile"
  | "headers"
  | "reports";

interface NavItem {
  id: ScanSection | string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  href?: string;
  disabled?: boolean;
}

interface Props {
  orgId: string;
  projectId?: string;
  active: ScanSection;
  onNavigate: (section: ScanSection) => void;
}

export function ScanDashboardSidebar({ orgId, projectId, active, onNavigate }: Props) {
  const scanItems: NavItem[] = [
    { id: "overview", label: "Özet", icon: LayoutDashboard },
    { id: "findings", label: "Bulgular", icon: Shield },
    { id: "all-findings", label: "Tüm Bulgular", icon: BarChart3 },
    { id: "site-profile", label: "Site Profili", icon: Globe },
    { id: "headers", label: "HTTP Başlıkları", icon: Lock },
    { id: "reports", label: "Raporlar", icon: FileText },
  ];

  const platformItems: NavItem[] = [
    {
      id: "monitoring",
      label: "İzleme",
      icon: Activity,
      href: projectId ? `/dashboard/${orgId}/projects/${projectId}` : undefined,
      disabled: !projectId,
    },
    {
      id: "assets",
      label: "Varlıklar (ASM)",
      icon: Radar,
      href: projectId ? `/dashboard/${orgId}/projects/${projectId}/attack-surface` : undefined,
      disabled: !projectId,
    },
    {
      id: "projects",
      label: "Projeler",
      icon: Server,
      href: `/dashboard/${orgId}`,
    },
    { id: "team", label: "Ekip", icon: Users, disabled: true },
    { id: "settings", label: "Ayarlar", icon: Settings, disabled: true },
  ];

  const renderItem = (item: NavItem) => {
    const Icon = item.icon;
    const isActive = item.id === active;

    if (item.href && !item.disabled) {
      return (
        <Link
          key={item.id}
          href={item.href}
          className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-secondary/80 hover:text-foreground"
        >
          <Icon className="h-4 w-4 shrink-0" />
          {item.label}
        </Link>
      );
    }

    return (
      <button
        key={item.id}
        type="button"
        disabled={item.disabled}
        onClick={() => !item.disabled && onNavigate(item.id as ScanSection)}
        className={cn(
          "flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm transition-colors",
          isActive
            ? "bg-indigo-500/15 font-medium text-indigo-200 ring-1 ring-indigo-500/30"
            : "text-muted-foreground hover:bg-secondary/80 hover:text-foreground",
          item.disabled && "cursor-not-allowed opacity-40"
        )}
      >
        <Icon className="h-4 w-4 shrink-0" />
        {item.label}
      </button>
    );
  };

  return (
    <aside className="hidden w-56 shrink-0 lg:block">
      <div className="sticky top-4 space-y-6 rounded-xl border border-border/60 bg-card/50 p-3 backdrop-blur-sm">
        <div>
          <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Tarama
          </p>
          <nav className="space-y-0.5">{scanItems.map(renderItem)}</nav>
        </div>
        <div>
          <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Platform
          </p>
          <nav className="space-y-0.5">{platformItems.map(renderItem)}</nav>
        </div>
        <div className="flex items-center gap-2 px-3 pt-2 text-xs text-muted-foreground">
          <Globe className="h-3.5 w-3.5" />
          <Monitor className="h-3.5 w-3.5" />
          SIBER Platform
        </div>
      </div>
    </aside>
  );
}
