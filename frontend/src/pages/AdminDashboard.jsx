import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowUpRight, ClipboardList, Users } from "lucide-react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { api } from "../api";
import { Button, Card, Status } from "../ui";

const colors = ["#3d9386", "#e9b872", "#8091a0"];

export function AdminDashboard() {
  const client = useQueryClient();
  const pending = useQuery({ queryKey: ["pending-patients"], queryFn: async () => (await api.get("/api/admin/pending-patients")).data });
  const clinicians = useQuery({ queryKey: ["psychiatrists"], queryFn: async () => (await api.get("/api/admin/psychiatrists")).data });
  const assign = useMutation({
    mutationFn: ({ telegram_id, psychiatrist_id }) => api.post("/api/admin/assign-case", { telegram_id, psychiatrist_id }),
    onSuccess: () => { client.invalidateQueries({ queryKey: ["pending-patients"] }); client.invalidateQueries({ queryKey: ["psychiatrists"] }); },
  });
  const counts = (clinicians.data || []).reduce((result, person) => {
    result[person.status] = (result[person.status] || 0) + 1;
    return result;
  }, {});
  const chartData = Object.entries(counts).map(([name, value]) => ({ name, value }));
  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div><p className="mb-2 text-xs font-bold uppercase tracking-[.16em] text-teal-700 dark:text-teal-300">Operations overview</p><h1 className="text-3xl font-bold tracking-tight sm:text-4xl">Patient assignments</h1><p className="mt-2 text-sm text-muted dark:text-slate-400">Review new intakes and connect patients with available clinicians.</p></div>
        <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-muted dark:border-slate-700 dark:bg-slate-900">Updated automatically · refresh to sync</div>
      </div>
      {(pending.isError || clinicians.isError) && <p role="alert" className="rounded-xl bg-red-50 p-4 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">Could not load dashboard data. {pending.error?.response?.data?.detail || clinicians.error?.response?.data?.detail || "Check the API connection."}</p>}
      <div className="grid gap-5 lg:grid-cols-[1fr_330px]">
        <Card className="overflow-hidden">
          <div className="flex items-center justify-between border-b border-slate-100 px-6 py-5 dark:border-slate-800"><div><h2 className="font-bold">Intake queue</h2><p className="mt-1 text-sm text-muted dark:text-slate-400">{pending.data?.length ?? "—"} awaiting assignment</p></div><ClipboardList className="text-teal-600" /></div>
          {pending.isPending ? <div className="p-8 text-sm text-muted">Loading intakes…</div> : pending.data?.length ? <div className="overflow-x-auto"><table className="w-full min-w-[680px] text-left text-sm"><thead className="bg-slate-50 text-xs uppercase tracking-wide text-muted dark:bg-slate-800/60"><tr><th className="px-6 py-3">Patient</th><th className="px-6 py-3">Age</th><th className="px-6 py-3">Concern</th><th className="px-6 py-3">Assign clinician</th></tr></thead><tbody className="divide-y divide-slate-100 dark:divide-slate-800">{pending.data.map((patient) => <tr key={patient.telegram_id} className="align-top"><td className="px-6 py-4"><div className="font-semibold">{patient.name}</div><div className="mt-1 text-xs text-muted">{patient.telegram_username ? `@${patient.telegram_username}` : "Telegram patient"}</div><div className="mt-2"><Status>{patient.status}</Status></div></td><td className="px-6 py-4">{patient.age}</td><td className="max-w-xs px-6 py-4 leading-6 text-slate-600 dark:text-slate-300">{patient.complaint}</td><td className="px-6 py-4"><select aria-label={`Assign ${patient.name}`} className="w-full rounded-lg border border-slate-200 bg-white p-2 text-sm dark:border-slate-700 dark:bg-slate-800" defaultValue="" onChange={(event) => { if (event.target.value) assign.mutate({ telegram_id: patient.telegram_id, psychiatrist_id: Number(event.target.value) }); }} disabled={assign.isPending}><option value="" disabled>Choose clinician…</option>{clinicians.data?.map((person) => <option key={person.psychiatrist_id} value={person.psychiatrist_id}>{person.full_name} · {person.field} ({person.status})</option>)}</select>{assign.isError && <span className="mt-2 block text-xs text-red-600">{assign.error.response?.data?.detail || "Assignment failed."}</span>}</td></tr>)}</tbody></table></div> : <div className="px-6 py-14 text-center"><div className="mx-auto mb-3 grid h-12 w-12 place-items-center rounded-2xl bg-teal-50 text-teal-700 dark:bg-teal-950 dark:text-teal-300"><Users size={21} /></div><p className="font-semibold">No pending intakes</p><p className="mt-1 text-sm text-muted dark:text-slate-400">New Telegram intakes will appear here.</p></div>}
        </Card>
        <Card className="p-6"><div className="flex items-center justify-between"><div><h2 className="font-bold">Clinician capacity</h2><p className="mt-1 text-sm text-muted dark:text-slate-400">Current roster availability</p></div><ArrowUpRight size={18} className="text-teal-600" /></div>{chartData.length ? <div className="mt-4 h-52"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={chartData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={80} paddingAngle={4}>{chartData.map((entry, index) => <Cell key={entry.name} fill={colors[index % colors.length]} />)}</Pie><Tooltip /></PieChart></ResponsiveContainer></div> : <div className="grid h-52 place-items-center text-sm text-muted">No clinician data</div>}<div className="space-y-3">{(clinicians.data || []).map((person) => <div key={person.psychiatrist_id} className="flex items-center justify-between border-t border-slate-100 pt-3 text-sm dark:border-slate-800"><div><div className="font-medium">{person.full_name}</div><div className="text-xs text-muted dark:text-slate-400">{person.field}</div></div><Status>{person.status}</Status></div>)}</div></Card>
      </div>
    </div>
  );
}
