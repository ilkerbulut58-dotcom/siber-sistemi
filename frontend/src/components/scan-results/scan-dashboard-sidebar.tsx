"use client";

import Link from "next/link";
import {
  Activity,
  BarChart3,
  FileText,
  Globe,
  LayoutDashboard,
  Lock,
  Radar,
  Server,
  Settings,
  Shield,
  Users,
} from "lucide-react";
import { useTranslation } from "@/components/locale-provider";
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
  const { t } = useTranslation();

  const scanItems: NavItem[] = [
    { id: "overview", label: t("scanResults.overview"), icon: LayoutDashboard },
    { id: "findings", label: t("scanResults.findings"), icon: Shield },
    { id: "all-findings", label: t("scanResults.allFindings"), icon: BarChart3 },
    { id: "site-profile", label: t("scanResults.siteProfile"), icon: Globe },
    { id: "headers", label: t("scanResults.headers"), icon: Lock },
    { id: "reports", label: t("scanResults.reports"), icon: FileText },
  ];

  const platformItems: NavItem[] = [
    {
      id: "monitoring",
      label: t("scanResults.monitoring"),
      icon: Activity,
      href: `/dashboard/${orgId}/monitoring`,
    },
    {
      id: "assets",
      label: t("scanResults.assets"),
      icon: Radar,
      href: projectId ? `/dashboard/${orgId}/projects/${projectId}/attack-surface` : undefined,
      disabled: !projectId,
    },
    {
      id: "projects",
      label: t("scanResults.projects"),
      icon: Server,
      href: `/dashboard/${orgId}`,
    },
    { id: "team", label: t("scanResults.team"), icon: Users, href: `/dashboard/${orgId}/team` },
    { id: "settings", label: t("scanResults.settings"), icon: Settings, href: "/dashboard/settings" },
  ];

  const renderItem = (item: NavItem) => {
    const Icon = item.icon;
    const isActive = item.id === active;
    const baseClass = cn(
      "flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors",
      isActive
        ? "bg-primary/15 font-medium text-primary"
        : "text-muted-foreground hover:bg-muted/40 hover:text-foreground",
      item.disabled && "pointer-events-none opacity-40"
    );

    if (item.href && !item.disabled) {
      return (
        <Link key={item.id} href={item.href} className={baseClass}>
          <Icon className="h-4 w-4 shrink-0" />
          {item.label}
        </Link>
      );
    }

    if (item.id in { overview: 1, findings: 1, "all-findings": 1, "site-profile": 1, headers: 1, reports: 1 }) {
      return (
        <button
          key={item.id}
          type="button"
          className={baseClass}
          onClick={() => onNavigate(item.id as ScanSection)}
        >
          <Icon className="h-4 w-4 shrink-0" />
          {item.label}
        </button>
      );
    }

    return (
      <span key={item.id} className={baseClass}>
        <Icon className="h-4 w-4 shrink-0" />
        {item.label}
      </span>
    );
  };

  return (
    <aside className="space-y-6">
      <div>
        <p className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {t("scanResults.scanNav")}
        </p>
        <nav className="space-y-1">{scanItems.map(renderItem)}</nav>
      </div>
      <div>
        <p className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {t("scanResults.platformNav")}
        </p>
        <nav className="space-y-1">{platformItems.map(renderItem)}</nav>
      </div>
    </aside>
  );
}
