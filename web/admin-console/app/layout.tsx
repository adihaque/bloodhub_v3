import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = { title: "Blood Hub Admin", description: "Blood Hub operations console" };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
