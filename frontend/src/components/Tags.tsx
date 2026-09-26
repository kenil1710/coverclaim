import { human } from "@/lib/format";

export function PerilTags({ perils, exclusions, max }: { perils: string[]; exclusions?: string[]; max?: number }) {
  const list = max ? perils.slice(0, max) : perils;
  return (
    <div className="row" style={{ gap: 6 }}>
      {list.map((p) => (
        <span key={p} className="tag tag-peril">{human(p)}</span>
      ))}
      {max && perils.length > max && <span className="tag tag-peril">+{perils.length - max}</span>}
      {exclusions?.map((x) => (
        <span key={x} className="tag tag-excl">✕ {human(x)}</span>
      ))}
    </div>
  );
}
