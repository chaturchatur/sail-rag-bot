"use client";

import { MantineProvider } from "@mantine/core";
import "@mantine/core/styles.css";
// import { appTheme } from "@/styles/theme";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <MantineProvider /* theme={appTheme} */ defaultColorScheme="light">
      {children}
    </MantineProvider>
  );
}
