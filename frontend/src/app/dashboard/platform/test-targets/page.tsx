"use client";

import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { useTranslation } from "@/components/locale-provider";

type PredefinedTarget = {
  id: string;
  hostname: string;
  display_name: string;
  default_scan_profile: string;
};

type Assignment = {
  id: string;
  user_id: string;
  organization_id: string;
  predefined_target_id: string;
  allowed_profiles: string[];
  starts_at: string;
  ends_at: string | null;
  revoked_at: string | null;
  target?: PredefinedTarget;
};

type Org = { id: string; name: string };
type Member = { user_id: string; email: string; role: string };

export default function PlatformTestTargetsPage() {
  const { t, locale } = useTranslation();
  const [targets, setTargets] = useState<PredefinedTarget[]>([]);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [orgs, setOrgs] = useState<Org[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [orgId, setOrgId] = useState("");
  const [userId, setUserId] = useState("");
  const [targetId, setTargetId] = useState("");
  const [endsAt, setEndsAt] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const [tRes, aRes, oRes] = await Promise.all([
      apiFetch<PredefinedTarget[]>("/api/v1/platform/predefined-scan-targets"),
      apiFetch<Assignment[]>("/api/v1/platform/scan-target-assignments"),
      apiFetch<Org[]>("/api/v1/platform/customer-organizations"),
    ]);
    setTargets(tRes);
    setAssignments(aRes);
    setOrgs(oRes);
  }, []);

  useEffect(() => {
    void load().catch((e) => setError(String(e)));
  }, [load]);

  useEffect(() => {
    if (!orgId) {
      setMembers([]);
      return;
    }
    void apiFetch<Member[]>(`/api/v1/platform/customer-organizations/${orgId}/members`)
      .then(setMembers)
      .catch((e) => setError(String(e)));
  }, [orgId]);

  const assign = async () => {
    setError(null);
    setMessage(null);
    try {
      await apiFetch("/api/v1/platform/scan-target-assignments", {
        method: "POST",
        body: JSON.stringify({
          predefined_target_id: targetId,
          user_id: userId,
          organization_id: orgId,
          allowed_profiles: ["safe"],
          ends_at: endsAt ? new Date(endsAt).toISOString() : null,
        }),
      });
      setMessage(locale === "de" ? "Zuweisung gespeichert." : "Atama kaydedildi.");
      await load();
    } catch (e) {
      setError(String(e));
    }
  };

  const revoke = async (id: string) => {
    await apiFetch(`/api/v1/platform/scan-target-assignments/${id}/revoke`, { method: "POST" });
    await load();
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <h1 className="text-2xl font-semibold">
        {t("platform.testTargetsTitle") || (locale === "de" ? "Vordefinierte Testziele" : "Hazır test hedefleri")}
      </h1>
      {message && <p className="text-sm text-green-700">{message}</p>}
      {error && <p className="text-sm text-destructive">{error}</p>}

      <Card>
        <CardHeader>
          <CardTitle>{locale === "de" ? "Ziele" : "Hedefler"}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {targets.map((row) => (
            <div key={row.id} className="flex justify-between border-b py-2">
              <span>{row.hostname}</span>
              <span className="text-muted-foreground">{row.default_scan_profile}</span>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{locale === "de" ? "Zuweisen" : "Kullanıcıya ata"}</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2">
          <div>
            <Label>{locale === "de" ? "Organisation" : "Organizasyon"}</Label>
            <select
              className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
              value={orgId}
              onChange={(e) => {
                setOrgId(e.target.value);
                setUserId("");
              }}
            >
              <option value="">—</option>
              {orgs.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label>{locale === "de" ? "Benutzer" : "Kullanıcı"}</Label>
            <select
              className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              disabled={!orgId}
            >
              <option value="">—</option>
              {members.map((m) => (
                <option key={m.user_id} value={m.user_id}>
                  {m.email} ({m.role})
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label>{locale === "de" ? "Ziel" : "Hedef"}</Label>
            <select
              className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
              value={targetId}
              onChange={(e) => setTargetId(e.target.value)}
            >
              <option value="">—</option>
              {targets.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.hostname}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label>{locale === "de" ? "Ende (optional)" : "Bitiş (isteğe bağlı)"}</Label>
            <input
              type="datetime-local"
              className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
              value={endsAt}
              onChange={(e) => setEndsAt(e.target.value)}
            />
          </div>
          <div className="sm:col-span-2">
            <Button type="button" onClick={() => void assign()} disabled={!targetId || !userId || !orgId}>
              {locale === "de" ? "Zuweisen" : "Ata"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{locale === "de" ? "Zuweisungen" : "Atamalar"}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {assignments.map((row) => (
            <div key={row.id} className="flex flex-wrap items-center justify-between gap-2 border-b py-2">
              <span>
                {row.target?.hostname || row.predefined_target_id} → {row.user_id.slice(0, 8)}…
                {row.revoked_at ? " (revoked)" : row.ends_at ? ` · ends ${row.ends_at.slice(0, 10)}` : ""}
              </span>
              {!row.revoked_at && (
                <Button type="button" variant="outline" size="sm" onClick={() => void revoke(row.id)}>
                  {locale === "de" ? "Widerrufen" : "İptal"}
                </Button>
              )}
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
