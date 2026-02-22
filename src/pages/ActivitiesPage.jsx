import { useState, useEffect, useMemo, useCallback } from "react";
import { WEEKS, getCurrentWeek } from "@/data/activities";
import { Badge } from "@/components/ui/warcraftcn/badge";
import { Button } from "@/components/ui/warcraftcn/button";

/* ─── helpers ──────────────────────────────────────────────────────────── */

const STORAGE_KEY = "wow-activities-done";

function loadDone() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "{}");
  } catch {
    return {};
  }
}

function saveDone(data) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}

function fmtDate(isoStr) {
  if (!isoStr) return "∞";
  const [y, m, d] = isoStr.split("-");
  return new Date(Number(y), Number(m) - 1, Number(d)).toLocaleDateString(
    "fr-FR",
    { day: "numeric", month: "short" }
  );
}

/* ─── sub-components ────────────────────────────────────────────────────── */

const Panel = ({ title, subtitle, actions, className = "", children }) => (
  <section className={`panel-frame ${className}`}>
    <div className="panel-header">
      <div>
        <p className="panel-title">{title}</p>
        {subtitle && <p className="panel-subtitle">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
    <div className="panel-body">{children}</div>
  </section>
);

function ProgressBar({ done, total }) {
  const pct = total === 0 ? 0 : Math.round((done / total) * 100);
  const color =
    pct === 100
      ? "bg-emerald-500"
      : pct >= 60
      ? "bg-amber-400"
      : "bg-primary";

  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 overflow-hidden rounded-full bg-muted h-2">
        <div
          className={`h-2 rounded-full transition-all duration-500 ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-muted-foreground tabular-nums w-14 text-right">
        {done}/{total} ({pct}%)
      </span>
    </div>
  );
}

function WeekSelector({ weeks, selectedId, onSelect, currentId }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {weeks.map((w) => {
        const isSelected = w.id === selectedId;
        const isCurrent = w.id === currentId;
        return (
          <button
            key={w.id}
            onClick={() => onSelect(w.id)}
            className={[
              "rounded border px-3 py-1 text-[11px] uppercase tracking-[0.15em] transition-all",
              isSelected
                ? "border-primary bg-primary/20 text-primary"
                : "border-border/60 bg-card/60 text-muted-foreground hover:border-primary/50 hover:text-foreground",
            ].join(" ")}
          >
            {isCurrent && !isSelected && (
              <span className="mr-1 inline-block h-1.5 w-1.5 rounded-full bg-emerald-400 align-middle" />
            )}
            {w.title}
            {isCurrent && (
              <span className="ml-1.5 text-[9px] text-emerald-400 normal-case tracking-normal">
                now
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

function TaskRow({ task, done, onToggle }) {
  return (
    <label
      className={[
        "flex cursor-pointer items-start gap-3 rounded-lg border px-3 py-2.5 transition-all",
        done
          ? "border-emerald-500/30 bg-emerald-500/5 opacity-60"
          : task.important
          ? "border-primary/25 bg-primary/5 hover:border-primary/40"
          : "border-border/50 bg-card/40 hover:border-border",
      ].join(" ")}
    >
      {/* custom checkbox */}
      <span
        className={[
          "mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded border transition-colors",
          done
            ? "border-emerald-500 bg-emerald-500"
            : task.important
            ? "border-primary/60 bg-transparent"
            : "border-border bg-transparent",
        ].join(" ")}
      >
        {done && (
          <svg
            className="h-2.5 w-2.5 text-black"
            viewBox="0 0 10 10"
            fill="none"
          >
            <path
              d="M1.5 5L4 7.5 8.5 2.5"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        )}
        <input
          type="checkbox"
          className="sr-only"
          checked={done}
          onChange={() => onToggle(task.id)}
        />
      </span>

      <div className="flex-1 min-w-0">
        <p
          className={[
            "text-sm leading-snug",
            done
              ? "line-through text-muted-foreground"
              : task.important
              ? "text-foreground font-medium"
              : "text-foreground/85",
          ].join(" ")}
        >
          {task.label}
        </p>
        {task.note && (
          <p className="mt-0.5 text-[11px] italic text-muted-foreground">
            {task.note}
          </p>
        )}
      </div>

      {task.important && !done && (
        <span className="shrink-0 rounded-full border border-primary/40 bg-primary/10 px-2 py-0.5 text-[9px] uppercase tracking-[0.2em] text-primary">
          Priorité
        </span>
      )}
    </label>
  );
}

/* ─── main page ─────────────────────────────────────────────────────────── */

function ActivitiesPage() {
  const today = new Date();
  const currentWeek = getCurrentWeek(today);

  // Which week is displayed (default = current, or first if before schedule)
  const [selectedId, setSelectedId] = useState(
    currentWeek?.id ?? WEEKS[0].id
  );

  // Checked task IDs – persisted in localStorage
  const [done, setDone] = useState(() => loadDone());

  // Persist on every change
  useEffect(() => {
    saveDone(done);
  }, [done]);

  const selectedWeek = useMemo(
    () => WEEKS.find((w) => w.id === selectedId) ?? WEEKS[0],
    [selectedId]
  );

  const toggleTask = useCallback((taskId) => {
    setDone((prev) => {
      const next = { ...prev, [taskId]: !prev[taskId] };
      return next;
    });
  }, []);

  const resetWeek = useCallback(() => {
    const ids = selectedWeek.tasks.map((t) => t.id);
    setDone((prev) => {
      const next = { ...prev };
      ids.forEach((id) => delete next[id]);
      return next;
    });
  }, [selectedWeek]);

  const doneCount = useMemo(
    () => selectedWeek.tasks.filter((t) => done[t.id]).length,
    [selectedWeek, done]
  );

  const totalCount = selectedWeek.tasks.length;

  // Date range label
  const dateRange = selectedWeek.endDate
    ? `${fmtDate(selectedWeek.startDate)} – ${fmtDate(selectedWeek.endDate)}`
    : `${fmtDate(selectedWeek.startDate)} et au-delà`;

  // Before the schedule starts
  const beforeSchedule =
    currentWeek === null &&
    today.toISOString().split("T")[0] < WEEKS[0].startDate;

  return (
    <div className="dashboard-grid">
      {/* ── Week Selector ──────────────────────────────────────────────── */}
      <Panel
        title="Programme de progression"
        subtitle="TWW Saison 1 · 2026"
        className="md:col-span-12"
        actions={
          <div className="flex items-center gap-2">
            {currentWeek && (
              <Badge size="sm" className="text-emerald-100">
                Semaine courante : {currentWeek.title}
              </Badge>
            )}
            {beforeSchedule && (
              <Badge size="sm" variant="outline">
                Early Access commence le {fmtDate(WEEKS[0].startDate)}
              </Badge>
            )}
          </div>
        }
      >
        <WeekSelector
          weeks={WEEKS}
          selectedId={selectedId}
          onSelect={setSelectedId}
          currentId={currentWeek?.id}
        />
      </Panel>

      {/* ── Current Week Detail ─────────────────────────────────────────── */}
      <Panel
        title={selectedWeek.title}
        subtitle={`${dateRange} · ${selectedWeek.subtitle}`}
        className="md:col-span-7"
        actions={
          <button
            onClick={resetWeek}
            className="text-[10px] text-muted-foreground hover:text-destructive transition-colors"
            title="Remettre toutes les tâches à 0"
          >
            Réinitialiser
          </button>
        }
      >
        {/* Progress */}
        <div className="mb-4">
          <ProgressBar done={doneCount} total={totalCount} />
        </div>

        {/* Crest / spending warning */}
        {selectedWeek.note && (
          <div className="mb-4 flex items-start gap-2 rounded-lg border border-amber-500/30 bg-amber-500/8 px-3 py-2.5">
            <span className="mt-0.5 shrink-0 text-amber-400">⚠</span>
            <p className="text-sm font-medium text-amber-200">
              {selectedWeek.note}
            </p>
          </div>
        )}

        {/* Task list */}
        <div className="flex flex-col gap-2">
          {selectedWeek.tasks.map((task) => (
            <TaskRow
              key={task.id}
              task={task}
              done={!!done[task.id]}
              onToggle={toggleTask}
            />
          ))}
        </div>
      </Panel>

      {/* ── Side Info ───────────────────────────────────────────────────── */}
      <div className="md:col-span-5 flex flex-col gap-4">
        {/* Tracking targets */}
        {selectedWeek.tracking && (
          <Panel title="Suivi Crests" subtitle={selectedWeek.title}>
            <div className="rounded-lg border border-border/50 bg-muted/30 px-4 py-3">
              <p className="font-mono text-sm text-foreground">
                {selectedWeek.tracking}
              </p>
            </div>
          </Panel>
        )}

        {/* Ending item level */}
        {selectedWeek.endingIlvl && (
          <Panel title="Item Level cible" subtitle="En fin de semaine">
            <div className="rounded-lg border border-border/50 bg-muted/30 px-4 py-3">
              <p className="text-sm text-muted-foreground leading-relaxed">
                {selectedWeek.endingIlvl
                  .split("·")
                  .map((s) => s.trim())
                  .join("\n")}
              </p>
            </div>
          </Panel>
        )}

        {/* All-weeks summary */}
        <Panel title="Vue planning" subtitle="Toutes les semaines">
          <div className="flex flex-col gap-1.5">
            {WEEKS.map((w) => {
              const wDone = w.tasks.filter((t) => done[t.id]).length;
              const wTotal = w.tasks.length;
              const pct =
                wTotal === 0 ? 0 : Math.round((wDone / wTotal) * 100);
              const isCurrent = w.id === currentWeek?.id;
              const isSelected = w.id === selectedId;

              return (
                <button
                  key={w.id}
                  onClick={() => setSelectedId(w.id)}
                  className={[
                    "flex items-center gap-3 rounded-lg border px-3 py-2 text-left transition-all",
                    isSelected
                      ? "border-primary/40 bg-primary/8"
                      : "border-border/40 bg-card/30 hover:border-border",
                  ].join(" ")}
                >
                  {/* active dot */}
                  <span
                    className={[
                      "h-2 w-2 shrink-0 rounded-full",
                      isCurrent ? "bg-emerald-400" : "bg-transparent border border-border",
                    ].join(" ")}
                  />

                  <span className="flex-1 min-w-0">
                    <span
                      className={[
                        "block text-xs truncate",
                        isSelected
                          ? "text-foreground"
                          : "text-muted-foreground",
                      ].join(" ")}
                    >
                      {w.title}
                    </span>
                    <span className="block text-[10px] text-muted-foreground/60 truncate">
                      {fmtDate(w.startDate)}
                      {w.endDate ? ` – ${fmtDate(w.endDate)}` : "+"}
                    </span>
                  </span>

                  {/* mini progress */}
                  <span
                    className={[
                      "shrink-0 text-[10px] tabular-nums",
                      pct === 100
                        ? "text-emerald-400"
                        : "text-muted-foreground",
                    ].join(" ")}
                  >
                    {wDone}/{wTotal}
                  </span>
                </button>
              );
            })}
          </div>
        </Panel>
      </div>
    </div>
  );
}

export default ActivitiesPage;
