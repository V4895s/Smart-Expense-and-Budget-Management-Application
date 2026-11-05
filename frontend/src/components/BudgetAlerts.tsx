"use client";

import { useCallback, useEffect, useState } from "react";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

type Alert = {
  id: string;
  title: string;
  message: string;
  level: "warning" | "danger";
  created_at: string;
};

export default function BudgetAlerts() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const loadAlerts = useCallback(async () => {
    const token = localStorage.getItem("pennywise-access-token");

    if (!token) {
      setLoading(false);
      return;
    }

    try {
      const response = await fetch(
        `${API_URL}/notifications?unread_only=true`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
          cache: "no-store",
        }
      );

      if (!response.ok) {
        throw new Error("Could not load budget alerts.");
      }

      setAlerts(await response.json());
      setError("");

    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not load alerts."
      );

    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAlerts();
  }, [loadAlerts]);

  async function markRead(id: string) {
    const token = localStorage.getItem("pennywise-access-token");

    if (!token) return;

    try {
      const response = await fetch(
        `${API_URL}/notifications/${id}/read`,
        {
          method: "PATCH",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error("Could not update this alert.");
      }

      setAlerts((current) =>
        current.filter((alert) => alert.id !== id)
      );

    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not update alert."
      );
    }
  }

  if (loading || (!error && alerts.length === 0)) {
    return null;
  }

  return (
    <section
      className="mt-8"
      aria-labelledby="budget-alerts-heading"
    >
      <div className="mb-4 flex items-center justify-between">
        <h2
          id="budget-alerts-heading"
          className="text-xl font-semibold text-slate-900"
        >
          Budget alerts
        </h2>

        {alerts.length > 0 && (
          <span className="rounded-full bg-rose-100 px-3 py-1 text-xs font-semibold text-rose-700">
            {alerts.length} unread
          </span>
        )}
      </div>

      {error && (
        <p
          role="alert"
          className="mb-3 rounded-xl bg-rose-50 p-3 text-sm text-rose-700"
        >
          {error}
        </p>
      )}

      <div className="space-y-3">
        {alerts.map((alert) => (
          <article
            key={alert.id}
            className={`flex flex-wrap items-start justify-between gap-4 rounded-xl border p-4 ${
              alert.level === "danger"
                ? "border-rose-200 bg-rose-50"
                : "border-amber-200 bg-amber-50"
            }`}
          >
            <div className="min-w-0 flex-1">
              <h3 className="font-semibold text-slate-900">
                {alert.title}
              </h3>

              <p className="mt-1 text-sm text-slate-700">
                {alert.message}
              </p>

              <p className="mt-2 text-xs text-slate-500">
                {new Date(alert.created_at).toLocaleString("en-IN")}
              </p>
            </div>

            <button
              onClick={() => markRead(alert.id)}
              className="text-sm font-semibold text-slate-700 underline underline-offset-2 hover:text-slate-950"
            >
              Mark as read
            </button>
          </article>
        ))}
      </div>
    </section>
  );
}