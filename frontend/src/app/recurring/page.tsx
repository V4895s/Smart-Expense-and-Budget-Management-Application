"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

type Frequency = "daily" | "weekly" | "monthly" | "yearly";

type Rule = {
  id: string;
  type: "income" | "expense";
  amount: number;
  category_id: string;
  category_name: string;
  description: string;
  frequency: Frequency;
  start_date: string;
  end_date: string | null;
  next_run_date: string;
  is_active: boolean;
};

type Category = {
  id: string;
  name: string;
  type: "income" | "expense";
};

const money = (amount: number) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(amount);

const dateLabel = (date: string) =>
  new Date(`${date}T00:00:00`).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem("pennywise-access-token");
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function apiError(response: Response) {
  try {
    const body = await response.json();
    return body.detail || body.message || "The request could not be completed.";
  } catch {
    return "The request could not be completed.";
  }
}

export default function RecurringPage() {
  const [rules, setRules] = useState<Rule[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [showForm, setShowForm] = useState(false);

  const [type, setType] = useState<"income" | "expense">("expense");
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [frequency, setFrequency] = useState<Frequency>("monthly");
  const [startDate, setStartDate] = useState(
    new Date().toISOString().slice(0, 10)
  );
  const [endDate, setEndDate] = useState("");

  const formCategories = categories.filter((c) => c.type === type);

  const load = useCallback(async () => {
    try {
      const headers = authHeaders();

      // Post any transactions that are due, then load the rules.
      const processResponse = await fetch(`${API_URL}/recurring/process`, {
        method: "POST",
        headers,
      });
      if (processResponse.ok) {
        const { created } = (await processResponse.json()) as { created: number };
        setNotice(
          created > 0
            ? `${created} recurring transaction${created === 1 ? "" : "s"} added to your transactions.`
            : ""
        );
      }

      const [rulesResponse, categoriesResponse] = await Promise.all([
        fetch(`${API_URL}/recurring`, { headers }),
        fetch(`${API_URL}/categories`, { headers }),
      ]);
      if (!rulesResponse.ok) throw new Error(await apiError(rulesResponse));
      if (!categoriesResponse.ok)
        throw new Error(await apiError(categoriesResponse));

      setRules(await rulesResponse.json());
      setCategories(await categoriesResponse.json());
      setError("");
    } catch (err) {
      setError(
        err instanceof TypeError
          ? "Service temporarily unavailable. Please try again."
          : err instanceof Error
            ? err.message
            : "Could not load recurring transactions."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  useEffect(() => {
    // keep the selected category valid when the type changes
    if (!formCategories.some((c) => c.id === categoryId)) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setCategoryId(formCategories[0]?.id ?? "");
    }
  }, [type, categories, categoryId, formCategories]);

  async function addRule(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!amount || Number(amount) <= 0 || !categoryId) {
      setError("Enter an amount greater than zero and choose a category.");
      return;
    }
    if (endDate && endDate < startDate) {
      setError("End date must not be before the start date.");
      return;
    }

    setSaving(true);
    try {
      const response = await fetch(`${API_URL}/recurring`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          type,
          amount,
          category_id: categoryId,
          description: description.trim(),
          frequency,
          start_date: startDate,
          end_date: endDate || null,
        }),
      });
      if (!response.ok) {
        setError(await apiError(response));
        return;
      }
      setDescription("");
      setAmount("");
      setEndDate("");
      setShowForm(false);
      setError("");
      await load();
    } catch {
      setError("Could not reach the server. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  async function togglePause(rule: Rule) {
    try {
      const response = await fetch(`${API_URL}/recurring/${rule.id}`, {
        method: "PUT",
        headers: authHeaders(),
        body: JSON.stringify({ is_active: !rule.is_active }),
      });
      if (!response.ok) {
        setError(await apiError(response));
        return;
      }
      await load();
    } catch {
      setError("Could not reach the server. Please try again.");
    }
  }

  async function removeRule(rule: Rule) {
    if (
      !window.confirm(
        "Delete this recurring rule? Transactions it already created are kept."
      )
    )
      return;
    try {
      const response = await fetch(`${API_URL}/recurring/${rule.id}`, {
        method: "DELETE",
        headers: authHeaders(),
      });
      if (!response.ok) {
        setError(await apiError(response));
        return;
      }
      await load();
    } catch {
      setError("Could not reach the server. Please try again.");
    }
  }

  return (
    <main className="min-h-screen bg-slate-50 p-5 text-slate-800 sm:p-8">
      <div className="mx-auto max-w-5xl">
        <header className="mb-8 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <Link
              href="/"
              className="mb-4 inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50"
            >
              <span aria-hidden="true">←</span>
              Back to Dashboard
            </Link>
            <h1 className="text-3xl font-bold tracking-tight">
              Recurring Transactions
            </h1>
            <p className="mt-2 text-slate-500">
              Salary, rent, subscriptions: add them once and they are posted
              automatically.
            </p>
          </div>

          <button
            onClick={() => {
              setShowForm(!showForm);
              setError("");
            }}
            className="rounded-xl bg-indigo-600 px-5 py-3 font-semibold text-white shadow-sm transition hover:bg-indigo-700"
          >
            {showForm ? "Cancel" : "+ Add Recurring"}
          </button>
        </header>

        {notice && (
          <p className="mb-4 rounded-xl bg-emerald-50 p-3 text-sm text-emerald-700">
            {notice}
          </p>
        )}
        {error && (
          <p className="mb-4 rounded-xl bg-rose-50 p-3 text-sm text-rose-700">
            {error}
          </p>
        )}

        {showForm && (
          <form
            onSubmit={addRule}
            className="mb-8 grid gap-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:grid-cols-2"
          >
            <label className="text-sm font-medium">
              Type
              <select
                value={type}
                onChange={(e) => setType(e.target.value as "income" | "expense")}
                className="mt-1 w-full rounded-xl border border-slate-300 p-3"
              >
                <option value="expense">Expense</option>
                <option value="income">Income</option>
              </select>
            </label>

            <label className="text-sm font-medium">
              Category
              <select
                value={categoryId}
                onChange={(e) => setCategoryId(e.target.value)}
                className="mt-1 w-full rounded-xl border border-slate-300 p-3"
              >
                {formCategories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </label>

            <label className="text-sm font-medium">
              Description
              <input
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                maxLength={200}
                placeholder="e.g. Netflix, Monthly salary"
                className="mt-1 w-full rounded-xl border border-slate-300 p-3"
              />
            </label>

            <label className="text-sm font-medium">
              Amount (₹)
              <input
                type="number"
                min="0.01"
                step="0.01"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                className="mt-1 w-full rounded-xl border border-slate-300 p-3"
              />
            </label>

            <label className="text-sm font-medium">
              Repeats
              <select
                value={frequency}
                onChange={(e) => setFrequency(e.target.value as Frequency)}
                className="mt-1 w-full rounded-xl border border-slate-300 p-3"
              >
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
                <option value="yearly">Yearly</option>
              </select>
            </label>

            <label className="text-sm font-medium">
              Start date
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="mt-1 w-full rounded-xl border border-slate-300 p-3"
              />
            </label>

            <label className="text-sm font-medium">
              End date (optional)
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="mt-1 w-full rounded-xl border border-slate-300 p-3"
              />
            </label>

            <div className="flex items-end">
              <button
                type="submit"
                disabled={saving}
                className="w-full rounded-xl bg-indigo-600 px-5 py-3 font-semibold text-white hover:bg-indigo-700 disabled:opacity-60"
              >
                {saving ? "Saving..." : "Save recurring rule"}
              </button>
            </div>
          </form>
        )}

        {loading ? (
          <p className="text-slate-500">Loading...</p>
        ) : rules.length === 0 ? (
          <p className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center text-slate-500">
            No recurring transactions yet. Add one to get started.
          </p>
        ) : (
          <div className="grid gap-4">
            {rules.map((rule) => (
              <article
                key={rule.id}
                className="flex flex-col justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:flex-row sm:items-center"
              >
                <div>
                  <h2 className="text-lg font-semibold">
                    {rule.description || rule.category_name}
                  </h2>
                  <p className="mt-1 text-sm text-slate-500">
                    {rule.category_name} · repeats {rule.frequency}
                    {rule.end_date ? ` until ${dateLabel(rule.end_date)}` : ""}
                  </p>
                  <p className="mt-1 text-sm text-slate-500">
                    {rule.is_active
                      ? `Next: ${dateLabel(rule.next_run_date)}`
                      : "Paused or finished"}
                  </p>
                </div>

                <div className="flex items-center gap-4">
                  <p
                    className={`text-xl font-bold ${
                      rule.type === "income"
                        ? "text-emerald-600"
                        : "text-rose-600"
                    }`}
                  >
                    {rule.type === "income" ? "+" : "−"}
                    {money(rule.amount)}
                  </p>
                  <button
                    onClick={() => togglePause(rule)}
                    className="rounded-xl border border-slate-300 px-4 py-2 text-sm hover:bg-slate-100"
                  >
                    {rule.is_active ? "Pause" : "Resume"}
                  </button>
                  <button
                    onClick={() => removeRule(rule)}
                    className="rounded-xl border border-rose-200 px-4 py-2 text-sm text-rose-600 hover:bg-rose-50"
                  >
                    Delete
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
