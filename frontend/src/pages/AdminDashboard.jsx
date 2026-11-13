import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, ArrowUpRight, ClipboardList, Plus, Users } from "lucide-react";
import { useState } from "react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { api } from "../api";
import { useLang } from "../i18n";
import { Button, Card, Input, Status } from "../ui";

const colors = ["#3d9386", "#e9b872", "#8091a0"];

export function AdminDashboard() {
  const [section, setSection] = useState("assignments");
  const [error, setError] = useState("");
  const { t } = useLang();
  const client = useQueryClient();
  const pending = useQuery({ queryKey: ["pending-patients"], queryFn: async () => (await api.get("/api/admin/pending-patients")).data });
  const advisers = useQuery({ queryKey: ["psychiatrists"], queryFn: async () => (await api.get("/api/admin/psychiatrists")).data });
  const assign = useMutation({
    mutationFn: ({ telegram_id, psychiatrist_id }) => api.post("/api/admin/assign-case", { telegram_id, psychiatrist_id }),
    onSuccess: () => {
      setError("");
      client.invalidateQueries({ queryKey: ["pending-patients"] });
      client.invalidateQueries({ queryKey: ["psychiatrists"] });
    },
    onError: (issue) => setError(issue.response?.data?.detail || t("assignmentFailed")),
  });
  const counts = (advisers.data || []).reduce((result, person) => {
    result[person.status] = (result[person.status] || 0) + 1;
    return result;
  }, {});
  const chartData = Object.entries(counts).map(([name, value]) => ({ name, value }));

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="mb-2 text-xs font-bold uppercase tracking-[.16em] text-teal-700 dark:text-teal-300">{t("operationsOverview")}</p>
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">{t("adminManagement")}</h1>
          <p className="mt-2 text-sm text-muted dark:text-slate-400">{t("adminSubtitle")}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-muted dark:border-slate-700 dark:bg-slate-900">
          {t("careTeam")} · {advisers.data?.length ?? "—"} {t("advisers")}
        </div>
      </div>

      <nav aria-label="Admin sections" className="flex flex-wrap gap-2 border-b border-slate-200 pb-3 dark:border-slate-800">
        <SectionButton active={section === "assignments"} onClick={() => setSection("assignments")}><ClipboardList size={16} />{t("tabAssignments")}</SectionButton>
        <SectionButton active={section === "psychiatrists"} onClick={() => setSection("psychiatrists")}><Users size={16} />{t("tabAdvisers")}</SectionButton>
        <SectionButton active={section === "activity"} onClick={() => setSection("activity")}><Activity size={16} />{t("tabActivity")}</SectionButton>
      </nav>

      {(pending.isError || advisers.isError) && <ErrorNotice>{pending.error?.response?.data?.detail || advisers.error?.response?.data?.detail || t("errorLoadingDashboard")}</ErrorNotice>}

      {section === "assignments" && (
        <div className="grid gap-5 lg:grid-cols-[1fr_330px]">
          <Card className="overflow-hidden">
            <div className="flex items-center justify-between border-b border-slate-100 px-6 py-5 dark:border-slate-800">
              <div>
                <h2 className="font-bold">{t("intakeQueue")}</h2>
                <p className="mt-1 text-sm text-muted dark:text-slate-400">{pending.data?.length ?? "—"} {t("awaitingAssignment")}</p>
              </div>
              <ClipboardList className="text-teal-600" />
            </div>
            {pending.isPending ? (
              <div className="p-8 text-sm text-muted">{t("loadingIntakes")}</div>
            ) : pending.data?.length ? (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[680px] text-left text-sm">
                  <thead className="bg-slate-50 text-xs uppercase tracking-wide text-muted dark:bg-slate-800/60">
                    <tr>
                      <th className="px-6 py-3">{t("colUser")}</th>
                      <th className="px-6 py-3">{t("colAge")}</th>
                      <th className="px-6 py-3">{t("colConcern")}</th>
                      <th className="px-6 py-3">{t("colAssignAdviser")}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {pending.data.map((user) => (
                      <tr key={user.telegram_id} className="align-top">
                        <td className="px-6 py-4">
                          <div className="font-semibold">{user.name}</div>
                          <div className="mt-1 text-xs text-muted">{user.telegram_username ? `@${user.telegram_username}` : t("telegramUser")}</div>
                          <div className="mt-2"><Status>{user.status}</Status></div>
                        </td>
                        <td className="px-6 py-4">{user.age}</td>
                        <td className="max-w-xs px-6 py-4 leading-6 text-slate-600 dark:text-slate-300">{user.complaint}</td>
                        <td className="px-6 py-4">
                          <select
                            aria-label={`Assign ${user.name}`}
                            className="w-full rounded-lg border border-slate-200 bg-white p-2 text-sm dark:border-slate-700 dark:bg-slate-800"
                            defaultValue=""
                            onChange={(e) => { if (e.target.value) assign.mutate({ telegram_id: user.telegram_id, psychiatrist_id: Number(e.target.value) }); }}
                            disabled={assign.isPending}
                          >
                            <option value="" disabled>{t("chooseAdviser")}</option>
                            {advisers.data?.map((adviser) => {
                              const available = adviser.assigned_patient_count < adviser.max_patients && !["Inactive", "Offline"].includes(adviser.status);
                              return (
                                <option key={adviser.psychiatrist_id} value={adviser.psychiatrist_id} disabled={!available}>
                                  {adviser.full_name} · {adviser.assigned_patient_count}/{adviser.max_patients}{available ? "" : " · at capacity"}
                                </option>
                              );
                            })}
                          </select>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState icon={<Users size={21} />} title={t("noIntakeYet")} description={t("noIntakeDesc")} />
            )}
            {error && <div className="px-6 pb-5"><ErrorNotice>{error}</ErrorNotice></div>}
          </Card>

          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="font-bold">{t("advisersSection")}</h2>
                <p className="mt-1 text-sm text-muted dark:text-slate-400">{t("advisersSectionDesc")}</p>
              </div>
              <ArrowUpRight size={18} className="text-teal-600" />
            </div>
            {chartData.length ? (
              <div className="mt-4 h-52">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={chartData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={80} paddingAngle={4}>
                      {chartData.map((entry, index) => <Cell key={entry.name} fill={colors[index % colors.length]} />)}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="grid h-52 place-items-center text-sm text-muted">{t("loadingDashboard")}</div>
            )}
            <div className="space-y-3">
              {(advisers.data || []).map((adviser) => (
                <div key={adviser.psychiatrist_id} className="flex items-center justify-between border-t border-slate-100 pt-3 text-sm dark:border-slate-800">
                  <div>
                    <div className="font-medium">{adviser.full_name}</div>
                    <div className="text-xs text-muted dark:text-slate-400">{adviser.assigned_patient_count}/{adviser.max_patients} {t("assignedUsers")}</div>
                  </div>
                  <Status>{adviser.status}</Status>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      {section === "psychiatrists" && <AdviserManagement advisers={advisers.data || []} isLoading={advisers.isPending} />}
      {section === "activity" && <InteractionActivity />}
    </div>
  );
}

function AdviserManagement({ advisers, isLoading }) {
  const { t } = useLang();
  const client = useQueryClient();
  const [selectedId, setSelectedId] = useState(null);
  const [message, setMessage] = useState("");
  const createProfile = useMutation({
    mutationFn: (form) => api.post("/api/admin/psychiatrists", form),
    onSuccess: () => {
      setMessage("Adviser account created! Share the initial password securely — they'll need to change it on first sign-in.");
      client.invalidateQueries({ queryKey: ["psychiatrists"] });
    },
    onError: (error) => setMessage(error.response?.data?.detail || "Could not create the account."),
  });
  return (
    <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_390px]">
      <Card className="overflow-hidden">
        <div className="border-b border-slate-100 px-6 py-5 dark:border-slate-800">
          <h2 className="font-bold">{t("advisersSection")}</h2>
          <p className="mt-1 text-sm text-muted dark:text-slate-400">{t("advisersSectionDesc")}</p>
        </div>
        {isLoading ? (
          <div className="p-8 text-sm text-muted">{t("loadingUsers")}</div>
        ) : advisers.length ? (
          <div className="divide-y divide-slate-100 dark:divide-slate-800">
            {advisers.map((adviser) => (
              <AdviserRow
                key={adviser.psychiatrist_id}
                adviser={adviser}
                expanded={selectedId === adviser.psychiatrist_id}
                onToggle={() => setSelectedId(selectedId === adviser.psychiatrist_id ? null : adviser.psychiatrist_id)}
              />
            ))}
          </div>
        ) : (
          <EmptyState icon={<Users size={21} />} title={t("noIntakeYet")} description={t("noIntakeDesc")} />
        )}
      </Card>
      <Card className="p-6">
        <div className="mb-5">
          <h2 className="font-bold">Add adviser</h2>
          <p className="mt-1 text-sm leading-6 text-muted dark:text-slate-400">
            They'll sign in using their email and this initial password, then set a new one.
          </p>
        </div>
        <form className="space-y-4" onSubmit={(e) => {
          e.preventDefault();
          const form = new FormData(e.currentTarget);
          createProfile.mutate({
            full_name: String(form.get("full_name")),
            email: String(form.get("email")),
            field: String(form.get("field")),
            initial_password: String(form.get("initial_password")),
          });
          e.currentTarget.reset();
        }}>
          <label className="block space-y-2 text-sm font-medium">Full name<Input name="full_name" autoComplete="name" maxLength={200} required /></label>
          <label className="block space-y-2 text-sm font-medium">Email<Input name="email" type="email" autoComplete="email" maxLength={254} required /></label>
          <label className="block space-y-2 text-sm font-medium">Specialty<Input name="field" maxLength={200} placeholder="e.g. Mental health counselling" required /></label>
          <label className="block space-y-2 text-sm font-medium">
            Initial password
            <Input name="initial_password" type="password" autoComplete="new-password" minLength={12} maxLength={128} required />
            <span className="block text-xs font-normal text-muted dark:text-slate-400">At least 12 characters. Share via a secure channel.</span>
          </label>
          {message && <p role="status" className={`rounded-xl p-3 text-sm ${createProfile.isError ? "bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300" : "bg-teal-50 text-teal-800 dark:bg-teal-950 dark:text-teal-200"}`}>{message}</p>}
          <Button type="submit" disabled={createProfile.isPending} className="w-full">
            <Plus size={16} />{createProfile.isPending ? "Creating…" : "Create account"}
          </Button>
        </form>
      </Card>
    </div>
  );
}

function AdviserRow({ adviser, expanded, onToggle }) {
  const { t } = useLang();
  const client = useQueryClient();
  const [capacity, setCapacity] = useState(String(adviser.max_patients));
  const [notice, setNotice] = useState("");
  const users = useQuery({
    queryKey: ["admin-psychiatrist-patients", adviser.psychiatrist_id],
    queryFn: async () => (await api.get(`/api/admin/psychiatrists/${adviser.psychiatrist_id}/patients`)).data,
    enabled: expanded,
  });
  const updateCapacity = useMutation({
    mutationFn: () => api.patch(`/api/admin/psychiatrists/${adviser.psychiatrist_id}/capacity`, { max_patients: Number(capacity) }),
    onSuccess: () => {
      setNotice("Limit saved.");
      client.invalidateQueries({ queryKey: ["psychiatrists"] });
    },
    onError: (error) => setNotice(error.response?.data?.detail || "Could not update limit."),
  });
  return (
    <article className="px-6 py-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-48">
          <h3 className="font-semibold">{adviser.full_name}</h3>
          <p className="mt-1 text-sm text-muted dark:text-slate-400">{adviser.email || adviser.username}</p>
          <p className="mt-1 text-xs text-muted dark:text-slate-400">{adviser.field}</p>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Status>{adviser.status}</Status>
            <span className="text-xs text-muted dark:text-slate-400">{adviser.assigned_patient_count} {t("assigned")} · ID {adviser.psychiatrist_id}</span>
          </div>
        </div>
        <div className="flex flex-wrap items-end gap-2">
          <label className="text-xs font-medium text-muted dark:text-slate-400">
            {t("caseLimit")}
            <Input
              aria-label={`User limit for ${adviser.full_name}`}
              type="number" min="0" max="1000"
              value={capacity}
              onChange={(e) => setCapacity(e.target.value)}
              className="mt-1 w-24"
            />
          </label>
          <Button variant="secondary" disabled={updateCapacity.isPending || capacity === String(adviser.max_patients) || !/^\d+$/.test(capacity)} onClick={() => updateCapacity.mutate()}>
            {updateCapacity.isPending ? t("savingLimit") : t("saveLimit")}
          </Button>
          <Button variant="ghost" onClick={onToggle}>{expanded ? t("hideUsers") : t("viewUsers")}</Button>
        </div>
      </div>
      {notice && <p role="status" className={`mt-3 text-xs ${updateCapacity.isError ? "text-red-700 dark:text-red-300" : "text-teal-700 dark:text-teal-300"}`}>{notice}</p>}
      {adviser.must_change_password && <p className="mt-3 text-xs text-amber-700 dark:text-amber-300">{t("waitingFirstLogin")}</p>}
      {expanded && (
        <div className="mt-5 rounded-xl bg-slate-50 p-4 dark:bg-slate-800/60">
          <h4 className="text-sm font-semibold">{t("assignedUsers")}</h4>
          {users.isPending ? (
            <p className="mt-3 text-sm text-muted">{t("loadingUsers")}</p>
          ) : users.isError ? (
            <p role="alert" className="mt-3 text-sm text-red-700 dark:text-red-300">{users.error.response?.data?.detail || "Could not load users."}</p>
          ) : users.data?.length ? (
            <ul className="mt-3 divide-y divide-slate-200 dark:divide-slate-700">
              {users.data.map((user) => (
                <li key={user.telegram_id} className="py-3 first:pt-0 last:pb-0">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-sm font-medium">{user.name}</span>
                    <span className="text-xs text-muted dark:text-slate-400">{user.age} {t("yearsOld")} · {user.telegram_id}</span>
                  </div>
                  <p className="mt-1 text-xs leading-5 text-muted dark:text-slate-400">{user.complaint}</p>
                  <p className="mt-1 text-[11px] text-slate-400">
                    {t("assigned")} {user.assigned_at ? new Date(user.assigned_at).toLocaleDateString() : t("dateUnavailable")}
                  </p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-sm text-muted dark:text-slate-400">{t("noUsersAssigned")}</p>
          )}
        </div>
      )}
    </article>
  );
}

function InteractionActivity() {
  const { t } = useLang();
  const activity = useQuery({
    queryKey: ["admin-interaction-logs"],
    queryFn: async () => (await api.get("/api/admin/interaction-logs")).data,
  });
  return (
    <Card className="overflow-hidden">
      <div className="border-b border-slate-100 px-6 py-5 dark:border-slate-800">
        <h2 className="font-bold">{t("interactionActivity")}</h2>
        <p className="mt-1 text-sm text-muted dark:text-slate-400">{t("activityDesc")}</p>
      </div>
      {activity.isPending ? (
        <div className="p-8 text-sm text-muted">{t("loadingDashboard")}</div>
      ) : activity.isError ? (
        <div className="p-6"><ErrorNotice>{activity.error.response?.data?.detail || t("errorLoadingDashboard")}</ErrorNotice></div>
      ) : activity.data?.length ? (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[680px] text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-muted dark:bg-slate-800/60">
              <tr>
                <th className="px-6 py-3">{t("colUser")}</th>
                <th className="px-6 py-3">{t("colAdviserName")}</th>
                <th className="px-6 py-3">{t("colMessages")}</th>
                <th className="px-6 py-3">{t("colUserAdviser")}</th>
                <th className="px-6 py-3">{t("colLatest")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {activity.data.map((item) => (
                <tr key={`${item.telegram_id}-${item.psychiatrist_id}`}>
                  <td className="px-6 py-4">
                    <div className="font-medium">{item.patient_name}</div>
                    <div className="text-xs text-muted">{item.telegram_id}</div>
                  </td>
                  <td className="px-6 py-4">{item.psychiatrist_name}</td>
                  <td className="px-6 py-4">{item.message_count}</td>
                  <td className="px-6 py-4">{item.patient_message_count} / {item.psychiatrist_message_count}</td>
                  <td className="px-6 py-4 text-muted dark:text-slate-400">{item.last_message_at ? new Date(item.last_message_at).toLocaleString() : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState icon={<Activity size={21} />} title={t("noActivityYet")} description={t("noActivityDesc")} />
      )}
    </Card>
  );
}

function SectionButton({ active, children, ...props }) {
  return <Button type="button" variant={active ? "primary" : "secondary"} className="px-3 py-2" {...props}>{children}</Button>;
}

function ErrorNotice({ children }) {
  return <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">{children}</p>;
}

function EmptyState({ icon, title, description }) {
  return (
    <div className="px-6 py-14 text-center">
      <div className="mx-auto mb-3 grid h-12 w-12 place-items-center rounded-2xl bg-teal-50 text-teal-700 dark:bg-teal-950 dark:text-teal-300">{icon}</div>
      <p className="font-semibold">{title}</p>
      <p className="mt-1 text-sm text-muted dark:text-slate-400">{description}</p>
    </div>
  );
}
