import { ReactElement } from "react";
import { render, RenderOptions } from "@testing-library/react";
import { LocaleProvider } from "@/components/locale-provider";

export function renderWithLocale(ui: ReactElement, options?: Omit<RenderOptions, "wrapper">) {
  return render(ui, {
    wrapper: ({ children }) => <LocaleProvider>{children}</LocaleProvider>,
    ...options,
  });
}
