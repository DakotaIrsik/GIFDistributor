import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'GIF Distributor',
  description: 'Upload once, distribute to GIPHY, Tenor, Slack, Discord, and more',
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
