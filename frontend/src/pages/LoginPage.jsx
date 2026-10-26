import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { HeartHandshake, LockKeyhole } from "lucide-react";
import { useState } from "react";
import { api } from "../api";
import { useSession } from "../store";
import { Button, Card, Input } from "../ui";

export function LoginPage() {
  const navigate = useNavigate();
  const setSession = useSession((state) => state.setSession);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const login = useMutation({
    mutationFn: async () => (await api.post("/api/auth/login", { username, password })).data,
    onSuccess: ({ access_token: token, user }) => {
      setSession(token, user);
      navigate({ to: user.role === "Admin" ? "/admin" : "/psychiatrist/dashboard" });
    },
  });
  return (
    <div className="grid min-h-[72vh] place-items-center">
      <Card className="w-full max-w-md p-8 sm:p-10">
        <div className="mb-8 grid h-12 w-12 place-items-center rounded-2xl bg-teal-50 text-teal-700 dark:bg-teal-950 dark:text-teal-300"><HeartHandshake size={24} /></div>
        <p className="mb-2 text-xs font-bold uppercase tracking-[.16em] text-teal-700 dark:text-teal-300">Secure sign in</p>
        <h1 className="mb-2 text-3xl font-bold tracking-tight">Welcome back</h1>
        <p className="mb-8 text-sm leading-6 text-muted dark:text-slate-400">Sign in with the account configured for your clinical role.</p>
        <form className="space-y-4" onSubmit={(event) => { event.preventDefault(); login.mutate(); }}>
          <label className="block space-y-2 text-sm font-medium">Username<Input autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} required /></label>
          <label className="block space-y-2 text-sm font-medium">Password<Input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label>
          {login.isError && <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">{login.error.response?.data?.detail || "Could not sign in. Check the server and credentials."}</p>}
          <Button type="submit" disabled={login.isPending} className="w-full py-3"><LockKeyhole size={16} />{login.isPending ? "Signing in…" : "Sign in"}</Button>
        </form>
      </Card>
    </div>
  );
}
