import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import PlatformQualityPage from "@/app/dashboard/platform/quality/page";
import { LocaleProvider } from "@/components/locale-provider";

const mockUseAuth = vi.fn();

vi.mock("@/components/auth-provider", () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock("@/components/navbar", () => ({ Navbar: () => <div>Navbar</div> }));

vi.mock("@/lib/api-client", () => ({
  apiFetch: vi.fn(),
}));

function renderPage() {
  return render(
    <LocaleProvider>
      <PlatformQualityPage />
    </LocaleProvider>
  );
}

describe("PlatformQualityPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows unauthorized message for non-admin users", () => {
    mockUseAuth.mockReturnValue({ user: { is_platform_admin: false }, getAccessToken: () => "token" });
    renderPage();
    expect(screen.getByText(/yalnız platform yöneticilerine açıktır/i)).toBeInTheDocument();
  });

  it("shows loading state for platform admin before data arrives", () => {
    mockUseAuth.mockReturnValue({ user: { is_platform_admin: true }, getAccessToken: () => "token" });
    renderPage();
    expect(screen.getByText(/Kalite verileri yükleniyor/i)).toBeInTheDocument();
  });
});
