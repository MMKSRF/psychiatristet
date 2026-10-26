import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileText, Pencil, Plus, Save, Trash2, X } from "lucide-react";
import { useState } from "react";
import { api } from "../api";
import { useSession } from "../store";
import { Button, Card, Input } from "../ui";

export function PatientNotesPanel({ patientId, patientName, compact = false }) {
  const psychiatristId = useSession((state) => state.user?.psychiatrist_id);
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState("");
  const [editingId, setEditingId] = useState(null);
  const [editText, setEditText] = useState("");
  const [error, setError] = useState("");
  const queryKey = ["patient-notes", patientId, psychiatristId];
  const notes = useQuery({
    queryKey,
    queryFn: async () => (await api.get(`/api/chat/${patientId}/${psychiatristId}/notes`)).data,
    enabled: Boolean(patientId && psychiatristId),
  });
  const save = useMutation({
    mutationFn: () => editingId
      ? api.patch(`/api/chat/${patientId}/${psychiatristId}/notes/${editingId}`, { text: editText })
      : api.post(`/api/chat/${patientId}/${psychiatristId}/notes`, { text: draft }),
    onSuccess: () => {
      setDraft("");
      setEditingId(null);
      setEditText("");
      setError("");
      queryClient.invalidateQueries({ queryKey });
    },
    onError: (issue) => setError(issue.response?.data?.detail || "Could not save this note."),
  });
  const remove = useMutation({
    mutationFn: (noteId) => api.delete(`/api/chat/${patientId}/${psychiatristId}/notes/${noteId}`),
    onSuccess: () => {
      setError("");
      queryClient.invalidateQueries({ queryKey });
    },
    onError: (issue) => setError(issue.response?.data?.detail || "Could not delete this note."),
  });

  return (
    <Card className={`flex min-h-0 flex-col overflow-hidden ${compact ? "h-full rounded-none border-0 shadow-none dark:bg-slate-900" : ""}`}>
      <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4 dark:border-slate-800">
        <div className="flex items-center gap-2"><FileText size={17} className="text-teal-600" /><div><h2 className="text-sm font-bold">Private notes</h2><p className="text-xs text-muted dark:text-slate-400">{patientName || "Patient"} · only visible to you</p></div></div>
      </div>
      <form className="border-b border-slate-100 p-4 dark:border-slate-800" onSubmit={(event) => { event.preventDefault(); if (draft.trim()) save.mutate(); }}>
        <label htmlFor={`note-draft-${patientId}`} className="sr-only">Add a private patient note</label>
        <textarea id={`note-draft-${patientId}`} value={draft} onChange={(event) => setDraft(event.target.value)} maxLength={10000} rows={compact ? 4 : 5} placeholder="Write a private clinical note…" className="w-full resize-y rounded-xl border border-slate-200 bg-white p-3 text-sm leading-6 text-ink outline-none placeholder:text-slate-400 focus:border-teal-500 focus:ring-2 focus:ring-teal-100 dark:border-slate-700 dark:bg-slate-800 dark:text-white dark:focus:ring-teal-900" />
        <div className="mt-2 flex items-center justify-between gap-3"><span className="text-[11px] text-muted dark:text-slate-400">Private to your account</span><Button type="submit" disabled={save.isPending || !draft.trim()} className="px-3 py-2"><Plus size={15} />Add note</Button></div>
      </form>
      {error && <p role="alert" className="mx-4 mt-3 rounded-lg bg-red-50 p-3 text-xs text-red-700 dark:bg-red-950 dark:text-red-300">{error}</p>}
      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-4">
        {notes.isPending ? <p className="py-5 text-center text-sm text-muted">Loading notes…</p> : notes.isError ? <p role="alert" className="py-5 text-center text-sm text-red-700 dark:text-red-300">{notes.error.response?.data?.detail || "Could not load private notes."}</p> : notes.data?.length ? notes.data.map((note) => <article key={note.note_id} className="rounded-xl border border-slate-200 bg-white p-3 dark:border-slate-700 dark:bg-slate-800">
          {editingId === note.note_id ? <form onSubmit={(event) => { event.preventDefault(); save.mutate(); }}>
            <label className="sr-only" htmlFor={`edit-note-${note.note_id}`}>Edit note</label><textarea id={`edit-note-${note.note_id}`} value={editText} onChange={(event) => setEditText(event.target.value)} maxLength={10000} rows={4} className="w-full resize-y rounded-lg border border-slate-200 bg-transparent p-2 text-sm leading-6 outline-none focus:border-teal-500 dark:border-slate-600" />
            <div className="mt-2 flex justify-end gap-2"><Button type="button" variant="ghost" className="px-2 py-1.5" onClick={() => { setEditingId(null); setEditText(""); }}><X size={14} />Cancel</Button><Button type="submit" className="px-2 py-1.5" disabled={save.isPending || !editText.trim()}><Save size={14} />Save</Button></div>
          </form> : <>
            <p className="whitespace-pre-wrap break-words text-sm leading-6 text-slate-700 dark:text-slate-200">{note.text}</p>
            <div className="mt-3 flex items-center justify-between gap-2 border-t border-slate-100 pt-2 dark:border-slate-700"><time className="text-[10px] text-slate-400" dateTime={note.updated_at}>{note.updated_at !== note.created_at ? "Edited " : ""}{new Date(note.updated_at).toLocaleString()}</time><div className="flex gap-1"><Button type="button" variant="ghost" className="px-2 py-1.5 text-xs" aria-label="Edit note" onClick={() => { setEditingId(note.note_id); setEditText(note.text); }}><Pencil size={13} /></Button><Button type="button" variant="ghost" className="px-2 py-1.5 text-xs text-red-600 dark:text-red-300" aria-label="Delete note" disabled={remove.isPending} onClick={() => { if (window.confirm("Delete this private note? This cannot be undone.")) remove.mutate(note.note_id); }}><Trash2 size={13} /></Button></div></div>
          </>}
        </article>) : <div className="px-3 py-8 text-center"><p className="text-sm font-medium">No notes yet</p><p className="mt-1 text-xs leading-5 text-muted dark:text-slate-400">Add private notes to keep track of this patient’s care.</p></div>}
      </div>
    </Card>
  );
}
