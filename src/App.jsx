import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate, useLocation } from "react-router-dom";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/warcraftcn/dropdown-menu";
import { Button } from "@/components/ui/warcraftcn/button";
import { mockData } from "@/data/mockData";
import {
  useAccounts,
  useDefaultAccount,
  useAuthStatus,
  useBlizzardLogin,
  useSyncAccount,
} from "@/hooks/useWow";

const navLinkClass = ({ isActive }) =>
  [
    "px-4 py-2 text-sm",
    isActive
      ? "shadow-inner ring-2 ring-primary/40 brightness-90"
      : "opacity-90 hover:brightness-110",
  ].join(" ");

function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const [syncMessage, setSyncMessage] = useState(null);

  const { data: defaultAccount } = useDefaultAccount();
  const { data: accounts } = useAccounts();

  const accountId = defaultAccount?.id ?? null;
  const accountName = defaultAccount?.name ?? mockData.account.name;
  const accountRealm = defaultAccount?.realm ?? mockData.account.realm;

  const { data: authStatus, refetch: refetchAuthStatus } = useAuthStatus(accountId);
  const { login } = useBlizzardLogin();
  const { syncAccount, loading: syncing } = useSyncAccount((result) => {
    setSyncMessage(
      result?.synced != null
        ? `${result.synced}/${result.total} persos synchronisés`
        : "Sync terminé"
    );
    setTimeout(() => setSyncMessage(null), 4000);
  });

  // Après le callback OAuth Blizzard : ?sync_success=1&account_id=X
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    if (params.get("sync_success") && params.get("account_id")) {
      const id = parseInt(params.get("account_id"), 10);
      // Nettoie l'URL
      navigate(location.pathname, { replace: true });
      // Lance la sync automatiquement
      refetchAuthStatus();
      syncAccount(id);
    }
    if (params.get("sync_error")) {
      setSyncMessage("Échec connexion Blizzard");
      setTimeout(() => setSyncMessage(null), 4000);
      navigate(location.pathname, { replace: true });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const isBlizzardConnected = authStatus?.is_connected ?? false;

  function handleSyncClick() {
    if (!accountId) return;
    if (isBlizzardConnected) {
      syncAccount(accountId);
    } else {
      login(accountId);
    }
  }

  return (
    <div className="dashboard-shell">
      {syncMessage && (
        <div className="fixed top-4 right-4 z-50 rounded border border-primary/40 bg-background/90 px-4 py-2 text-sm text-foreground shadow-lg backdrop-blur">
          {syncMessage}
        </div>
      )}
      <header className="flex flex-wrap lg:flex-nowrap items-center justify-between gap-3 py-4">
        <div>
          <p className="text-xs uppercase tracking-[0.35em] text-primary">
            {accountRealm}
          </p>
          <h1 className="text-3xl text-foreground">WoW Progress Hub</h1>
          <p className="text-sm text-muted-foreground">
            Progression et economie sans scroll infini.
          </p>
        </div>
        <nav className="flex flex-wrap items-center gap-2 lg:gap-1">
          <Button asChild>
            <NavLink to="/" end className={navLinkClass}>
              Dashboard
            </NavLink>
          </Button>
          <Button asChild>
            <NavLink to="/personnages" className={navLinkClass}>
              Personnages
            </NavLink>
          </Button>
          <Button asChild>
            <NavLink to="/guilde" className={navLinkClass}>
              Guilde
            </NavLink>
          </Button>
          <Button asChild>
            <NavLink to="/crafting" className={navLinkClass}>
              Crafting
            </NavLink>
          </Button>
          <Button asChild>
            <NavLink to="/economie" className={navLinkClass}>
              Economie
            </NavLink>
          </Button>
          <Button asChild>
            <NavLink to="/todos" className={navLinkClass}>
              Todos
            </NavLink>
          </Button>
          <Button asChild>
            <NavLink to="/activites" className={navLinkClass}>
              Activites
            </NavLink>
          </Button>
        </nav>
        <div className="flex flex-wrap items-center gap-3">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="frame">Compte: {accountName}</Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>Comptes</DropdownMenuLabel>
              {(accounts ?? [mockData.account]).map((acc) => (
                <DropdownMenuItem key={acc.id ?? acc.name}>
                  {acc.name}
                  {acc.is_default ? " ✓" : ""}
                </DropdownMenuItem>
              ))}
              <DropdownMenuSeparator />
              <DropdownMenuItem>Ajouter un compte</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          <Button onClick={handleSyncClick} disabled={syncing || !accountId}>
              {syncing
                ? "Synchronisation..."
                : isBlizzardConnected
                ? "Sync Blizzard"
                : "Connecter Blizzard"}
            </Button>
        </div>
      </header>

      <Outlet />
    </div>
  );
}

export default App;
