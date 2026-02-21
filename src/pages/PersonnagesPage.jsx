import { useState, useCallback } from "react";
import { Badge } from "@/components/ui/warcraftcn/badge";
import { Button } from "@/components/ui/warcraftcn/button";
import { Skeleton } from "@/components/ui/warcraftcn/skeleton";
import {
  useDefaultAccount,
  useCharacters,
  useCreateCharacter,
  useDeleteCharacter,
  useSyncAccount,
} from "@/hooks/useWow";
import { api } from "@/lib/api";
import { useMutation } from "@/hooks/useApi";

// ── Helpers ───────────────────────────────────────────────────────────────────

const CLASS_COLOR = {
  "Chasseur de démons": "text-purple-300",
  "Chevalier de la mort": "text-red-400",
  "Paladin": "text-pink-300",
  "Guerrier": "text-amber-400",
  "Mage": "text-sky-300",
  "Démoniste": "text-violet-400",
  "Prêtre": "text-slate-100",
  "Druide": "text-orange-400",
  "Chaman": "text-blue-400",
  "Moine": "text-emerald-400",
  "Chasseur": "text-lime-400",
  "Voleur": "text-yellow-300",
  "Évocateur": "text-teal-400",
};

const ROLE_OPTIONS = ["DPS", "Heal", "Tank"];
const REALM_SUGGESTIONS = ["Archimonde", "Hyjal", "Ysondre", "Kirin Tor", "Cho'gall", "Medivh"];

function RaiderioRuns({ runs }) {
  if (!runs || runs.length === 0) {
    return <p className="text-xs text-muted-foreground italic">Aucun run enregistré</p>;
  }
  return (
    <div className="space-y-1">
      {runs.map((run, i) => (
        <div key={i} className="flex items-center justify-between rounded bg-background/40 px-2 py-1 text-xs">
          <span className="font-medium text-foreground truncate max-w-[120px]">
            {run.short_name ?? run.dungeon}
          </span>
          <span className="text-primary font-bold ml-2">+{run.mythic_level}</span>
          <span className="text-muted-foreground ml-2">{Math.round(run.score ?? 0)} pts</span>
        </div>
      ))}
    </div>
  );
}

function CharacterCard({ char, onDelete, onSyncOne }) {
  const [expanded, setExpanded] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const classColor = CLASS_COLOR[char.class_name] ?? "text-foreground";

  return (
    <div className="panel-frame">
      <div className="panel-header">
        <div className="min-w-0">
          <p className={`font-semibold text-base truncate ${classColor}`}>{char.name}</p>
          <p className="text-xs text-muted-foreground">{char.realm} · {char.region?.toUpperCase()}</p>
        </div>
        <div className="flex gap-1 shrink-0">
          <Button variant="ghost" className="text-xs px-2 py-1 h-7" onClick={() => setExpanded((v) => !v)}>
            {expanded ? "▲" : "▼"}
          </Button>
          {!confirmDelete ? (
            <Button variant="ghost" className="text-xs text-destructive px-2 py-1 h-7" onClick={() => setConfirmDelete(true)}>
              ✕
            </Button>
          ) : (
            <span className="flex gap-1 text-xs">
              <Button variant="ghost" className="px-2 py-1 h-7 text-destructive" onClick={() => onDelete(char.id)}>Suppr.</Button>
              <Button variant="ghost" className="px-2 py-1 h-7" onClick={() => setConfirmDelete(false)}>Annuler</Button>
            </span>
          )}
        </div>
      </div>

      <div className="panel-body space-y-2">
        {/* Stats principales */}
        <div className="flex flex-wrap gap-2 text-xs">
          <span className="text-muted-foreground">{char.class_name ?? "—"}</span>
          {char.spec && <span className="text-muted-foreground">· {char.spec}</span>}
          {char.role && (
            <Badge variant="outline" className="text-[10px] px-1.5 py-0">
              {char.role}
            </Badge>
          )}
        </div>

        <div className="grid grid-cols-3 gap-2 text-xs">
          <div className="rounded bg-background/40 px-2 py-1 text-center">
            <p className="text-[10px] text-muted-foreground uppercase tracking-wide">ilvl</p>
            <p className="font-bold text-foreground">{char.ilvl_equipped || char.ilvl || "—"}</p>
          </div>
          <div className="rounded bg-background/40 px-2 py-1 text-center">
            <p className="text-[10px] text-muted-foreground uppercase tracking-wide">M+</p>
            <p className="font-bold text-primary">
              {char.raiderio_score > 0
                ? char.raiderio_score.toFixed(0)
                : char.mythic_score > 0
                ? char.mythic_score.toFixed(0)
                : "—"}
            </p>
          </div>
          <div className="rounded bg-background/40 px-2 py-1 text-center">
            <p className="text-[10px] text-muted-foreground uppercase tracking-wide">Or</p>
            <p className="font-bold text-yellow-400">{char.gold_display}</p>
          </div>
        </div>

        {/* Rangs Raider.io */}
        {char.raiderio_score > 0 && (
          <div className="text-[10px] text-muted-foreground flex gap-3 flex-wrap">
            {char.raiderio_rank_realm && <span>Royaume: #{char.raiderio_rank_realm}</span>}
            {char.raiderio_rank_region && <span>Région: #{char.raiderio_rank_region}</span>}
            {char.raiderio_rank_world && <span>Monde: #{char.raiderio_rank_world}</span>}
          </div>
        )}

        {/* Détail expandable */}
        {expanded && (
          <div className="border-t border-border/30 pt-2 space-y-2">
            {/* Professions */}
            {char.professions?.length > 0 && (
              <div>
                <p className="text-[10px] uppercase tracking-wide text-muted-foreground mb-1">Professions</p>
                <div className="space-y-0.5">
                  {char.professions.map((p) => (
                    <div key={p.id} className="flex justify-between text-xs">
                      <span className="text-foreground">{p.name}</span>
                      <span className="text-muted-foreground">{p.kp_current}/{p.kp_max}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Meilleurs runs M+ */}
            <div>
              <p className="text-[10px] uppercase tracking-wide text-muted-foreground mb-1">Meilleurs runs M+</p>
              <RaiderioRuns runs={char.raiderio_best_runs} />
            </div>

            <div className="flex justify-end">
              <Button
                variant="ghost"
                className="text-xs px-2 py-1 h-7"
                onClick={() => onSyncOne(char.id)}
              >
                Sync ce perso
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function AddCharacterForm({ accountId, onCreated }) {
  const [form, setForm] = useState({ name: "", realm: "Archimonde", role: "DPS", region: "eu" });
  const { createCharacter, loading } = useCreateCharacter(onCreated);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) return;
    await createCharacter({ ...form, account_id: accountId });
    setForm({ name: "", realm: "Archimonde", role: "DPS", region: "eu" });
  };

  return (
    <form onSubmit={handleSubmit} className="panel-frame">
      <div className="panel-header">
        <p className="panel-title">Ajouter un personnage</p>
      </div>
      <div className="panel-body space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-[10px] uppercase tracking-wide text-muted-foreground">Nom</label>
            <input
              value={form.name}
              onChange={set("name")}
              placeholder="Dhetdkouto"
              className="mt-1 w-full rounded border border-border/40 bg-background/60 px-2 py-1.5 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/50"
              required
            />
          </div>
          <div>
            <label className="text-[10px] uppercase tracking-wide text-muted-foreground">Royaume</label>
            <input
              value={form.realm}
              onChange={set("realm")}
              list="realm-suggestions"
              placeholder="Archimonde"
              className="mt-1 w-full rounded border border-border/40 bg-background/60 px-2 py-1.5 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/50"
              required
            />
            <datalist id="realm-suggestions">
              {REALM_SUGGESTIONS.map((r) => <option key={r} value={r} />)}
            </datalist>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-[10px] uppercase tracking-wide text-muted-foreground">Rôle</label>
            <select
              value={form.role}
              onChange={set("role")}
              className="mt-1 w-full rounded border border-border/40 bg-background/60 px-2 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
            >
              {ROLE_OPTIONS.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
          <div>
            <label className="text-[10px] uppercase tracking-wide text-muted-foreground">Région</label>
            <select
              value={form.region}
              onChange={set("region")}
              className="mt-1 w-full rounded border border-border/40 bg-background/60 px-2 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
            >
              <option value="eu">EU</option>
              <option value="us">US</option>
              <option value="kr">KR</option>
              <option value="tw">TW</option>
            </select>
          </div>
        </div>

        <Button type="submit" disabled={loading} className="w-full">
          {loading ? "Ajout en cours..." : "Ajouter le personnage"}
        </Button>
      </div>
    </form>
  );
}

// ── Page principale ───────────────────────────────────────────────────────────

export default function PersonnagesPage() {
  const [syncMsg, setSyncMsg] = useState(null);
  const { data: account } = useDefaultAccount();
  const { data: characters, loading, refetch } = useCharacters(account?.id);

  const { deleteCharacter } = useDeleteCharacter(refetch);

  const { mutate: syncOneBlizzard } = useMutation((charId) =>
    api.sync.character(charId)
  );
  const { mutate: syncOneRaiderio } = useMutation((charId) =>
    api.sync.raiderioCharacter(charId)
  );

  const handleSyncOne = useCallback(async (charId) => {
    setSyncMsg("Synchronisation...");
    await Promise.allSettled([syncOneBlizzard(charId), syncOneRaiderio(charId)]);
    refetch();
    setSyncMsg("Sync terminée ✓");
    setTimeout(() => setSyncMsg(null), 3000);
  }, [syncOneBlizzard, syncOneRaiderio, refetch]);

  const { syncAccount, loading: syncing } = useSyncAccount((result) => {
    setSyncMsg(`${result.synced}/${result.total} persos synchronisés ✓`);
    refetch();
    setTimeout(() => setSyncMsg(null), 4000);
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-2xl text-foreground">Personnages</h2>
          <p className="text-sm text-muted-foreground">
            {characters?.length ?? 0} personnage{characters?.length !== 1 ? "s" : ""} sur {account?.name ?? "—"}
          </p>
        </div>
        <div className="flex gap-2 items-center">
          {syncMsg && (
            <span className="text-xs text-primary">{syncMsg}</span>
          )}
          <Button
            onClick={() => account?.id && syncAccount(account.id)}
            disabled={syncing || !account?.id}
          >
            {syncing ? "Synchronisation..." : "Tout synchroniser"}
          </Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        {/* Liste des personnages */}
        <div className="space-y-3">
          {loading
            ? Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="panel-frame">
                  <div className="panel-body space-y-2">
                    <Skeleton className="h-5 w-40" />
                    <Skeleton className="h-4 w-24" />
                    <div className="grid grid-cols-3 gap-2">
                      {[0, 1, 2].map((j) => <Skeleton key={j} className="h-10" />)}
                    </div>
                  </div>
                </div>
              ))
            : characters?.length === 0
            ? (
                <div className="panel-frame">
                  <div className="panel-body text-center py-8 text-muted-foreground">
                    Aucun personnage. Ajoutes-en un à droite.
                  </div>
                </div>
              )
            : characters?.map((char) => (
                <CharacterCard
                  key={char.id}
                  char={char}
                  onDelete={deleteCharacter}
                  onSyncOne={handleSyncOne}
                />
              ))}
        </div>

        {/* Formulaire d'ajout */}
        <div>
          {account?.id ? (
            <AddCharacterForm accountId={account.id} onCreated={refetch} />
          ) : (
            <div className="panel-frame">
              <div className="panel-body text-sm text-muted-foreground">
                Chargement du compte...
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
