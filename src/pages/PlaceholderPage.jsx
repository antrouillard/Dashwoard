import { Badge } from "@/components/ui/warcraftcn/badge";

function PlaceholderPage({ title }) {
  return (
    <div className="dashboard-grid">
      <section className="panel-frame md:col-span-12">
        <div className="panel-header">
          <div>
            <p className="panel-title">{title}</p>
            <p className="panel-subtitle">En preparation</p>
          </div>
          <Badge size="sm">Soon</Badge>
        </div>
        <div className="panel-body">
          <p className="text-sm text-muted-foreground">
            Cette section arrive bientot. Dis-moi ce que tu veux y voir en
            priorite.
          </p>
        </div>
      </section>
    </div>
  );
}

export default PlaceholderPage;
