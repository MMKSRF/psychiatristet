import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "@tanstack/react-router";
import { ArrowLeft, Check, MoreHorizontal, Pencil, Send, Trash2, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { useSession } from "../store";
import { PatientNotesPanel } from "./PatientNotesPanel";
import { Button, Card, Input } from "../ui";

export function ChatPage() {
  const { patientId } = useParams({ from: "/psychiatrist/chat/$patientId" });
  const psychiatristId = useSession((state) => state.user?.psychiatrist_id);
  const queryClient = useQueryClient();
  const [text, setText] = useState("");
  const [editingId, setEditingId] = useState(null);
  const [editText, setEditText] = useState("");
  const [deleteMenuId, setDeleteMenuId] = useState(null);
  const [actionError, setActionError] = useState("");
  const bottom = useRef(null);
  const patients = useQuery({
    queryKey: ["assigned-patients", psychiatristId],
    queryFn: async () => (await api.get(`/api/psychiatrist/${psychiatristId}/patients`)).data,
  });
  const patient = patients.data?.find((item) => item.telegram_id === Number(patientId));
  const chatKey = ["chat", patientId, psychiatristId];
  const messages = useQuery({
    queryKey: chatKey,
    queryFn: async () => (await api.get(`/api/chat/${patientId}/${psychiatristId}`)).data,
    refetchInterval: 4000,
  });
  const send = useMutation({
    mutationFn: () => api.post("/api/chat/send", { telegram_id: Number(patientId), psychiatrist_id: psychiatristId, text }),
    onSuccess: () => {
      setText("");
      setActionError("");
      queryClient.invalidateQueries({ queryKey: chatKey });
    },
    onError: (error) => setActionError(error.response?.data?.detail || "Message could not be sent. Please retry."),
  });
  const edit = useMutation({
    mutationFn: ({ messageId, nextText }) => api.patch(`/api/chat/${patientId}/${psychiatristId}/${messageId}`, { text: nextText }),
    onSuccess: () => {
      setEditingId(null);
      setEditText("");
      setActionError("");
      queryClient.invalidateQueries({ queryKey: chatKey });
    },
    onError: (error) => setActionError(error.response?.data?.detail || "Message could not be edited."),
  });
  const remove = useMutation({
    mutationFn: ({ messageId, scope }) => api.delete(`/api/chat/${patientId}/${psychiatristId}/${messageId}`, { params: { scope } }),
    onSuccess: () => {
      setDeleteMenuId(null);
      setActionError("");
      queryClient.invalidateQueries({ queryKey: chatKey });
    },
    onError: (error) => setActionError(error.response?.data?.detail || "Message could not be deleted."),
  });
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.data?.length]);

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link to="/psychiatrist/dashboard" className="inline-flex items-center gap-2 text-sm font-semibold text-muted hover:text-ink dark:hover:text-white"><ArrowLeft size={16} />Back to patients</Link>
        {patient && <Link to="/psychiatrist/notes/$patientId" params={{ patientId: String(patient.telegram_id) }} className="text-sm font-semibold text-teal-700 hover:underline dark:text-teal-300">Open notes separately</Link>}
      </div>
      {!patient && patients.isError && <p role="alert" className="rounded-xl bg-red-50 p-4 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">Could not load this patient. {patients.error.response?.data?.detail || ""}</p>}
      <div className="grid min-h-[76vh] gap-5 lg:grid-cols-[minmax(0,1.65fr)_minmax(330px,0.85fr)]">
        <Card className="flex min-h-[680px] min-w-0 flex-col overflow-hidden">
          <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4 dark:border-slate-800 sm:px-6">
            <div className="min-w-0"><h1 className="truncate text-lg font-bold">{patient?.name || "Patient conversation"}</h1><p className="mt-1 truncate text-sm text-muted dark:text-slate-400">{patient ? `${patient.age} years · ${patient.telegram_username ? `@${patient.telegram_username}` : "Telegram"}` : "Loading patient…"}</p></div>
            <div className="rounded-full bg-teal-50 px-3 py-1.5 text-xs font-semibold text-teal-700 dark:bg-teal-950 dark:text-teal-300">Telegram chat</div>
          </div>
          {patient?.complaint && <div className="border-b border-slate-100 bg-slate-50 px-5 py-3 text-sm leading-6 dark:border-slate-800 dark:bg-slate-800/40"><span className="mr-2 font-semibold">Intake</span>{patient.complaint}</div>}
          <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto bg-slate-50/70 px-4 py-5 dark:bg-slate-950/40 sm:px-6">
            {messages.isError && <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">{messages.error.response?.data?.detail || "Could not load this conversation."}</p>}
            {messages.isPending ? <div className="m-auto text-sm text-muted">Loading messages…</div> : messages.data?.length ? messages.data.map((message) => {
              const ownMessage = message.sender_type === "psychiatrist";
              const deleted = Boolean(message.deleted_at);
              const isEditing = editingId === message.message_id;

              return <div key={message.message_id} className={`group flex w-full ${ownMessage ? "justify-end" : "justify-start"}`}>
                <div className={`relative max-w-[88%] rounded-2xl px-4 py-3 sm:max-w-[82%] ${
                  ownMessage && !isEditing 
                    ? "rounded-br-md bg-teal-600 text-white" 
                    : "rounded-bl-md border border-slate-200 bg-white text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
                } ${deleted ? "italic opacity-75" : ""}`}>
                  {isEditing ? (
                    <form onSubmit={(event) => { event.preventDefault(); if (editText.trim()) edit.mutate({ messageId: message.message_id, nextText: editText }); }}>
                      
                      <label className="sr-only" htmlFor={`edit-message-${message.message_id}`}>Edit message</label>
                      <textarea 
                        id={`edit-message-${message.message_id}`} 
                        value={editText} 
                        onChange={(event) => setEditText(event.target.value)} 
                        maxLength={4000} 
                        rows={3} 
                        autoFocus 
                        className="w-full min-w-52 resize-y rounded-lg border border-slate-300 bg-white p-2 text-sm leading-6 text-slate-900 outline-none placeholder:text-slate-400 focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20 dark:border-slate-600 dark:bg-slate-900 dark:text-white dark:placeholder:text-slate-400 dark:focus:border-teal-400" 
                      />
                      
                      <div className="mt-2 flex justify-end gap-2">
                        <Button type="button" variant="ghost" className="px-2 py-1.5 text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-700" onClick={() => { setEditingId(null); setEditText(""); }}>
                          <X size={14} />Cancel
                        </Button>
                        <Button type="submit" variant="secondary" className="px-2 py-1.5" disabled={edit.isPending || !editText.trim()}>
                          <Check size={14} />Save
                        </Button>
                      </div>
                    </form>
                  ) : (
                    <>
                      <p className="whitespace-pre-wrap break-words text-sm leading-6">{deleted ? "This message was deleted" : message.text}</p>
                      <div className={`mt-1 flex items-center justify-end gap-1.5 text-[10px] ${ownMessage ? "text-teal-100" : "text-slate-400"}`}>
                        <time dateTime={message.timestamp}>{new Date(message.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</time>
                        {message.edited_at && !deleted && <span>· edited</span>}
                      </div>
                      {ownMessage && !deleted && (
                        <div className="absolute -top-3 right-2 flex gap-1 rounded-lg border border-slate-200 bg-white p-1 opacity-100 shadow transition sm:opacity-0 sm:group-hover:opacity-100 sm:focus-within:opacity-100 dark:border-slate-700 dark:bg-slate-800">
                          {Number.isInteger(message.telegram_message_id) && (
                            <Button type="button" variant="ghost" className="px-2 py-1.5 text-slate-700 dark:text-slate-200" aria-label="Edit sent message" title="Edit message" onClick={() => { setEditingId(message.message_id); setEditText(message.text); }}>
                              <Pencil size={13} />
                            </Button>
                          )}
                          <Button type="button" variant="ghost" className="px-2 py-1.5 text-slate-700 dark:text-slate-200" aria-label="Delete sent message" title="Delete message" onClick={() => setDeleteMenuId(deleteMenuId === message.message_id ? null : message.message_id)}>
                            <MoreHorizontal size={14} />
                          </Button>
                        </div>
                      )}
                      {ownMessage && deleteMenuId === message.message_id && (
                        <div className="mt-3 flex flex-wrap justify-end gap-2 border-t border-slate-200 dark:border-slate-700 pt-2">
                          <Button type="button" variant="ghost" className="px-2 py-1.5 text-xs text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-700" disabled={remove.isPending} onClick={() => { if (window.confirm("Hide this message from your chat only? The patient will still see it in Telegram.")) remove.mutate({ messageId: message.message_id, scope: "self" }); }}>
                            <Trash2 size={13} />Delete for me
                          </Button>
                          {Number.isInteger(message.telegram_message_id) && (
                            <Button type="button" variant="ghost" className="px-2 py-1.5 text-xs text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-700" disabled={remove.isPending} onClick={() => { if (window.confirm("Delete this message from Telegram for both you and the patient?")) remove.mutate({ messageId: message.message_id, scope: "everyone" }); }}>
                              <Trash2 size={13} />Delete for both
                            </Button>
                          )}
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>;
            }) : <div className="m-auto text-center"><p className="text-sm font-medium">No messages yet</p><p className="mt-1 text-xs text-muted dark:text-slate-400">Start the conversation below.</p></div>}
            <div ref={bottom} />
          </div>
          {actionError && <p role="alert" className="mx-4 mt-3 rounded-xl bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950 dark:text-red-300 sm:mx-5">{actionError}</p>}
          <form className="flex gap-3 border-t border-slate-100 p-4 dark:border-slate-800 sm:p-5" onSubmit={(event) => { event.preventDefault(); if (text.trim()) send.mutate(); }}>
            <Input aria-label="Message" placeholder="Write a message…" value={text} maxLength={4000} onChange={(event) => setText(event.target.value)} />
            <Button type="submit" disabled={send.isPending || !text.trim()}><Send size={16} /><span className="hidden sm:inline">{send.isPending ? "Sending…" : "Send"}</span></Button>
          </form>
        </Card>
        <div className="min-h-[560px] lg:sticky lg:top-24 lg:h-[calc(100vh-8rem)] lg:min-h-0">
          {patient ? <PatientNotesPanel patientId={Number(patientId)} patientName={patient.name} compact /> : <Card className="grid h-full place-items-center p-6 text-center text-sm text-muted">Patient notes will load with the assigned case.</Card>}
        </div>
      </div>
    </div>
  );
}