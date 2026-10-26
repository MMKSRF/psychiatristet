import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createRootRoute, createRoute, createRouter, lazyRouteComponent, Outlet, redirect, RouterProvider } from "@tanstack/react-router";
import { Activity, LogOut, Moon, ShieldCheck, Stethoscope, Sun } from "lucide-react";
import { api } from "./api";
import { useSession } from "./store";
import { ThemeProvider, useTheme } from "./theme";
import { Button, Card } from "./ui";
import "./styles.css";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: true } },
});

function Shell() {
  const user = useSession((state) => state.user);
  const clearSession = useSession((state) => state.clearSession);
  const { theme, toggleTheme } = useTheme();
  return (
    <div className="min-h-screen bg-canvas text-ink dark:bg-slate-950 dark:text-white">
      <header className="sticky top-0 z-20 border-b border-slate-200/80 bg-white/90 backdrop-blur dark:border-slate-800 dark:bg-slate-950/90">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-xl bg-teal-600 text-white"><Activity size={20} /></div>
            <div><div className="font-bold tracking-tight">CareBridge</div><div className="text-xs text-muted dark:text-slate-400">Clinical workspace</div></div>
          </div>
          <div className="flex items-center gap-2">
            {user && <span className="hidden items-center gap-2 rounded-full bg-slate-100 px-3 py-2 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300 sm:flex">{user.role === "Admin" ? <ShieldCheck size={15} /> : <Stethoscope size={15} />}{user.username}</span>}
            <Button variant="ghost" className="px-3" onClick={toggleTheme} aria-label="Toggle color theme">{theme === "light" ? <Moon size={18} /> : <Sun size={18} />}</Button>
            {user && <Button variant="ghost" className="px-3" onClick={() => { clearSession(); window.location.href = "/login"; }} aria-label="Sign out"><LogOut size={18} /></Button>}
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-5 py-8"><Outlet /></main>
      <footer className="mx-auto max-w-7xl px-5 pb-8 text-center text-xs text-slate-400">CareBridge MVP · Handle patient information only in accordance with your organization’s privacy policies.</footer>
    </div>
  );
}

function signedIn() {
  if (!useSession.getState().user) throw redirect({ to: "/login" });
}

const rootRoute = createRootRoute({ component: Shell });
const loginRoute = createRoute({ getParentRoute: () => rootRoute, path: "/login", component: lazyRouteComponent(() => import("./pages/LoginPage"), "LoginPage") });
const adminRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/admin",
  beforeLoad: () => { signedIn(); if (useSession.getState().user?.role !== "Admin") throw redirect({ to: "/psychiatrist/dashboard" }); },
  component: lazyRouteComponent(() => import("./pages/AdminDashboard"), "AdminDashboard"),
});
const psychiatristRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/psychiatrist/dashboard",
  beforeLoad: () => { signedIn(); if (useSession.getState().user?.role !== "Psychiatrist") throw redirect({ to: "/admin" }); },
  component: lazyRouteComponent(() => import("./pages/PsychiatristDashboard"), "PsychiatristDashboard"),
});
const chatRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/psychiatrist/chat/$patientId",
  beforeLoad: () => { signedIn(); if (useSession.getState().user?.role !== "Psychiatrist") throw redirect({ to: "/admin" }); },
  component: lazyRouteComponent(() => import("./pages/ChatPage"), "ChatPage"),
});
const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  beforeLoad: () => {
    const user = useSession.getState().user;
    throw redirect({ to: !user ? "/login" : user.role === "Admin" ? "/admin" : "/psychiatrist/dashboard" });
  },
});
const routeTree = rootRoute.addChildren([indexRoute, loginRoute, adminRoute, psychiatristRoute, chatRoute]);
const router = createRouter({ routeTree });

window.addEventListener("carebridge:unauthorized", () => {
  queryClient.clear();
  router.navigate({ to: "/login" });
});

function App() {
  return <ThemeProvider><QueryClientProvider client={queryClient}><RouterProvider router={router} /></QueryClientProvider></ThemeProvider>;
}

ReactDOM.createRoot(document.getElementById("root")).render(<React.StrictMode><App /></React.StrictMode>);
