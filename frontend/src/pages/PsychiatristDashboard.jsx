import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { ArrowUpRight, FileText, MessageCircle, Users } from "lucide-react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api";
import { useSession } from "../store";
import { Button, Card, Status } from "../ui";

export function PsychiatristDashboard() {
  const psychiatristId = useSession((state) => state.user?.psychiatrist_id);
  const patients = useQuery({
    queryKey: ["assigned-patients", psychiatristId],
    queryFn: async () => (await api.get(`/api/psychiatrist/${psychiatristId}/patients`)).data,
    refetchInterval: 15000,
  });
  const data = [{ name: "Assigned", patients: patients.data?.length || 0 }];
  return (
    <div className="space-y-8">
      <div><p className="mb-2 text-xs font-bold uppercase tracking-[.16em] text-teal-700 dark:text-teal-300">Clinical workspace</p><h1 className="text-3xl font-bold tracking-tight sm:text-4xl">Your patients</h1><p className="mt-2 text-sm text-muted dark:text-slate-400">Open a patient to continue the conversation securely.</p></div>
      {patients.isError && <p role="alert" className="rounded-xl bg-red-50 p-4 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">Could not load assigned patients. {patients.error.response?.data?.detail || "Check the API connection."}</p>}
      <div className="grid gap-5 lg:grid-cols-[1fr_320px]">
        <Card className="overflow-hidden"><div className="flex items-center justify-between border-b border-slate-100 px-6 py-5 dark:border-slate-800"><div><h2 className="font-bold">Active cases</h2><p className="mt-1 text-sm text-muted dark:text-slate-400">Assigned directly to your account</p></div><Users className="text-teal-600" /></div>
          {patients.isPending ? <div className="p-8 text-sm text-muted">Loading patients…</div> : patients.data?.length ? <div className="divide-y divide-slate-100 dark:divide-slate-800">{patients.data.map((patient) => <div key={patient.telegram_id} className="flex flex-wrap items-center justify-between gap-4 px-6 py-5"><div className="min-w-0"><div className="flex items-center gap-2"><h3 className="truncate font-semibold">{patient.name}</h3><Status>{patient.status}</Status></div><p className="mt-1 text-sm text-muted dark:text-slate-400">{patient.age} years · {patient.complaint}</p><p className="mt-2 text-xs text-slate-400">Intake {new Date(patient.created_at).toLocaleDateString()}</p></div><div className="flex gap-2"><Link to="/psychiatrist/notes/$patientId" params={{ patientId: String(patient.telegram_id) }}><Button type="button" variant="secondary"><FileText size={16} />Notes</Button></Link><Link to="/psychiatrist/chat/$patientId" params={{ patientId: String(patient.telegram_id) }}><Button type="button"><MessageCircle size={16} />Open chat</Button></Link></div></div>)}</div> : <div className="px-6 py-14 text-center"><div className="mx-auto mb-3 grid h-12 w-12 place-items-center rounded-2xl bg-teal-50 text-teal-700 dark:bg-teal-950 dark:text-teal-300"><Users size={21} /></div><p className="font-semibold">No active cases yet</p><p className="mt-1 text-sm text-muted dark:text-slate-400">New assignments will appear in your workspace.</p></div>}
        </Card>
        <Card className="p-6"><div className="flex items-center justify-between"><div><h2 className="font-bold">Case overview</h2><p className="mt-1 text-sm text-muted dark:text-slate-400">Your current workload</p></div><ArrowUpRight size={18} className="text-teal-600" /></div><div className="mt-5 h-48"><ResponsiveContainer width="100%" height="100%"><BarChart data={data} margin={{ left: -22, right: 4 }}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" /><XAxis dataKey="name" tickLine={false} axisLine={false} /><YAxis allowDecimals={false} tickLine={false} axisLine={false} /><Tooltip /><Bar dataKey="patients" fill="#3d9386" radius={[6, 6, 0, 0]} /></BarChart></ResponsiveContainer></div><div className="flex items-center gap-3 rounded-xl bg-teal-50 p-4 dark:bg-teal-950"><MessageCircle className="shrink-0 text-teal-700 dark:text-teal-300" size={18} /><p className="text-sm text-teal-900 dark:text-teal-100">Chats sync automatically every few seconds while open.</p></div></Card>
      </div>
    </div>
  );
}
