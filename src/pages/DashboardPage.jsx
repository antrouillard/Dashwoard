import { useMemo, useCallback, useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Badge } from "@/components/ui/warcraftcn/badge";
import { Button } from "@/components/ui/warcraftcn/button";
import { Skeleton } from "@/components/ui/warcraftcn/skeleton";
import { mockData } from "@/data/mockData";
import { getCurrentWeek } from "@/data/activities";

const STORAGE_KEY = "wow-activities-done";
function loadActivityDone() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "{}"); }
  catch { return {}; }
}
import {
  useDefaultAccount,
  useCharacters,
  useAllTodos,
  useAdvanceTodo,
  useGuilds,
} from "@/hooks/useWow";

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

const STATUS_LABEL = {
  a_faire: "A faire",
  en_cours: "En cours",
  termine: "Termine",
};

const statusToBadge = (status) => {
  switch (status) {
    case "termine":
    case "Termine":
      return { variant: "default", className: "text-emerald-100" };
    case "en_cours":
    case "En cours":
      return { variant: "secondary", className: "text-amber-100" };
    default:
      return { variant: "outline", className: "text-slate-200" };
  }
};

const roleStyle = (role) => {
  if (!role) return "border-slate-500/40 bg-slate-500/10 text-slate-400";
  if (role.includes("Heal")) {
    return "border-emerald-500/40 bg-emerald-500/10 text-emerald-100";
  }
  if (role.includes("Tank")) {
    return "border-blue-500/40 bg-blue-500/10 text-blue-100";
  }
  return "border-amber-500/40 bg-amber-500/10 text-amber-100";
};

function DashboardPage() {
  const navigate = useNavigate();
  // â”€â”€ DonnÃ©es API â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  const { data: account } = useDefaultAccount();
  const { data: characters, loading: charsLoading } = useCharacters(account?.id);
  const { data: todosRaw, refetch: refetchTodos } = useAllTodos();
  const { data: guilds } = useGuilds();

  const { advanceTodo } = useAdvanceTodo(refetchTodos);

  // Fallback mockData pour les sections pas encore en API (market, heroStats)
  const market = mockData.market;
  const heroStats = mockData.heroStats;

  // Activities : semaine courante depuis le calendrier
  const currentWeek = useMemo(() => getCurrentWeek(new Date()), []);
  const [actDone, setActDone] = useState(() => loadActivityDone());
  // Sync avec localStorage (partagé avec ActivitiesPage)
  useEffect(() => {
    const onStorage = () => setActDone(loadActivityDone());
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);
  const priorityTasks = useMemo(
    () => (currentWeek?.tasks ?? []).filter((t) => t.important).slice(0, 5),
    [currentWeek]
  );
  const weekDoneCount = useMemo(
    () => (currentWeek?.tasks ?? []).filter((t) => actDone[t.id]).length,
    [currentWeek, actDone]
  );
  const weekTotal = currentWeek?.tasks?.length ?? 0;

  // Guilde principale (premiÃ¨re de la liste)
  const guild = guilds?.[0] ?? null;

  // Todos : groupÃ©s par personnage avec enrichissement du nom
  const flatTodos = useMemo(() => {
    if (!todosRaw || !characters) return [];
    return todosRaw.map((todo) => {
      const char = characters.find((c) => c.id === todo.character_id);
      return { ...todo, ownerName: char?.name ?? "â€”" };
    });
  }, [todosRaw, characters]);

  const todoCompletion = useMemo(() => {
    if (!flatTodos.length) return 0;
    const score = flatTodos.reduce((total, task) => {
      if (task.status === "termine") return total + 1;
      if (task.status === "en_cours") return total + 0.5;
      return total;
    }, 0);
    return Math.round((score / flatTodos.length) * 100);
  }, [flatTodos]);

  const handleAdvanceTodo = useCallback(
    async (todoId) => {
      await advanceTodo(todoId);
    },
    [advanceTodo]
  );

  // Affichage gold : copper â†’ "XXXk" / "X.Xm"
  const goldDisplay = useCallback((copper) => {
    const gold = Math.floor(copper / 10000);
    if (gold >= 1_000_000) return `${(gold / 1_000_000).toFixed(1)}M`;
    if (gold >= 1_000) return `${Math.floor(gold / 1_000)}k`;
    return `${gold}g`;
  }, []);

  return (
    <div className="dashboard-grid">
      {/* â”€â”€ ActivitÃ©s hebdo â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      {/* ── Activités (calendrier) ──────────────────────────────────────── */}
      <Panel
        title="Activites"
        subtitle={currentWeek ? currentWeek.subtitle : "Avant le lancement"}
        className="md:col-span-3"
        actions={
          <div className="flex items-center gap-2">
            <Badge size="sm">{weekDoneCount}/{weekTotal}</Badge>
            <button
              onClick={() => navigate("/activites")}
              className="text-[10px] text-muted-foreground hover:text-primary transition-colors"
            >
              Tout voir →
            </button>
          </div>
        }
      >
        {/* Mini progress bar */}
        <div className="mb-3">
          <div className="h-1 w-full rounded-full bg-muted/60 overflow-hidden">
            <div
              className={`h-1 rounded-full transition-all duration-500 ${
                weekTotal > 0 && weekDoneCount === weekTotal
                  ? "bg-emerald-500"
                  : "bg-primary"
              }`}
              style={{ width: weekTotal > 0 ? `${Math.round((weekDoneCount / weekTotal) * 100)}%` : "0%" }}
            />
          </div>
        </div>

        {/* Crest warning */}
        {currentWeek?.note && (
          <div className="mb-3 flex items-start gap-1.5 rounded border border-amber-500/30 bg-amber-500/8 px-2 py-1.5">
            <span className="shrink-0 text-amber-400 text-xs">⚠</span>
            <p className="text-[10px] text-amber-200 leading-snug">{currentWeek.note}</p>
          </div>
        )}

        {!currentWeek && (
          <p className="text-xs text-muted-foreground">
            Le programme commence le 26 févr. 2026 (Early Access).
          </p>
        )}

        {/* Priorité-only tasks */}
        <div className="flex flex-col gap-1.5">
          {priorityTasks.map((task) => {
            const done = !!actDone[task.id];
            return (
              <div
                key={task.id}
                className={`flex items-start gap-2 rounded border px-2 py-1.5 ${
                  done
                    ? "border-emerald-500/20 bg-emerald-500/5 opacity-60"
                    : "border-primary/20 bg-primary/5"
                }`}
              >
                <span
                  className={`mt-0.5 flex h-3 w-3 shrink-0 items-center justify-center rounded border ${
                    done ? "border-emerald-500 bg-emerald-500" : "border-primary/50"
                  }`}
                >
                  {done && (
                    <svg className="h-2 w-2 text-black" viewBox="0 0 10 10" fill="none">
                      <path d="M1.5 5L4 7.5 8.5 2.5" stroke="currentColor" strokeWidth="1.5"
                        strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  )}
                </span>
                <p className={`text-[11px] leading-snug ${
                  done ? "line-through text-muted-foreground" : "text-foreground/90"
                }`}>
                  {task.label}
                </p>
              </div>
            );
          })}
        </div>

        {currentWeek && priorityTasks.length < weekTotal && (
          <button
            onClick={() => navigate("/activites")}
            className="mt-2 block w-full text-center text-[10px] text-muted-foreground hover:text-primary transition-colors"
          >
            +{weekTotal - priorityTasks.length} autres tâches →
          </button>
        )}
      </Panel>

      {/* â”€â”€ Personnages â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      <Panel
        title="Personnages"
        className="md:col-span-5"
        actions={<Button variant="frame">Ajouter</Button>}
      >
        <div className="space-y-1.5">
          {charsLoading &&
            Array.from({ length: 4 }).map((_, i) => (
              <div
                key={`char-skeleton-${i}`}
                className="flex items-center gap-3 rounded-lg border border-border/70 bg-card/70 px-3 py-1.5"
              >
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-4 w-16" />
                <Skeleton className="ml-auto h-4 w-10" />
              </div>
            ))}

          {!charsLoading &&
            (characters ?? []).map((character) => (
              <div
                key={character.id}
                className="flex items-center gap-3 rounded-lg border border-border/70 bg-card/70 px-3 py-1.5"
              >
                {/* Nom + rÃ´le */}
                <div className="flex min-w-0 flex-1 items-center gap-2">
                  <p className="text-sm leading-tight text-foreground">
                    {character.name}
                  </p>
                  <p
                    className={`inline-flex shrink-0 items-center rounded-full border px-2 py-0.5 text-[9px] uppercase tracking-[0.18em] ${roleStyle(
                      character.role
                    )}`}
                  >
                    {character.role}
                    {character.spec ? ` - ${character.spec}` : ""}
                  </p>
                </div>
                {/* M+ */}
                <p className="shrink-0 text-[10px] text-muted-foreground">
                  M+ {character.mythic_score.toLocaleString()}
                </p>
                {/* Or */}
                <div className="flex shrink-0 items-center gap-1 text-[10px] text-muted-foreground">
                  <svg aria-hidden="true" viewBox="0 0 24 24" className="h-3 w-3 text-primary" fill="currentColor">
                    <path d="M12 3c-4.4 0-8 2.2-8 5s3.6 5 8 5 8-2.2 8-5-3.6-5-8-5zm0 12c-4.4 0-8-2.2-8-5v4c0 2.8 3.6 5 8 5s8-2.2 8-5v-4c0 2.8-3.6 5-8 5z" />
                  </svg>
                  <span className="text-foreground">{goldDisplay(character.gold)}</span>
                </div>
                {/* MÃ©tiers */}
                <p className="shrink-0 text-[10px] text-muted-foreground">
                  {character.professions.map((p) => p.name).join(" / ")}
                </p>
                {/* ilvl */}
                <div className="shrink-0 text-right">
                  <p className="text-[9px] uppercase tracking-[0.2em] text-muted-foreground">ilvl</p>
                  <p className="text-sm leading-tight text-foreground">{character.ilvl}</p>
                </div>
              </div>
            ))}
        </div>
      </Panel>

      {/* â”€â”€ Vue d'ensemble + Guilde â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      <div className="md:col-span-4 space-y-3">
        <Panel
          title="Vue d'ensemble"
          subtitle={`Reset dans ${mockData.account.resetHours}h`}
          className="panel-compact"
          actions={<Badge size="sm">Live</Badge>}
        >
          <div className="grid gap-2 sm:grid-cols-2">
            {heroStats.map((stat) => (
              <div
                key={stat.label}
                className="rounded-md border border-border/70 bg-card/70 px-2 py-2"
              >
                <p className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                  {stat.label}
                </p>
                <p className="text-lg text-foreground">{stat.value}</p>
              </div>
            ))}
          </div>
        </Panel>

        <Panel
          title="Progression de guilde"
          subtitle={
            guild
              ? `${guild.raid_name ?? guild.name} â€¢ ${guild.member_count} membres`
              : mockData.guild.raid
          }
          className="panel-compact"
          actions={<Badge faction="alliance">Roster</Badge>}
        >
          <div className="space-y-2">
            <div className="rounded-md border border-border/60 bg-card/70 px-2 py-2">
              <p className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                Prochain boss
              </p>
              <p className="text-sm text-foreground">{mockData.guild.nextBoss}</p>
              <p className="text-[10px] text-muted-foreground">
                {mockData.guild.pulls} trys
              </p>
            </div>
            {(guild?.raid_progress ?? mockData.guild.progress).map((stage) => {
              const percent = Math.round((stage.done / stage.total) * 100);
              return (
                <div key={stage.label} className="space-y-1">
                  <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                    <span>{stage.label}</span>
                    <span>{stage.done}/{stage.total}</span>
                  </div>
                  <div className="h-1 w-full rounded-full bg-muted/50">
                    <div
                      className="h-1 rounded-full bg-primary shadow-[0_0_8px_rgba(245,204,120,0.35)]"
                      style={{ width: `${percent}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </Panel>
      </div>

      {/* â”€â”€ Prix AH â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      <Panel
        title="Prix AH"
        subtitle="A garder sous le coude"
        className="md:col-span-6"
        actions={<Button variant="frame">Alertes</Button>}
      >
        <table className="dense-table">
          <thead>
            <tr>
              <th>Objet</th>
              <th>Prix</th>
              <th>Tendance</th>
              <th>Focus</th>
            </tr>
          </thead>
          <tbody>
            {market.map((item) => (
              <tr key={item.item}>
                <td className="text-foreground">{item.item}</td>
                <td>{item.price}</td>
                <td>{item.trend}</td>
                <td>
                  <Badge size="sm" variant="outline">{item.focus}</Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>

      {/* â”€â”€ Todos â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      <Panel
        title="Todos"
        subtitle="Cochage direct et statut"
        className="md:col-span-6"
        actions={
          <div className="flex items-center gap-3">
            <div className="min-w-[140px]">
              <div className="flex items-center justify-between text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                <span>Progression</span>
                <span>{todoCompletion}%</span>
              </div>
              <div className="mt-1 h-1.5 w-full rounded-full bg-muted/60">
                <div
                  className={`h-1.5 rounded-full shadow-[0_0_10px_rgba(245,204,120,0.35)] ${
                    todoCompletion === 100 ? "rainbow-progress" : "bg-primary"
                  }`}
                  style={{ width: `${todoCompletion}%` }}
                />
              </div>
            </div>
            <Button variant="frame">Ajouter</Button>
          </div>
        }
      >
        <table className="dense-table">
          <thead>
            <tr>
              <th>Perso</th>
              <th>Tache</th>
              <th>Etat</th>
            </tr>
          </thead>
          <tbody>
            {flatTodos.map((task) => {
              const badgeProps = statusToBadge(task.status);
              return (
                <tr key={task.id}>
                  <td>
                    <Badge size="sm" variant="outline">{task.ownerName}</Badge>
                  </td>
                  <td className="text-foreground">{task.title}</td>
                  <td>
                    <Badge size="sm" {...badgeProps} asChild>
                      <button
                        type="button"
                        className="cursor-pointer"
                        onClick={() => handleAdvanceTodo(task.id)}
                      >
                        {STATUS_LABEL[task.status] ?? task.status}
                      </button>
                    </Badge>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Panel>

    </div>
  );
}

export default DashboardPage;
