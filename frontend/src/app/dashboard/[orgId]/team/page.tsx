"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Navbar } from "@/components/navbar";
import { useAuth } from "@/components/auth-provider";
import { useTranslation } from "@/components/locale-provider";
import { apiFetch, type OrganizationMember } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const ROLES = ["viewer", "developer", "security_analyst", "admin"] as const;

export default function TeamPage() {
  const params = useParams<{ orgId: string }>();
  const orgId = params.orgId;
  const { getAccessToken } = useAuth();
  const { t, formatApiError } = useTranslation();
  const [members, setMembers] = useState<OrganizationMember[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const roleLabel = (role: string) => {
    const map: Record<string, string> = {
      owner: t("team.roleOwner"),
      admin: t("team.roleAdmin"),
      security_analyst: t("team.roleSecurityAnalyst"),
      developer: t("team.roleDeveloper"),
      viewer: t("team.roleViewer"),
    };
    return map[role] ?? role;
  };

  const load = useCallback(async () => {
    try {
      const data = await apiFetch<OrganizationMember[]>(
        `/api/v1/organizations/${orgId}/members`,
        { token: getAccessToken() }
      );
      setMembers(data);
    } catch (err) {
      setError(formatApiError(err));
    }
  }, [formatApiError, getAccessToken, orgId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function invite(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    const form = new FormData(e.currentTarget);
    try {
      await apiFetch(`/api/v1/organizations/${orgId}/members/invite`, {
        method: "POST",
        token: getAccessToken(),
        body: JSON.stringify({
          email: form.get("email"),
          role: form.get("role") || "viewer",
        }),
      });
      e.currentTarget.reset();
      setMessage(t("team.inviteSuccess"));
      await load();
    } catch (err) {
      setError(formatApiError(err));
    }
  }

  return (
    <>
      <Navbar />
      <main className="container mx-auto max-w-3xl space-y-6 px-4 py-8">
        <div>
          <Link href={`/dashboard/${orgId}`} className="text-sm text-muted-foreground hover:underline">
            ← {t("common.back")}
          </Link>
          <h1 className="mt-2 text-3xl font-bold">{t("team.title")}</h1>
          <p className="text-muted-foreground">{t("team.desc")}</p>
        </div>
        {error && <p className="text-destructive">{error}</p>}
        {message && <p className="text-green-400">{message}</p>}

        <Card>
          <CardHeader>
            <CardTitle>{t("team.invite")}</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={invite} className="flex flex-wrap gap-3">
              <div className="min-w-[200px] flex-1 space-y-2">
                <Label htmlFor="email">{t("team.email")}</Label>
                <Input id="email" name="email" type="email" required />
              </div>
              <div className="space-y-2">
                <Label htmlFor="role">{t("team.role")}</Label>
                <select
                  id="role"
                  name="role"
                  className="flex h-10 rounded-md border border-input bg-background px-3 text-sm"
                  defaultValue="viewer"
                >
                  {ROLES.map((role) => (
                    <option key={role} value={role}>
                      {roleLabel(role)}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex items-end">
                <Button type="submit">{t("team.inviteBtn")}</Button>
              </div>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("team.members")}</CardTitle>
            <CardDescription>{members.length} {t("team.members").toLowerCase()}</CardDescription>
          </CardHeader>
          <CardContent>
            {members.length === 0 ? (
              <p className="text-muted-foreground">{t("team.noMembers")}</p>
            ) : (
              <ul className="space-y-3 text-sm">
                {members.map((member) => (
                  <li key={member.id} className="flex flex-wrap justify-between gap-2 border-b border-border/40 pb-2">
                    <div>
                      <p className="font-medium">{member.full_name ?? member.email ?? member.user_id}</p>
                      <p className="text-muted-foreground">{member.email}</p>
                    </div>
                    <div className="text-right text-muted-foreground">
                      <p>{roleLabel(member.role)}</p>
                      <p>{t("team.joined")}: {new Date(member.joined_at).toLocaleDateString()}</p>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </main>
    </>
  );
}
