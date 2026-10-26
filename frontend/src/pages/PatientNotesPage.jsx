import { Link, useParams } from "@tanstack/react-router";
import { ArrowLeft } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { useSession } from "../store";
import { PatientNotesPanel } from "./PatientNotesPanel";

export function PatientNotesPage() {
  const { patientId } = useParams({ from: "/psychiatrist/notes/$patientId" });
  const psychiatristId = useSession((state) => state.user?.psychiatrist_id);
  const patients = useQuery({
    queryKey: ["assigned-patients", psychiatristId],
    queryFn: async () => (await api.get(`/api/psychiatrist/${psychiatristId}/patients`)).data,
    enabled: Boolean(psychiatristId),
  });
  const patient = patients.data?.find((item) => item.telegram_id === Number(patientId));

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <Link to="/psychiatrist/dashboard" className="inline-flex items-center gap-2 text-sm font-semibold text-muted hover:text-ink dark:hover:text-white"><ArrowLeft size={16} />Back to patients</Link>
      <PatientNotesPanel patientId={Number(patientId)} patientName={patient?.name} />
    </div>
  );
}
