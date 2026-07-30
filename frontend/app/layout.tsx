import type { Metadata } from "next";
import "../styles/globals.css";

export const metadata: Metadata = {
  title: "RAGaaS",
  description: "Retrieval-Augmented Generation as a Service",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
