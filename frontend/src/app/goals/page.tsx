"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

type Goal = {
  id: string;
  name: string;
  target_amount: number;
  current_amount: number;
  target_date: string | null;
  progress_percent: number;
  status: "active" | "completed";
  created_at: string;
};

type GoalForm = {
  name: string;
  target_amount: string;
  current_amount: string;
  target_date: string;
};

const emptyForm: GoalForm = {
  name: "",
  target_amount: "",
  current_amount: "0",
  target_date: "",
};

function money(amount: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(amount);
}

async function apiError(response: Response) {
  try {
    const body = await response.json();
    return body.detail || body.message || "The request could not be completed.";
  } catch {
    return "The request could not be completed.";
  }
}

function GoalCard({
  goal,
  onEdit,
  onDelete,
  onContribute,
}: {
  goal: Goal;
  onEdit: (goal: Goal) => void;
  onDelete: (goal: Goal) => void;
  onContribute: (goal: Goal, amount: string) => Promise<void>;
}) {
  const [amount, setAmount] = useState("");
  const [saving, setSaving] = useState(false);
  const remaining = Math.max(0, goal.target_amount - goal.current_amount);

  async function contribute(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!amount || Number(amount) <= 0 || Number(amount) > remaining) return;

    setSaving(true);

    try {
      await onContribute(goal, amount);
      setAmount("");
    } finally {
      setSaving(false);
    }
  }

  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">{goal.name}</h2>
          <p className="mt-1 text-sm text-slate-500">
            {goal.target_date
              ? `Target date: ${new Date(
                  `${goal.target_date}T00:00:00`
                ).toLocaleDateString("en-IN")}`
              : "No target date"}
          </p>
        </div>

        <span
          className={`rounded-full px-3 py-1 text-xs font-semibold ${
            goal.status === "completed"
              ? "bg-emerald-100 text-emerald-700"
              : "bg-indigo-50 text-indigo-700"
          }`}
        >
          {goal.status === "completed" ? "Completed" : "In progress"}
        </span>
      </div>

      <div className="mt-6 flex items-end justify-between gap-4">
        <div>
          <p className="text-2xl font-bold text-slate-900">
            {money(goal.current_amount)}
          </p>
          <p className="mt-1 text-sm text-slate-500">
            of {money(goal.target_amount)}
          </p>
        </div>

        <p className="text-xl font-bold text-indigo-600">
          {goal.progress_percent}%
        </p>
      </div>

      <div
        className="mt-4 h-3 overflow-hidden rounded-full bg-slate-100"
        role="progressbar"
        aria-label={`${goal.name} progress`}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={goal.progress_percent}
      >
        <div
          className="h-full rounded-full bg-indigo-600 transition-all"
          style={{ width: `${goal.progress_percent}%` }}
        />
      </div>

      <p className="mt-2 text-xs text-slate-500">
        {remaining > 0
          ? `${money(remaining)} left to reach your goal`
          : "Target reached"}
      </p>

      {goal.status !== "completed" && (
        <form onSubmit={contribute} className="mt-5 flex flex-wrap gap-2">
          <label className="sr-only" htmlFor={`contribution-${goal.id}`}>
            Contribution amount
          </label>

          <input
            id={`contribution-${goal.id}`}
            type="number"
            min="0.01"
            max={remaining}
            step="0.01"
            required
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="Add contribution"
            className="min-w-0 flex-1 rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-indigo-500"
          />

          <button
            disabled={saving || !amount || Number(amount) > remaining}
            className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {saving ? "Saving..." : "Add"}
          </button>
        </form>
      )}

      <div className="mt-5 flex gap-4 border-t border-slate-100 pt-4">
        <button
          onClick={() => onEdit(goal)}
          className="text-sm font-semibold text-indigo-600 hover:text-indigo-800"
        >
          Edit
        </button>

        <button
          onClick={() => onDelete(goal)}
          className="text-sm font-semibold text-rose-600 hover:text-rose-800"
        >
          Delete
        </button>
      </div>
    </article>
  );
}

export default function SavingsGoalsPage() {
  const [goals, setGoals] = useState<Goal[]>([]);
  const [form, setForm] = useState<GoalForm>(emptyForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadGoals = useCallback(async () => {
    const token = localStorage.getItem("pennywise-access-token");

    if (!token) {
      setError("Your session has expired. Please log in again.");
      setLoading(false);
      return;
    }

    try {
      setLoading(true);

      const response = await fetch(`${API_URL}/savings-goals`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      });

      if (!response.ok) throw new Error(await apiError(response));

      setGoals(await response.json());
      setError("");
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not load savings goals."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadGoals();
  }, [loadGoals]);

  function startCreate() {
    setEditingId(null);
    setForm(emptyForm);
    setShowForm(true);
    setError("");
    setNotice("");
  }

  function startEdit(goal: Goal) {
    setEditingId(goal.id);
    setForm({
      name: goal.name,
      target_amount: String(goal.target_amount),
      current_amount: String(goal.current_amount),
      target_date: goal.target_date || "",
    });
    setShowForm(true);
    setError("");
    setNotice("");
  }

  async function submitGoal(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const token = localStorage.getItem("pennywise-access-token");

    if (!token) {
      setError("Your session has expired. Please log in again.");
      return;
    }

    const target = Number(form.target_amount);
    const current = Number(form.current_amount);

    if (
      !form.name.trim() ||
      !Number.isFinite(target) ||
      target <= 0 ||
      !Number.isFinite(current) ||
      current < 0 ||
      current > target
    ) {
      setError(
        "Enter a name, a positive target, and a saved amount between zero and the target."
      );
      return;
    }

    const payload = {
      name: form.name,
      target_amount: target,
      current_amount: current,
      target_date: form.target_date || null,
    };

    try {
      setSaving(true);

      const response = await fetch(
        `${API_URL}/savings-goals${editingId ? `/${editingId}` : ""}`,
        {
          method: editingId ? "PUT" : "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        }
      );

      if (!response.ok) throw new Error(await apiError(response));

      setShowForm(false);
      setForm(emptyForm);
      setEditingId(null);
      setNotice(editingId ? "Savings goal updated." : "Savings goal created.");

      await loadGoals();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not save the goal."
      );
    } finally {
      setSaving(false);
    }
  }

  async function contribute(goal: Goal, amount: string) {
    const token = localStorage.getItem("pennywise-access-token");

    if (!token) {
      setError("Your session has expired. Please log in again.");
      return;
    }

    try {
      setError("");

      const response = await fetch(
        `${API_URL}/savings-goals/${goal.id}/contributions`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ amount: Number(amount) }),
        }
      );

      if (!response.ok) throw new Error(await apiError(response));

      setNotice(`Contribution added to ${goal.name}.`);
      await loadGoals();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not add the contribution."
      );
    }
  }

  async function deleteGoal(goal: Goal) {
    if (
      !window.confirm(
        `Delete the savings goal "${goal.name}"? This cannot be undone.`
      )
    ) {
      return;
    }

    const token = localStorage.getItem("pennywise-access-token");

    if (!token) {
      setError("Your session has expired. Please log in again.");
      return;
    }

    try {
      const response = await fetch(`${API_URL}/savings-goals/${goal.id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) throw new Error(await apiError(response));

      setNotice("Savings goal deleted.");
      await loadGoals();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not delete the goal."
      );
    }
  }

  const totalTarget = goals.reduce(
    (sum, goal) => sum + goal.target_amount,
    0
  );

  const totalSaved = goals.reduce(
    (sum, goal) => sum + goal.current_amount,
    0
  );

  return (
    <main className="min-h-screen bg-[#f6f7fb] p-5 text-slate-800 md:p-9">
      <div className="mx-auto max-w-6xl">
        <header className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="mb-1 text-sm text-slate-500">
              PennyWise / Savings Goals
            </p>
            <h1 className="text-3xl font-bold tracking-tight">
              Savings Goals
            </h1>
            <p className="mt-2 text-sm text-slate-500">
              Set a target, add contributions, and track your progress.
            </p>
          </div>

          <div className="flex gap-3">
            <Link
              href="/"
              className="rounded-xl border border-slate-200 bg-white px-5 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
            >
              ← Dashboard
            </Link>

            <button
              onClick={startCreate}
              className="rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white hover:bg-indigo-700"
            >
              + New Goal
            </button>
          </div>
        </header>

        {error && (
          <div
            role="alert"
            className="mb-5 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700"
          >
            {error}
          </div>
        )}

        {notice && (
          <div
            role="status"
            className="mb-5 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700"
          >
            {notice}
          </div>
        )}

        {showForm && (
          <form
            onSubmit={submitGoal}
            className="mb-7 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
          >
            <div className="mb-5 flex items-center justify-between">
              <h2 className="text-lg font-semibold">
                {editingId ? "Edit savings goal" : "Create savings goal"}
              </h2>

              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="text-sm text-slate-500 hover:text-slate-800"
              >
                Cancel
              </button>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <label className="text-sm font-medium text-slate-700">
                Goal name
                <input
                  required
                  maxLength={100}
                  value={form.name}
                  onChange={(e) =>
                    setForm({ ...form, name: e.target.value })
                  }
                  placeholder="Emergency fund"
                  className="mt-2 w-full rounded-xl border border-slate-200 px-4 py-3 font-normal outline-none focus:border-indigo-500"
                />
              </label>

              <label className="text-sm font-medium text-slate-700">
                Target amount (₹)
                <input
                  required
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={form.target_amount}
                  onChange={(e) =>
                    setForm({ ...form, target_amount: e.target.value })
                  }
                  placeholder="50000"
                  className="mt-2 w-full rounded-xl border border-slate-200 px-4 py-3 font-normal outline-none focus:border-indigo-500"
                />
              </label>

              <label className="text-sm font-medium text-slate-700">
                Already saved (₹)
                <input
                  required
                  type="number"
                  min="0"
                  step="0.01"
                  value={form.current_amount}
                  onChange={(e) =>
                    setForm({ ...form, current_amount: e.target.value })
                  }
                  className="mt-2 w-full rounded-xl border border-slate-200 px-4 py-3 font-normal outline-none focus:border-indigo-500"
                />
              </label>

              <label className="text-sm font-medium text-slate-700">
                Target date (optional)
                <input
                  type="date"
                  value={form.target_date}
                  onChange={(e) =>
                    setForm({ ...form, target_date: e.target.value })
                  }
                  className="mt-2 w-full rounded-xl border border-slate-200 px-4 py-3 font-normal outline-none focus:border-indigo-500"
                />
              </label>
            </div>

            <button
              disabled={saving}
              className="mt-5 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {saving
                ? "Saving..."
                : editingId
                  ? "Save changes"
                  : "Create goal"}
            </button>
          </form>
        )}

        <section className="mb-7 grid gap-4 sm:grid-cols-2">
          <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-sm text-slate-500">
              Total saved toward goals
            </p>
            <p className="mt-2 text-2xl font-bold text-emerald-600">
              {money(totalSaved)}
            </p>
          </article>

          <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-sm text-slate-500">Combined goal targets</p>
            <p className="mt-2 text-2xl font-bold text-slate-900">
              {money(totalTarget)}
            </p>
          </article>
        </section>

        {loading ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center text-slate-500">
            Loading savings goals...
          </div>
        ) : goals.length === 0 ? (
          <div className="rounded-2xl border border-slate-200 bg-white px-6 py-14 text-center">
            <h2 className="font-semibold text-slate-900">
              No savings goals yet
            </h2>
            <p className="mt-2 text-sm text-slate-500">
              Create your first goal to start tracking your savings.
            </p>
            <button
              onClick={startCreate}
              className="mt-5 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white hover:bg-indigo-700"
            >
              Create a goal
            </button>
          </div>
        ) : (
          <section className="grid gap-5 md:grid-cols-2">
            {goals.map((goal) => (
              <GoalCard
                key={goal.id}
                goal={goal}
                onEdit={startEdit}
                onDelete={deleteGoal}
                onContribute={contribute}
              />
            ))}
          </section>
        )}
      </div>
    </main>
  );
}