import { forwardRef } from "react";

export function Card({ className = "", children }) {
  return <section className={`rounded-2xl border border-slate-200 bg-white shadow-card dark:border-slate-700 dark:bg-slate-900 ${className}`}>{children}</section>;
}

export const Button = forwardRef(function Button({ variant = "primary", className = "", ...props }, ref) {
  const variants = {
    primary: "bg-teal-600 text-white hover:bg-teal-700 disabled:opacity-50",
    secondary: "border border-slate-200 bg-white text-ink hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-white dark:hover:bg-slate-700",
    ghost: "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800",
  };
  return <button ref={ref} className={`inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition disabled:cursor-not-allowed ${variants[variant]} ${className}`} {...props} />;
});

export function Input(props) {
  return <input {...props} className={`w-full rounded-xl border border-slate-200 bg-white px-3.5 py-3 text-sm text-ink outline-none placeholder:text-slate-400 focus:border-teal-500 focus:ring-2 focus:ring-teal-100 dark:border-slate-700 dark:bg-slate-800 dark:text-white dark:focus:ring-teal-900 ${props.className || ""}`} />;
}

export function Status({ children }) {
  const active = children === "Active" || children === "Available";
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${active ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300" : "bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300"}`}>{children?.replaceAll("_", " ")}</span>;
}
