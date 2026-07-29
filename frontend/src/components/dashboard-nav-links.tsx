"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { LucideIcon } from "lucide-react";
import {
  LayoutDashboard,
  Menu,
  ScanSearch,
  Settings,
} from "lucide-react";
import { useState } from "react";
import { useTranslation } from "@/components/locale-provider";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";

function NavLink({
  href,
  label,
  icon: Icon,
  onClick,
  highlight,
}: {
  href: string;
  label: string;
  icon: LucideIcon;
  onClick?: () => void;
  highlight?: boolean;
}) {
  const pathname = usePathname();
  const active =
    href === "/dashboard"
      ? pathname === "/dashboard"
      : pathname === href || pathname.startsWith(`${href}/`);

  return (
    <Link
      href={href}
      onClick={onClick}
      className={`flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors ${
        active
          ? "bg-primary/15 font-medium text-primary"
          : highlight
            ? "text-foreground hover:bg-primary/10 hover:text-primary"
            : "text-muted-foreground hover:bg-muted/40 hover:text-foreground"
      }`}
    >
      <Icon className="h-4 w-4 shrink-0" />
      {label}
    </Link>
  );
}

export function DashboardNavLinks({ mobile = false }: { mobile?: boolean }) {
  const [open, setOpen] = useState(false);
  const { t } = useTranslation();

  const navItems = [
    { href: "/dashboard", label: t("nav.overview"), icon: LayoutDashboard },
    { href: "/dashboard/scan", label: t("nav.scans"), icon: ScanSearch, highlight: true },
    { href: "/dashboard/settings", label: t("nav.settings"), icon: Settings },
  ] as const;

  if (mobile) {
    return (
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetTrigger asChild>
          <Button variant="outline" size="sm" className="md:hidden">
            <Menu className="h-4 w-4" />
            <span className="sr-only">{t("common.menu")}</span>
          </Button>
        </SheetTrigger>
        <SheetContent side="right" className="w-[280px] p-0">
          <SheetHeader className="border-b border-border px-4 py-4">
            <SheetTitle>{t("nav.menuTitle")}</SheetTitle>
          </SheetHeader>
          <nav className="flex flex-col gap-1 p-3">
            {navItems.map((item) => (
              <NavLink key={item.href} {...item} onClick={() => setOpen(false)} />
            ))}
          </nav>
        </SheetContent>
      </Sheet>
    );
  }

  return (
    <nav className="hidden items-center gap-1 md:flex">
      {navItems.map((item) => (
        <NavLink key={item.href} {...item} />
      ))}
    </nav>
  );
}
