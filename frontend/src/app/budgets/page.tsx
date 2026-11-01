"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

type Category = {
  id: string;
  name: string;
  type: "income" | "expense";
  is_default: boolean;
};

type Budget = {
  id: string;
  name: string;
  category_id: string;
  category_name: string;
  amount: number;
  period: "weekly" | "monthly";
  spent: number;
  remaining: number;
  period_start: string;
  period_end: string;
};

type BudgetForm = {
  name: string;
  category_id: string;
  amount: string;
  period: "weekly" | "monthly";
};

const money = (amount: number) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(amount);

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem("pennywise-access-token");

  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const body = await response.json();

    if (typeof body.message === "string") return body.message;
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // Ignore response parsing errors.
  }

  return "Something went wrong. Please try again.";
}

export default function BudgetsPage() {
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [editingId, setEditingId] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  const [error, setError] = useState("");

  const [form, setForm] = useState<BudgetForm>({
    name: "",
    category_id: "",
    amount: "",
    period: "monthly",
  });

  const expenseCategories = useMemo(
    () => categories.filter((category) => category.type === "expense"),
    [categories]
  );

  const load = useCallback(async () => {
    try {
      const headers = authHeaders();

      const [budgetResponse, categoryResponse] = await Promise.all([
        fetch(`${API_URL}/budgets`, { headers }),
        fetch(`${API_URL}/categories`, { headers }),
      ]);

      if (!budgetResponse.ok || !categoryResponse.ok) {
        throw new Error(
          await errorMessage(
            budgetResponse.ok ? categoryResponse : budgetResponse
          )
        );
      }

      const budgetData: Budget[] = await budgetResponse.json();
      const categoryData: Category[] = await categoryResponse.json();

      setBudgets(budgetData);
      setCategories(categoryData);
      setError("");
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not load your budgets."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const totalLimit = budgets.reduce(
    (sum, budget) => sum + budget.amount,
    0
  );

  const totalSpent = budgets.reduce(
    (sum, budget) => sum + budget.spent,
    0
  );

  const totalRemaining = budgets.reduce(
    (sum, budget) => sum + budget.remaining,
    0
  );

  function openCreateForm() {
    setEditingId(null);

    setForm({
      name: "",
      category_id: expenseCategories[0]?.id ?? "",
      amount: "",
      period: "monthly",
    });

    setError("");
    setShowForm(true);
  }

  function openEditForm(budget: Budget) {
    setEditingId(budget.id);

    setForm({
      name: budget.name,
      category_id: budget.category_id,
      amount: String(budget.amount),
      period: budget.period,
    });

    setError("");
    setShowForm(true);
  }

  async function saveBudget(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const name = form.name.trim();
    const amount = Number(form.amount);

    if (!name || !form.category_id) {
      setError("Enter a budget name and select a category.");
      return;
    }

    if (!Number.isFinite(amount) || amount <= 0) {
      setError("The spending limit must be greater than zero.");
      return;
    }

    const duplicate = budgets.some(
      (budget) =>
        budget.category_id === form.category_id &&
        budget.period === form.period &&
        budget.id !== editingId
    );

    if (duplicate) {
      setError(
        "A budget for this category and period already exists."
      );
      return;
    }

    setSaving(true);

    try {
      const response = await fetch(
        editingId
          ? `${API_URL}/budgets/${editingId}`
          : `${API_URL}/budgets`,
        {
          method: editingId ? "PUT" : "POST",
          headers: authHeaders(),
          body: JSON.stringify({
            name,
            category_id: form.category_id,
            amount,
            period: form.period,
          }),
        }
      );

      if (!response.ok) {
        setError(await errorMessage(response));
        return;
      }

      setShowForm(false);
      setEditingId(null);
      setError("");

      await load();
    } catch {
      setError("Could not reach the server. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  async function deleteBudget(id: string) {
    if (!window.confirm("Delete this budget? This action cannot be undone.")) {
      return;
    }

    try {
      const response = await fetch(`${API_URL}/budgets/${id}`, {
        method: "DELETE",
        headers: authHeaders(),
      });

      if (!response.ok) {
        setError(await errorMessage(response));
        return;
      }

      setBudgets((current) =>
        current.filter((budget) => budget.id !== id)
      );

      setError("");
    } catch {
      setError("Could not reach the server. Please try again.");
    }
  }

  return (
    <main className="min-h-screen bg-[#f6f7fb] p-5 text-slate-800 md:p-9">
      <div className="mx-auto max-w-6xl">
        <header className="mb-8 flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="mb-1 text-sm text-slate-500">
              PennyWise / Budgets
            </p>

            <h1 className="text-3xl font-bold tracking-tight">
              Your budgets
            </h1>

            <p className="mt-2 text-sm text-slate-500">
              Set spending limits and keep your expenses in check.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Link
              href="/"
              className="rounded-xl border border-slate-200 bg-white px-5 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
            >
              ← Back to Dashboard
            </Link>

            <button
              onClick={openCreateForm}
              disabled={expenseCategories.length === 0}
              className="rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              + Create budget
            </button>
          </div>
        </header>

        {error && (
          <p
            role="alert"
            className="mb-6 rounded-xl bg-rose-50 p-4 text-sm text-rose-700"
          >
            {error}
          </p>
        )}

        <section className="mb-7 grid gap-4 sm:grid-cols-3">
          <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-sm text-slate-500">Total budget</p>
            <p className="mt-3 text-2xl font-bold">{money(totalLimit)}</p>
            <p className="mt-2 text-xs text-slate-400">
              Across {budgets.length} budget{budgets.length === 1 ? "" : "s"}
            </p>
          </article>

          <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-sm text-slate-500">Total spent</p>
            <p className="mt-3 text-2xl font-bold text-indigo-600">
              {money(totalSpent)}
            </p>
            <p className="mt-2 text-xs text-slate-400">
              Based on your recorded expenses
            </p>
          </article>

          <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-sm text-slate-500">Remaining budget</p>
            <p
              className={`mt-3 text-2xl font-bold ${
                totalRemaining < 0
                  ? "text-rose-600"
                  : "text-emerald-600"
              }`}
            >
              {money(totalRemaining)}
            </p>
            <p className="mt-2 text-xs text-slate-400">
              Total remaining across budgets
            </p>
          </article>
        </section>

        {showForm && (
          <section className="mb-7 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="mb-5 text-lg font-bold">
              {editingId ? "Edit budget" : "Create a budget"}
            </h2>

            <form onSubmit={saveBudget} className="grid gap-4 sm:grid-cols-2">
              <div>
                <label
                  htmlFor="budget-name"
                  className="mb-2 block text-sm font-medium"
                >
                  Budget name
                </label>

                <input
                  id="budget-name"
                  value={form.name}
                  onChange={(event) =>
                    setForm({ ...form, name: event.target.value })
                  }
                  placeholder="e.g. Monthly groceries"
                  maxLength={100}
                  required
                  className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                />
              </div>

              <div>
                <label
                  htmlFor="budget-category"
                  className="mb-2 block text-sm font-medium"
                >
                  Expense category
                </label>

                <select
                  id="budget-category"
                  value={form.category_id}
                  onChange={(event) =>
                    setForm({ ...form, category_id: event.target.value })
                  }
                  required
                  className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none focus:border-indigo-500"
                >
                  <option value="" disabled>
                    Select a category
                  </option>

                  {expenseCategories.map((category) => (
                    <option key={category.id} value={category.id}>
                      {category.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label
                  htmlFor="budget-limit"
                  className="mb-2 block text-sm font-medium"
                >
                  Spending limit (₹)
                </label>

                <input
                  id="budget-limit"
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={form.amount}
                  onChange={(event) =>
                    setForm({ ...form, amount: event.target.value })
                  }
                  placeholder="10000"
                  required
                  className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label
                  htmlFor="budget-period"
                  className="mb-2 block text-sm font-medium"
                >
                  Budget period
                </label>

                <select
                  id="budget-period"
                  value={form.period}
                  onChange={(event) =>
                    setForm({
                      ...form,
                      period: event.target.value as "weekly" | "monthly",
                    })
                  }
                  className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none focus:border-indigo-500"
                >
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                </select>
              </div>

              <div className="flex flex-wrap gap-3 sm:col-span-2">
                <button
                  type="submit"
                  disabled={saving || expenseCategories.length === 0}
                  className="rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-60"
                >
                  {saving
                    ? "Saving..."
                    : editingId
                      ? "Save changes"
                      : "Create budget"}
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setShowForm(false);
                    setError("");
                  }}
                  className="rounded-xl border border-slate-200 px-5 py-3 text-sm font-semibold hover:bg-slate-50"
                >
                  Cancel
                </button>
              </div>
            </form>
          </section>
        )}

        <section>
          <div className="mb-4">
            <h2 className="text-lg font-bold">Your spending limits</h2>
            <p className="mt-1 text-sm text-slate-500">
              Review each category and its remaining allowance.
            </p>
          </div>

          {loading ? (
            <div className="rounded-2xl border border-slate-200 bg-white px-6 py-14 text-center text-slate-500">
              Loading budgets...
            </div>
          ) : budgets.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-14 text-center">
              <h3 className="font-semibold">No budgets yet</h3>

              <p className="mt-2 text-sm text-slate-500">
                Create your first budget to start tracking spending.
              </p>

              <button
                onClick={openCreateForm}
                className="mt-5 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white hover:bg-indigo-700"
              >
                Create your first budget
              </button>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {budgets.map((budget) => {
                const percentage =
                  budget.amount > 0
                    ? Math.round((budget.spent / budget.amount) * 100)
                    : 0;

                const overBudget = budget.remaining < 0;
                const warning = percentage >= 75;

                return (
                  <article
                    key={budget.id}
                    className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-wide text-indigo-600">
                          {budget.category_name}
                        </p>

                        <h3 className="mt-2 text-lg font-bold">
                          {budget.name}
                        </h3>

                        <p className="mt-1 text-xs capitalize text-slate-400">
                          {budget.period} · {budget.period_start} to {budget.period_end}
                        </p>
                      </div>

                      <div className="flex gap-3 text-sm">
                        <button
                          onClick={() => openEditForm(budget)}
                          className="font-medium text-indigo-600 hover:text-indigo-800"
                          aria-label={`Edit ${budget.name}`}
                        >
                          Edit
                        </button>

                        <button
                          onClick={() => deleteBudget(budget.id)}
                          className="font-medium text-rose-600 hover:text-rose-800"
                          aria-label={`Delete ${budget.name}`}
                        >
                          Delete
                        </button>
                      </div>
                    </div>

                    <div className="mt-6 flex items-end justify-between gap-3">
                      <div>
                        <p className="text-sm text-slate-500">Spent</p>
                        <p className="mt-1 text-xl font-bold">
                          {money(budget.spent)}
                        </p>
                      </div>

                      <p className="text-right text-sm text-slate-500">
                        Limit{" "}
                        <span className="font-semibold text-slate-800">
                          {money(budget.amount)}
                        </span>
                      </p>
                    </div>

                    <div
                      className="mt-4 h-2.5 overflow-hidden rounded-full bg-slate-100"
                      role="progressbar"
                      aria-label={`${budget.name} spending`}
                      aria-valuemin={0}
                      aria-valuemax={budget.amount}
                      aria-valuenow={Math.min(Math.max(budget.spent, 0), budget.amount)}
                    >
                      <div
                        className={`h-full rounded-full ${
                          overBudget
                            ? "bg-rose-500"
                            : warning
                              ? "bg-amber-500"
                              : "bg-indigo-600"
                        }`}
                        style={{
                          width: `${Math.min(Math.max(percentage, 0), 100)}%`,
                        }}
                      />
                    </div>

                    <div className="mt-3 flex flex-wrap justify-between gap-2 text-sm">
                      <span
                        className={
                          warning
                            ? "font-medium text-amber-600"
                            : "text-slate-500"
                        }
                      >
                        {percentage}% used
                      </span>

                      <span
                        className={`font-semibold ${
                          overBudget ? "text-rose-600" : "text-emerald-600"
                        }`}
                      >
                        {overBudget
                          ? `${money(Math.abs(budget.remaining))} over budget`
                          : `${money(budget.remaining)} remaining`}
                      </span>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>

        <p className="mt-8 text-center text-xs text-slate-400">
          PennyWise · Budget and spending data synced with your account.
        </p>
      </div>
    </main>
  );
}