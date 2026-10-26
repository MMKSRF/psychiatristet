import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { KeyRound } from "lucide-react";
import { useState } from "react";
import { api } from "../api";
import { useSession } from "../store";
import { Button, Card, Input } from "../ui";

export function ChangePasswordPage() {
  const navigate = useNavigate();
  const setSession = useSession((state) => state.setSession);
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const changePassword = useMutation({
    mutationFn: async () => (await api.post("/api/auth/change-password", { new_password: password })).data,
    onSuccess: ({ access_token: token, user }) => {
      setSession(token, user);
      navigate({ to: "/psychiatrist/dashboard" });
    },
  });

  return (
    <div className="grid min-h-[72vh] place-items-center">
      <Card className="w-full max-w-md p-8 sm:p-10">
        <div className="mb-8 grid h-12 w-12 place-items-center rounded-2xl bg-teal-50 text-teal-700 dark:bg-teal-950 dark:text-teal-300"><KeyRound size={23} /></div>
        <p className="mb-2 text-xs font-bold uppercase tracking-[.16em] text-teal-700 dark:text-teal-300">First sign-in</p>
        <h1 className="mb-2 text-3xl font-bold tracking-tight">Create a new password</h1>
        <p className="mb-8 text-sm leading-6 text-muted dark:text-slate-400">Change your administrator-provided initial password to continue.</p>
        <form className="space-y-4" onSubmit={(event) => { event.preventDefault(); changePassword.mutate(); }}>
          <label className="block space-y-2 text-sm font-medium">New password<Input type="password" autoComplete="new-password" minLength={12} maxLength={128} value={password} onChange={(event) => setPassword(event.target.value)} required /><span className="block text-xs font-normal text-muted dark:text-slate-400">Use at least 12 characters.</span></label>
          <label className="block space-y-2 text-sm font-medium">Confirm password<Input type="password" autoComplete="new-password" minLength={12} maxLength={128} value={confirmation} onChange={(event) => setConfirmation(event.target.value)} required /></label>
          {password && confirmation && password !== confirmation && <p role="alert" className="text-sm text-red-700 dark:text-red-300">Passwords do not match.</p>}
          {changePassword.isError && <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">{changePassword.error.response?.data?.detail || "Could not update your password."}</p>}
          <Button type="submit" disabled={changePassword.isPending || password.length < 12 || password !== confirmation} className="w-full py-3">{changePassword.isPending ? "Updating…" : "Set new password"}</Button>
        </form>
      </Card>
    </div>
  );
}
