"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Navbar } from "@/components/navbar";
import { useAuth } from "@/components/auth-provider";
import { useTranslation } from "@/components/locale-provider";
import {
  apiFetch,
  type Domain,
  type MonitoringEvent,
  type Project,
  type ScanSchedule,
} from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function MonitoringPage() {
  const params = useParams<{ orgId: string }>();
  const orgId = params.orgId;
  const { getAccessToken } = useAuth();
  const { t, formatApiError, scanProfileLabel } = useTranslation();
  const [schedules, setSchedules] = useState<ScanSchedule[]>([]);
  const [events, setEvents] = useState<MonitoringEvent[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [domains, setDomains] = useState<Domain[]>([]);
  const [selectedProject, setSelectedProject] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [scheduleData, eventData, projectData] = await Promise.all([
        apiFetch<ScanSchedule[]>(`/api/v1/organizations/${orgId}/monitoring/schedules`, {
          token: getAccessToken(),
        }),
        apiFetch<MonitoringEvent[]>(`/api/v1/organizations/${orgId}/monitoring/events`, {
          token: getAccessToken(),
        }),
        apiFetch<Project[]>(`/api/v1/organizations/${orgId}/projects`, { token: getAccessToken() }),
      ]);
      setSchedules(scheduleData);
      setEvents(eventData.slice(0, 20));
      setProjects(projectData);
      if (projectData[0] && !selectedProject) setSelectedProject(projectData[0].id);
    } catch (err) {
      setError(formatApiError(err));
    }
  }, [formatApiError, getAccessToken, orgId, selectedProject]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!selectedProject) {
      setDomains([]);
      return;
    }
    void apiFetch<Domain[]>(
      `/api/v1/organizations/${orgId}/projects/${selectedProject}/domains`,
      { token: getAccessToken() }
    ).then(setDomains).catch(() => setDomains([]));
  }, [getAccessToken, orgId, selectedProject]);

  async function createSchedule(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    const form = new FormData(e.currentTarget);
    try {
      await apiFetch(`/api/v1/organizations/${orgId}/monitoring/schedules`, {
        method: "POST",
        token: getAccessToken(),
        body: JSON.stringify({
          project_id: form.get("project_id"),
          domain_id: form.get("domain_id"),
          name: form.get("name"),
          target_url: form.get("target_url"),
          scan_profile: form.get("scan_profile") || "safe",
          interval_hours: Number(form.get("interval_hours") || 24),
          enabled: true,
        }),
      });
      e.currentTarget.reset();
      setMessage(t("monitoring.createSuccess"));
      await load();
    } catch (err) {
      setError(formatApiError(err));
    }
  }

  return (
    <>
      <Navbar />
      <main className="container mx-auto max-w-4xl space-y-6 px-4 py-8">
        <div>
          <Link href={`/dashboard/${orgId}`} className="text-sm text-muted-foreground hover:underline">
            ← {t("common.back")}
          </Link>
          <h1 className="mt-2 text-3xl font-bold">{t("monitoring.title")}</h1>
          <p className="text-muted-foreground">{t("monitoring.desc")}</p>
        </div>
        {error && <p className="text-destructive">{error}</p>}
        {message && <p className="text-green-400">{message}</p>}

        <Card>
          <CardHeader>
            <CardTitle>{t("monitoring.createSchedule")}</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={createSchedule} className="grid gap-3 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="name">{t("monitoring.name")}</Label>
                <Input id="name" name="name" required />
              </div>
              <div className="space-y-2">
                <Label htmlFor="target_url">{t("monitoring.targetUrl")}</Label>
                <Input id="target_url" name="target_url" type="url" required />
              </div>
              <div className="space-y-2">
                <Label htmlFor="project_id">{t("monitoring.selectProject")}</Label>
                <select
                  id="project_id"
                  name="project_id"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                  value={selectedProject}
                  onChange={(e) => setSelectedProject(e.target.value)}
                  required
                >
                  <option value="" disabled>{t("common.selectEllipsis")}</option>
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="domain_id">{t("monitoring.selectDomain")}</Label>
                <select
                  id="domain_id"
                  name="domain_id"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                  required
                >
                  <option value="" disabled>{t("common.selectEllipsis")}</option>
                  {domains.filter((d) => d.is_verified).map((d) => (
                    <option key={d.id} value={d.id}>{d.hostname}</option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="scan_profile">{t("scanPage.scanProfile")}</Label>
                <select
                  id="scan_profile"
                  name="scan_profile"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                  defaultValue="safe"
                >
                  <option value="safe">{scanProfileLabel("safe")}</option>
                  <option value="deep">{scanProfileLabel("deep")}</option>
                </select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="interval_hours">{t("monitoring.intervalHours")}</Label>
                <Input id="interval_hours" name="interval_hours" type="number" min={1} max={168} defaultValue={24} />
              </div>
              <div className="md:col-span-2">
                <Button type="submit">{t("monitoring.createBtn")}</Button>
              </div>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("monitoring.schedules")}</CardTitle>
          </CardHeader>
          <CardContent>
            {schedules.length === 0 ? (
              <p className="text-muted-foreground">{t("monitoring.noSchedules")}</p>
            ) : (
              <ul className="space-y-3 text-sm">
                {schedules.map((s) => (
                  <li key={s.id} className="rounded-md border border-border/50 p-3">
                    <p className="font-medium">{s.name}</p>
                    <p className="text-muted-foreground">{s.target_url} · {scanProfileLabel(s.scan_profile)}</p>
                    <p className="text-xs text-muted-foreground">
                      {t("monitoring.lastRun")}: {s.last_run_at ? new Date(s.last_run_at).toLocaleString() : "—"} ·{" "}
                      {t("monitoring.nextRun")}: {s.next_run_at ? new Date(s.next_run_at).toLocaleString() : "—"}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("monitoring.events")}</CardTitle>
          </CardHeader>
          <CardContent>
            {events.length === 0 ? (
              <p className="text-muted-foreground">{t("monitoring.noEvents")}</p>
            ) : (
              <ul className="space-y-2 text-sm">
                {events.map((ev) => (
                  <li key={ev.id} className="flex justify-between border-b border-border/40 pb-2">
                    <span>{ev.event_type}</span>
                    <span className="text-muted-foreground">{new Date(ev.created_at).toLocaleString()}</span>
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
