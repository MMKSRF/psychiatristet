import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "@tanstack/react-router";
import { ArrowLeft, Send } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { useSession } from "../store";
import { Button, Card, Input } from "../ui";

export function ChatPage() {
  const { patientId } = useParams({ from: "/psychiatrist/chat/$patientId" });
  const psychiatristId = useSession((state) => state.user?.psychiatrist_id);
  const queryClient = useQueryClient();
  const [text, setText] = useState("");
  const bottom = useRef(null);
  const patients = useQuery({ queryKey: ["assigned-patients", psychiatristId], queryFn: async () => (await api.get(`/api/psychiatrist/${psychiatristId}/patients`)).data });
  const patient = patients.data?.find((item) => item.telegram_id === Number(patientId));
  const messages = useQuery({
    queryKey: ["chat", patientId, psychiatristId],
    queryFn: async () => (await api.get(`/api/chat/${patientId}/${psychiatristId}`)).data,
    refetchInterval: 4000,
  });
  const send = useMutation({
    mutationFn: () => api.post("/api/chat/send", { telegram_id: Number(patientId), psychiatrist_id: psychiatristId, text }),
    onSuccess: () => { setText(""); queryClient.invalidateQueries({ queryKey: ["chat", patientId, psychiatristId] }); },
  });
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.data?.length]);
  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <Link to="/psychiatrist/dashboard" className="inline-flex items-center gap-2 text-sm font-semibold text-muted hover:text-ink dark:hover:text-white"><ArrowLeft size={16} />Back to patients</Link>
      <Card className="overflow-hidden">
        <div className="flex items-center justify-between border-b border-slate-100 px-6 py-5 dark:border-slate-800"><div><h1 className="text-lg font-bold">{patient?.name || "Patient conversation"}</h1><p className="mt-1 text-sm text-muted dark:text-slate-400">{patient ? `${patient.age} years · ${patient.telegram_username ? `@${patient.telegram_username}` : "Telegram"}` : "Loading patient…"}</p></div><div className="text-xs text-muted dark:text-slate-400">Telegram relay</div></div>
        {patient?.complaint && <div className="border-b border-slate-100 bg-slate-50 px-6 py-4 text-sm leading-6 dark:border-slate-800 dark:bg-slate-800/40"><span className="mr-2 font-semibold">Intake concern</span>{patient.complaint}</div>}
        <div className="flex h-[min(58vh,620px)] flex-col gap-3 overflow-y-auto bg-slate-50/70 px-5 py-6 dark:bg-slate-950/40 sm:px-8">
          {messages.isError && <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">Could not load this conversation.</p>}
          {messages.data?.length ? messages.data.map((message) => <div key={message.message_id} className={`max-w-[82%] rounded-2xl px-4 py-3 ${message.sender_type === "psychiatrist" ? "ml-auto rounded-br-md bg-teal-600 text-white" : "mr-auto rounded-bl-md border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800"}`}><p className="whitespace-pre-wrap text-sm leading-6">{message.text}</p><time className={`mt-1 block text-right text-[10px] ${message.sender_type === "psychiatrist" ? "text-teal-100" : "text-slate-400"}`}>{new Date(message.timestamp).toLocaleString()}</time></div>) : !messages.isPending && <div className="m-auto text-center text-sm text-muted dark:text-slate-400">No messages yet. Start the conversation below.</div>}
          <div ref={bottom} />
        </div>
        <form className="flex gap-3 border-t border-slate-100 p-4 dark:border-slate-800 sm:p-5" onSubmit={(event) => { event.preventDefault(); if (text.trim()) send.mutate(); }}>
          <Input aria-label="Message" placeholder="Write a message…" value={text} maxLength={4000} onChange={(event) => setText(event.target.value)} />
          <Button type="submit" disabled={send.isPending || !text.trim()}><Send size={16} /><span className="hidden sm:inline">{send.isPending ? "Sending…" : "Send"}</span></Button>
        </form>
        {send.isError && <p role="alert" className="px-5 pb-4 text-sm text-red-700 dark:text-red-300">{send.error.response?.data?.detail || "Message could not be sent. Please retry."}</p>}
      </Card>
    </div>
  );
}
