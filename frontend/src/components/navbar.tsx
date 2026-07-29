"use client";

import Link from "next/link";
import { Shield } from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { DashboardNavLinks } from "@/components/dashboard-nav-links";
import { LanguageSwitcher } from "@/components/language-switcher";
import { useTranslation } from "@/components/locale-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { usePublicRegistrationEnabled } from "@/lib/system-info";

export function Navbar() {
  const { user, logout } = useAuth();
  const { t } = useTranslation();
  const registrationOpen = usePublicRegistrationEnabled();

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/95 backdrop-blur">
      <div className="container mx-auto flex h-16 items-center justify-between gap-3 px-4">
        <Link href={user ? "/dashboard" : "/"} className="flex shrink-0 items-center gap-2">
          <Shield className="h-6 w-6 text-primary" />
          <span className="text-xl font-bold">SIBER</span>
        </Link>

        {user ? (
          <div className="flex flex-1 items-center justify-end gap-2 md:gap-4">
            <DashboardNavLinks />
            <DashboardNavLinks mobile />
            <LanguageSwitcher />
            {user.is_platform_admin && (
              <Badge variant="secondary" className="hidden sm:inline-flex">
                {t("admin.badge")}
              </Badge>
            )}
            <span className="hidden max-w-[160px] truncate text-sm text-muted-foreground lg:inline">
              {user.email}
            </span>
            <Button variant="outline" size="sm" onClick={() => logout()}>
              {t("common.logout")}
            </Button>
          </div>
        ) : (
          <nav className="flex items-center gap-2">
            <LanguageSwitcher />
            <Link href="/login">
              <Button variant="outline" size="sm">
                {t("common.login")}
              </Button>
            </Link>
            {registrationOpen !== false && (
              <Link href="/register">
                <Button size="sm">{t("common.register")}</Button>
              </Link>
            )}
          </nav>
        )}
      </div>
    </header>
  );
}
