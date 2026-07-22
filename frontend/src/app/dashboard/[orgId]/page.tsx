"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Navbar } from "@/components/navbar";
import { useAuth } from "@/components/auth-provider";
import { apiFetch, type Organization, type Project } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function OrgDashboardPage() {
  const params = useParams<{ orgId: string }>();
  const orgId = params.orgId;
  const { getAccessToken } = useAuth();
  const [org, setOrg] = useState<Organization | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [orgData, projectData] = await Promise.all([
        apiFetch<Organization>(`/api/v1/organizations/${orgId}`, { token: getAccessToken() }),
        apiFetch<Project[]>(`/api/v1/organizations/${orgId}/projects`, {
          token: getAccessToken(),
        }),
      ]);
      setOrg(orgData);
      setProjects(projectData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Veri yüklenemedi");
    }
  }, [getAccessToken, orgId]);

  useEffect(() => {
    load();
  }, [load]);

  async function createProject(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const formEl = e.currentTarget;
    const form = new FormData(formEl);
    setError(null);
    try {
      await apiFetch<Project>(`/api/v1/organizations/${orgId}/projects`, {
        method: "POST",
        token: getAccessToken(),
        body: JSON.stringify({
          name: form.get("name"),
          description: form.get("description") || null,
          environment: form.get("environment") || "production",
        }),
      });
      formEl.reset();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Proje oluşturulamadı");
    }
  }

  return (
    <>
      <Navbar />
      <main className="container mx-auto px-4 py-8">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <div>
            <Link href="/dashboard" className="text-sm text-muted-foreground hover:underline">
              ← Organizasyonlar
            </Link>
            <h1 className="mt-2 text-3xl font-bold">{org?.name || "Organizasyon"}</h1>
          </div>
          <Link
            href={`/dashboard/${orgId}/mobile`}
            className="rounded-md border border-indigo-500/40 bg-indigo-500/10 px-4 py-2 text-sm font-medium hover:bg-indigo-500/20"
          >
            Mobil Güvenlik →
          </Link>
        </div>
        {error && <p className="mb-4 text-destructive">{error}</p>}

        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Yeni Proje</CardTitle>
              <CardDescription>Domain ve taramalar proje bazında yönetilir</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={createProject} className="space-y-3">
                <div className="space-y-2">
                  <Label htmlFor="name">Proje adı</Label>
                  <Input id="name" name="name" required />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="environment">Ortam</Label>
                  <select
                    id="environment"
                    name="environment"
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                    defaultValue="production"
                  >
                    <option value="production">Production</option>
                    <option value="staging">Staging</option>
                    <option value="development">Development</option>
                  </select>
                </div>
                <Button type="submit">Proje Oluştur</Button>
              </form>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Projeler</CardTitle>
            </CardHeader>
            <CardContent>
              {projects.length === 0 ? (
                <p className="text-muted-foreground">Henüz proje yok.</p>
              ) : (
                <ul className="space-y-2">
                  {projects.map((project) => (
                    <li key={project.id}>
                      <Link
                        href={`/dashboard/${orgId}/projects/${project.id}`}
                        className="block rounded-md border border-border px-4 py-3 hover:bg-muted/40"
                      >
                        <div className="font-medium">{project.name}</div>
                        <div className="text-sm text-muted-foreground">{project.environment}</div>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>
      </main>
    </>
  );
}
