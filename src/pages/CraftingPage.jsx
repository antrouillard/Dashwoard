import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/warcraftcn/badge";
import { Button } from "@/components/ui/warcraftcn/button";
import { Skeleton } from "@/components/ui/warcraftcn/skeleton";
import { mockData } from "@/data/mockData";

const Panel = ({ title, subtitle, actions, className = "", children }) => (
  <section className={`panel-frame ${className}`}>
    <div className="panel-header">
      <div>
        <p className="panel-title">{title}</p>
        {subtitle ? <p className="panel-subtitle">{subtitle}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
    </div>
    <div className="panel-body">{children}</div>
  </section>
);

const ProgressBar = ({ value }) => (
  <div className="h-2 w-full rounded-full bg-muted/50">
    <div
      className="h-2 rounded-full bg-primary shadow-[0_0_10px_rgba(245,204,120,0.4)]"
      style={{ width: `${value}%` }}
    />
  </div>
);

const actionButtonClass = "px-4 py-2 text-xs leading-none";

function CraftingPage() {
  const [viewMode, setViewMode] = useState("profession");
  const [selectedKey, setSelectedKey] = useState("Alchimie");

  const byProfession = useMemo(() => {
    const map = new Map();
    mockData.characters.forEach((character) => {
      character.professions.forEach((profession) => {
        if (!map.has(profession)) {
          map.set(profession, []);
        }
        map.get(profession).push(character.name);
      });
    });
    return Array.from(map.entries()).map(([profession, owners]) => ({
      profession,
      owners,
    }));
  }, []);

  const byCharacter = useMemo(
    () =>
      mockData.characters.map((character) => ({
        name: character.name,
        professions: character.professions,
      })),
    []
  );

  const activeProfessions = useMemo(() => {
    if (viewMode === "profession") {
      return selectedKey ? [selectedKey] : [];
    }
    const match = mockData.characters.find(
      (character) => character.name === selectedKey
    );
    return match ? match.professions : [];
  }, [selectedKey, viewMode]);

  const filteredOrders = useMemo(() => {
    if (viewMode === "character") {
      return mockData.crafting.orders.filter(
        (order) => order.owner === selectedKey
      );
    }
    return mockData.crafting.orders.filter((order) =>
      activeProfessions.includes(order.profession)
    );
  }, [activeProfessions, selectedKey, viewMode]);

  const filteredBestCrafts = useMemo(
    () =>
      mockData.crafting.bestCrafts.filter((craft) =>
        activeProfessions.includes(craft.profession)
      ),
    [activeProfessions]
  );

  const filteredKp = useMemo(
    () =>
      mockData.crafting.kp.filter((track) =>
        activeProfessions.includes(track.profession)
      ),
    [activeProfessions]
  );

  const filteredSkillTree = useMemo(
    () =>
      mockData.crafting.skillTree.filter((node) =>
        activeProfessions.includes(node.profession)
      ),
    [activeProfessions]
  );

  const filteredMaterials = useMemo(
    () =>
      mockData.crafting.materials.filter((mat) =>
        activeProfessions.includes(mat.profession)
      ),
    [activeProfessions]
  );

  return (
    <div className="dashboard-grid">
      <Panel
        title="Metiers & personnages"
        subtitle="Vue par metier ou par personnage"
        className="md:col-span-12"
        actions={
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setViewMode("profession")}
              className={`rounded-md border px-2 py-1 text-[10px] uppercase tracking-[0.2em] ${
                viewMode === "profession"
                  ? "border-primary/60 bg-card/80 text-foreground"
                  : "border-border/60 text-muted-foreground"
              }`}
            >
              Metiers
            </button>
            <button
              type="button"
              onClick={() => setViewMode("character")}
              className={`rounded-md border px-2 py-1 text-[10px] uppercase tracking-[0.2em] ${
                viewMode === "character"
                  ? "border-primary/60 bg-card/80 text-foreground"
                  : "border-border/60 text-muted-foreground"
              }`}
            >
              Persos
            </button>
          </div>
        }
      >
        {viewMode === "profession" ? (
          <div className="flex flex-wrap gap-2">
            {byProfession.map((row) => (
              <button
                key={row.profession}
                type="button"
                onClick={() => setSelectedKey(row.profession)}
                className={`rounded-full border px-3 py-1 text-xs ${
                  selectedKey === row.profession
                    ? "border-primary/60 bg-card/90 text-foreground"
                    : "border-border/60 text-muted-foreground"
                }`}
              >
                {row.profession}
                <span className="ml-2 text-[10px] text-muted-foreground">
                  {row.owners.length}
                </span>
              </button>
            ))}
          </div>
        ) : (
          <div className="flex flex-wrap gap-2">
            {byCharacter.map((row) => (
              <button
                key={row.name}
                type="button"
                onClick={() => setSelectedKey(row.name)}
                className={`rounded-full border px-3 py-1 text-xs ${
                  selectedKey === row.name
                    ? "border-primary/60 bg-card/90 text-foreground"
                    : "border-border/60 text-muted-foreground"
                }`}
              >
                {row.name}
                <span className="ml-2 text-[10px] text-muted-foreground">
                  {row.professions.length}
                </span>
              </button>
            ))}
          </div>
        )}
      </Panel>

      <Panel
        title="Commandes"
        subtitle="Priorite et statut"
        className="md:col-span-6"
        actions={
          <Button variant="frame" className={actionButtonClass}>
            Nouvelle commande
          </Button>
        }
      >
        <table className="dense-table">
          <thead>
            <tr>
              <th>Client</th>
              <th>Objet</th>
              <th>Metier</th>
              <th>Statut</th>
              <th>Marge</th>
            </tr>
          </thead>
          <tbody>
            {filteredOrders.map((order) => (
              <tr key={order.id}>
                <td className="text-foreground">{order.client}</td>
                <td>{order.item}</td>
                <td>{order.profession}</td>
                <td>
                  <Badge size="sm" variant={order.statusVariant}>
                    {order.status}
                  </Badge>
                </td>
                <td>{order.profit}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>

      <Panel
        title="Crafts rentables"
        subtitle="Top marges et temps"
        className="md:col-span-6"
        actions={<Badge size="sm">Live</Badge>}
      >
        <table className="dense-table">
          <thead>
            <tr>
              <th>Objet</th>
              <th>Metier</th>
              <th>Marge</th>
              <th>Temps</th>
            </tr>
          </thead>
          <tbody>
            {filteredBestCrafts.map((craft) => (
              <tr key={craft.item}>
                <td className="text-foreground">{craft.item}</td>
                <td>{craft.profession}</td>
                <td>{craft.profit}</td>
                <td>{craft.time}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>

      <Panel
        title="Knowledge Points"
        subtitle="KP recoltes / KP max"
        className="md:col-span-4"
        actions={
          <Button variant="frame" className={actionButtonClass}>
            Voir KP
          </Button>
        }
      >
        <div className="space-y-3">
          {filteredKp.map((track) => {
            const percent = Math.round((track.current / track.max) * 100);
            return (
              <div key={track.profession} className="space-y-2">
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>{track.profession}</span>
                  <span>
                    {track.current}/{track.max}
                  </span>
                </div>
                <ProgressBar value={percent} />
              </div>
            );
          })}
        </div>
      </Panel>

      <Panel
        title="Arbre de competence"
        subtitle="Noeuds a debloquer"
        className="md:col-span-4"
        actions={<Badge size="sm">En cours</Badge>}
      >
        <div className="space-y-3">
          {filteredSkillTree.map((node) => (
            <div key={node.name} className="rounded-md border border-border/60 bg-card/70 px-3 py-2">
              <div className="flex items-center justify-between">
                <p className="text-sm text-foreground">{node.name}</p>
                <Badge size="sm" variant="outline">
                  {node.level}
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground">{node.detail}</p>
            </div>
          ))}
        </div>
      </Panel>

      <Panel
        title="Stock matieres"
        subtitle="Ce qu'il manque pour les crafts"
        className="md:col-span-4"
        actions={
          <Button variant="frame" className={actionButtonClass}>
            Importer sac
          </Button>
        }
      >
        <div className="space-y-2">
          {filteredMaterials.map((mat) => (
            <div key={mat.name} className="flex items-center justify-between text-xs">
              <span className="text-foreground">{mat.name}</span>
              <span className="text-muted-foreground">{mat.need}</span>
            </div>
          ))}
        </div>
      </Panel>

      <Panel
        title="En cours de sync"
        subtitle="AH et commandes"
        className="md:col-span-12"
        actions={<Badge size="sm">Sync</Badge>}
      >
        <div className="grid gap-3 sm:grid-cols-4">
          <Skeleton className="h-16 w-full" faction="human" />
          <Skeleton className="h-16 w-full" faction="orc" />
          <Skeleton className="h-16 w-full" faction="elf" />
          <Skeleton className="h-16 w-full" faction="undead" />
        </div>
      </Panel>
    </div>
  );
}

export default CraftingPage;
