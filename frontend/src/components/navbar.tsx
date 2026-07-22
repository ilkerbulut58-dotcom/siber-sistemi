"use client";

import Link from "next/link";
import { Shield } from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { DashboardNavLinks } from "@/components/dashboard-nav-links";
import { Button } from "@/components/ui/button";

export function Navbar() {
  const { user, logout } = useAuth();

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
            <span className="hidden max-w-[160px] truncate text-sm text-muted-foreground lg:inline">
              {user.email}
            </span>
            <Button variant="outline" size="sm" onClick={() => logout()}>
              Çıkış
            </Button>
          </div>
        ) : (
          <nav className="flex items-center gap-2">
            <Link href="/login">
              <Button variant="outline" size="sm">
                Giriş
              </Button>
            </Link>
            <Link href="/register">
              <Button size="sm">Kayıt Ol</Button>
            </Link>
          </nav>
        )}
      </div>
    </header>
  );
}
