import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { HeartHandshake, LockKeyhole } from "lucide-react";
import { useState } from "react";
import { api } from "../api";
import { useLang } from "../i18n";
import { useSession } from "../store";
import { Button, Card, Input } from "../ui";

export function LoginPage() {
  const navigate = useNavigate();
  const setSession = useSession((state) => state.setSession);
  const { t } = useLang();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const login = useMutation({
    mutationFn: async () => (await api.post("/api/auth/login", { username, password })).data,
    onSuccess: ({ access_token: token, user }) => {
      setSession(token, user);
      navigate({ to: user.must_change_password ? "/change-password" : user.role === "Admin" ? "/admin" : "/psychiatrist/dashboard" });
    },
  });
  return (
    <div className="grid min-h-[72vh] place-items-center">
      <Card className="w-full max-w-md p-8 sm:p-10">
        <div className="mb-8 grid h-12 w-12 place-items-center rounded-2xl bg-teal-50 text-teal-700 dark:bg-teal-950 dark:text-teal-300">
          <HeartHandshake size={24} />
        </div>
        <p className="mb-2 text-xs font-bold uppercase tracking-[.16em] text-teal-700 dark:text-teal-300">
          {t("secureSignIn")}
        </p>
        <h1 className="mb-2 text-3xl font-bold tracking-tight">{t("welcomeBack")}</h1>
        <p className="mb-8 text-sm leading-6 text-muted dark:text-slate-400">{t("loginHint")}</p>
        <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); login.mutate(); }}>
          <label className="block space-y-2 text-sm font-medium">
            {t("usernameLabel")}
            <Input
              autoComplete="username"
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck={false}
              placeholder={t("usernamePlaceholder")}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </label>
          <label className="block space-y-2 text-sm font-medium">
            {t("passwordLabel")}
            <Input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>
          {login.isError && (
            <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">
              {login.error.response?.data?.detail || t("loginError")}
            </p>
          )}
          <Button type="submit" disabled={login.isPending} className="w-full py-3">
            <LockKeyhole size={16} />
            {login.isPending ? t("signingIn") : t("signIn")}
          </Button>
        </form>
      </Card>
    </div>
  );
}
