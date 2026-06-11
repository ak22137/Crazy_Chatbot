import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Excel Intelligence — Conversational Analytics',
  description: 'Upload Excel files and query your data with natural language. SQL-powered, deterministic answers.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
