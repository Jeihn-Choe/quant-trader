import { PropsWithChildren, ReactNode } from "react";

interface SectionCardProps extends PropsWithChildren {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  accent?: "amber" | "teal" | "coral";
}

export function SectionCard({
  title,
  subtitle,
  actions,
  accent = "amber",
  children
}: SectionCardProps) {
  return (
    <section className={`section-card accent-${accent}`}>
      <header className="section-header">
        <div>
          <p className="section-eyebrow">{title}</p>
          {subtitle ? <h2>{subtitle}</h2> : null}
        </div>
        {actions ? <div className="section-actions">{actions}</div> : null}
      </header>
      <div className="section-body">{children}</div>
    </section>
  );
}
