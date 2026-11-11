"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import { saveAs } from "file-saver";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

type Transaction = {
  id: string;
  description: string;
  category_id: string;
  category_name: string;
  amount: number;
  type: "income" | "expense";
  date: string;
};

type Budget = {
  id: string;
  name: string;
  category_name: string;
  amount: number;
  period: "weekly" | "monthly";
  spent: number;
  remaining: number;
  period_start: string;
  period_end: string;
};

type Period = "week" | "month" | "year" | "all";

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

const todayStamp = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};

function getStartDate(period: Period, now = new Date()) {
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  if (period === "week") start.setDate(start.getDate() - 6);
  if (period === "month") start.setDate(1);
  if (period === "year") start.setMonth(0, 1);
  if (period === "all") start.setFullYear(1970, 0, 1);
  return start;
}

function exportPDF(
  income: number,
  expenses: number,
  balance: number,
  transactions: Transaction[],
  period: Period,
  budgets: Budget[]
) {
  const doc = new jsPDF();
  doc.setFontSize(18);
  doc.text("PennyWise Financial Report", 14, 20);
  doc.setFontSize(11);
  doc.text(
    `Period: ${period === "all" ? "All available data" : `Last/current ${period}`}`,
    14,
    29
  );
  doc.text(`Income: ${money(income)}`, 14, 40);
  doc.text(`Expenses: ${money(expenses)}`, 14, 48);
  doc.text(`Net savings: ${money(balance)}`, 14, 56);

  autoTable(doc, {
    startY: 65,
    head: [["Description", "Category", "Date", "Type", "Amount"]],
    body: transactions.map((t) => [
      t.description,
      t.category_name,
      dateLabel(t.date),
      t.type,
      `${t.type === "income" ? "+" : "-"}${money(Number(t.amount))}`,
    ]),
  });

  if (budgets.length > 0) {
    doc.addPage();
    doc.setFontSize(16);
    doc.text("Budget Summary", 14, 20);
    autoTable(doc, {
      startY: 28,
      head: [["Budget", "Category", "Period", "Limit", "Spent", "Remaining"]],
      body: budgets.map((b) => [
        b.name,
        b.category_name,
        b.period,
        money(b.amount),
        money(b.spent),
        money(b.remaining),
      ]),
    });
  }

  doc.save(`PennyWise_Report_${todayStamp()}.pdf`);
}

function exportCSV(transactions: Transaction[], budgets: Budget[]) {
  const escapeCSV = (value: string | number) =>
    `"${String(value).replaceAll('"', '""')}"`;

  const rows = [
    ["Description", "Category", "Date", "Type", "Amount"],
    ...transactions.map((t) => [
      t.description,
      t.category_name,
      dateLabel(t.date),
      t.type,
      String(t.amount),
    ]),
    ...(budgets.length > 0
      ? [
          [],
          ["Budget", "Category", "Period", "Limit", "Spent", "Remaining"],
          ...budgets.map((b) => [
            b.name,
            b.category_name,
            b.period,
            String(b.amount),
            String(b.spent),
            String(b.remaining),
          ]),
        ]
      : []),
  ];

  const csv = rows.map((row) => row.map(escapeCSV).join(",")).join("\r\n");

  saveAs(
    new Blob(["\uFEFF", csv], { type: "text/csv;charset=utf-8;" }),
    `PennyWise_Report_${todayStamp()}.csv`
  );
}

export default function ReportsPage() {
  const [period, setPeriod] = useState<Period>("month");
  const [category, setCategory] = useState("all");
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    async function loadTransactions() {
      const token = localStorage.getItem("pennywise-access-token");

      if (!token) {
        setError("Your session has expired. Please log in again.");
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError("");

        const response = await fetch(`${API_URL}/transactions`, {
          headers: { Authorization: `Bearer ${token}` },
          signal: controller.signal,
          cache: "no-store",
        });

        if (response.status === 401) {
          throw new Error("Your session has expired. Please log in again.");
        }

        if (!response.ok) {
          throw new Error("Could not load your transactions. Please try again.");
        }

        const data: Transaction[] = await response.json();
        setTransactions(data);

        const budgetResponse = await fetch(`${API_URL}/budgets`, {
          headers: { Authorization: `Bearer ${token}` },
          signal: controller.signal,
          cache: "no-store",
        });
        if (budgetResponse.ok) setBudgets(await budgetResponse.json());
      } catch (err) {
        if (err instanceof Error && err.name === "AbortError") return;

        setError(
          err instanceof Error
            ? err.message
            : "Something went wrong while loading reports."
        );
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }

    loadTransactions();
    return () => controller.abort();
  }, []);

  const categories = useMemo(
    () =>
      Array.from(
        new Set(
          transactions
            .filter((t) => t.type === "expense")
            .map((t) => t.category_name)
        )
      ).sort(),
    [transactions]
  );

  const filteredTransactions = useMemo(() => {
    const start = getStartDate(period);
    const now = new Date();

    return transactions.filter((transaction) => {
      const date = new Date(`${transaction.date}T00:00:00`);

      return (
        date >= start &&
        date <= now &&
        (category === "all" ||
          transaction.type === "income" ||
          transaction.category_name === category)
      );
    });
  }, [transactions, period, category]);

  const exportBudgets =
    category === "all"
      ? budgets
      : budgets.filter((b) => b.category_name === category);
  const nothingToExport =
    filteredTransactions.length === 0 && exportBudgets.length === 0;

  const income = filteredTransactions
    .filter((t) => t.type === "income")
    .reduce((sum, t) => sum + Number(t.amount), 0);

  const expenses = filteredTransactions
    .filter((t) => t.type === "expense")
    .reduce((sum, t) => sum + Number(t.amount), 0);

  const balance = income - expenses;
  const maxTotal = Math.max(income, expenses, 1);

  const categoryTotals = useMemo(() => {
    const totals = new Map<string, number>();

    filteredTransactions
      .filter((t) => t.type === "expense")
      .forEach((t) => {
        totals.set(
          t.category_name,
          (totals.get(t.category_name) ?? 0) + Number(t.amount)
        );
      });

    return Array.from(totals.entries())
      .map(([name, amount]) => ({ name, amount }))
      .sort((a, b) => b.amount - a.amount);
  }, [filteredTransactions]);

  const maxCategoryTotal = Math.max(
    ...categoryTotals.map((item) => item.amount),
    1
  );

  const chartData = categoryTotals.map((item) => ({
    category: item.name,
    amount: item.amount,
  }));

  return (
    <main className="min-h-screen bg-[#f6f7fb] p-5 text-slate-800 md:p-9">
      <div className="mx-auto max-w-6xl">
        <header className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="mb-1 text-sm text-slate-500">PennyWise / Reports</p>
            <h1 className="text-3xl font-bold tracking-tight">Reports</h1>
            <p className="mt-2 text-sm text-slate-500">
              Understand your income, expenses and spending habits.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Link
              href="/"
              className="rounded-xl border border-slate-200 bg-white px-5 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
            >
              ← Back to Dashboard
            </Link>

            <label className="sr-only" htmlFor="report-period">
              Reporting period
            </label>
            <select
              id="report-period"
              value={period}
              onChange={(e) => setPeriod(e.target.value as Period)}
              className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none focus:border-indigo-500"
            >
              <option value="week">Last 7 days</option>
              <option value="month">This month</option>
              <option value="year">This year</option>
              <option value="all">All available data</option>
            </select>

            <label className="sr-only" htmlFor="report-category">
              Filter by category
            </label>
            <select
              id="report-category"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none focus:border-indigo-500"
            >
              <option value="all">All categories</option>
              {categories.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </div>
        </header>

        {error && (
          <div
            role="alert"
            className="mb-6 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700"
          >
            {error}
          </div>
        )}

        {loading ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center text-slate-500">
            Loading your reports...
          </div>
        ) : !error ? (
          <>
            <section className="mb-7 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <p className="text-sm text-slate-500">Total income</p>
                <p className="mt-3 text-2xl font-bold text-emerald-600">
                  {money(income)}
                </p>
                <p className="mt-2 text-xs text-slate-400">
                  Income in the selected period
                </p>
              </article>

              <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <p className="text-sm text-slate-500">Total expenses</p>
                <p className="mt-3 text-2xl font-bold text-rose-500">
                  {money(expenses)}
                </p>
                <p className="mt-2 text-xs text-slate-400">
                  Expenses in the selected period
                </p>
              </article>

              <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <p className="text-sm text-slate-500">Net savings</p>
                <p
                  className={`mt-3 text-2xl font-bold ${
                    balance < 0 ? "text-rose-600" : "text-indigo-600"
                  }`}
                >
                  {money(balance)}
                </p>
                <p className="mt-2 text-xs text-slate-400">
                  Income minus expenses
                </p>
              </article>
            </section>

            <section className="mb-7 grid gap-6 lg:grid-cols-2">
              <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <h2 className="font-bold">Income vs. expenses</h2>
                <p className="mt-1 text-sm text-slate-500">
                  Compare money earned with money spent.
                </p>

                <div className="mt-8 space-y-6">
                  {[
                    {
                      label: "Income",
                      amount: income,
                      color: "bg-emerald-500",
                    },
                    {
                      label: "Expenses",
                      amount: expenses,
                      color: "bg-rose-500",
                    },
                  ].map((item) => (
                    <div key={item.label}>
                      <div className="mb-2 flex justify-between gap-3 text-sm">
                        <span className="font-medium">{item.label}</span>
                        <span className="font-semibold">
                          {money(item.amount)}
                        </span>
                      </div>

                      <div
                        className="h-3 overflow-hidden rounded-full bg-slate-100"
                        role="progressbar"
                        aria-label={item.label}
                        aria-valuemin={0}
                        aria-valuemax={maxTotal}
                        aria-valuenow={item.amount}
                      >
                        <div
                          className={`h-full rounded-full ${item.color}`}
                          style={{
                            width: `${(item.amount / maxTotal) * 100}%`,
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>

                <div className="mt-8 rounded-xl bg-slate-50 p-4">
                  <p className="text-sm text-slate-500">Savings rate</p>
                  <p className="mt-1 text-xl font-bold">
                    {income > 0
                      ? `${Math.round((balance / income) * 100)}%`
                      : "—"}
                  </p>
                  <p className="mt-1 text-xs text-slate-400">
                    Calculated as net savings divided by income.
                  </p>
                </div>
              </article>

              <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <h2 className="font-bold">Expenses by category</h2>
                <p className="mt-1 text-sm text-slate-500">
                  See which categories account for your spending.
                </p>

                {categoryTotals.length === 0 ? (
                  <div className="py-12 text-center text-sm text-slate-500">
                    No expense data for this selection.
                  </div>
                ) : (
                  <>
                    <div className="mt-6 h-72">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={chartData}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="category" />
                          <YAxis />
                          <Tooltip
                            formatter={(value) => money(Number(value))}
                          />
                          <Bar
                            dataKey="amount"
                            fill="#4F46E5"
                            radius={[6, 6, 0, 0]}
                          />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>

                    <div className="mt-7 space-y-5">
                      {categoryTotals.map((item) => (
                        <div key={item.name}>
                          <div className="mb-2 flex justify-between gap-3 text-sm">
                            <span className="font-medium">{item.name}</span>
                            <span className="text-slate-500">
                              {money(item.amount)} ·{" "}
                              {expenses > 0
                                ? Math.round((item.amount / expenses) * 100)
                                : 0}
                              %
                            </span>
                          </div>
                          <div className="h-2.5 overflow-hidden rounded-full bg-slate-100">
                            <div
                              className="h-full rounded-full bg-indigo-600"
                              style={{
                                width: `${
                                  (item.amount / maxCategoryTotal) * 100
                                }%`,
                              }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </article>
            </section>

            <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
              <div className="border-b border-slate-100 p-6">
                <h2 className="font-bold">Transaction summary</h2>
                <p className="mt-1 text-sm text-slate-500">
                  {filteredTransactions.length} transaction
                  {filteredTransactions.length === 1 ? "" : "s"} in this
                  selection
                </p>
              </div>

              {filteredTransactions.length === 0 ? (
                <div className="px-6 py-12 text-center">
                  <p className="font-medium">No transactions found</p>
                  <p className="mt-2 text-sm text-slate-500">
                    Try another date range or category.
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                      <tr>
                        <th className="px-6 py-4 font-semibold">
                          Description
                        </th>
                        <th className="px-6 py-4 font-semibold">Category</th>
                        <th className="px-6 py-4 font-semibold">Date</th>
                        <th className="px-6 py-4 text-right font-semibold">
                          Amount
                        </th>
                      </tr>
                    </thead>

                    <tbody className="divide-y divide-slate-100">
                      {filteredTransactions
                        .slice()
                        .sort((a, b) => b.date.localeCompare(a.date))
                        .map((t) => (
                          <tr
                            key={t.id}
                            className="hover:bg-slate-50"
                          >
                            <td className="whitespace-nowrap px-6 py-4 font-medium">
                              {t.description}
                            </td>
                            <td className="whitespace-nowrap px-6 py-4 text-slate-500">
                              {t.category_name}
                            </td>
                            <td className="whitespace-nowrap px-6 py-4 text-slate-500">
                              {dateLabel(t.date)}
                            </td>
                            <td
                              className={`whitespace-nowrap px-6 py-4 text-right font-semibold ${
                                t.type === "income"
                                  ? "text-emerald-600"
                                  : "text-slate-800"
                              }`}
                            >
                              {t.type === "income" ? "+" : "−"}
                              {money(Number(t.amount))}
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            <section className="mt-7 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-bold">Export Reports</h2>
              <p className="mt-1 text-sm text-slate-500">
                Download the transactions, totals and your budget summary for
                the selected period and category.
              </p>

              <div className="mt-5 flex flex-wrap gap-4">
                <button
                  disabled={nothingToExport}
                  onClick={() =>
                    exportPDF(
                      income,
                      expenses,
                      balance,
                      filteredTransactions,
                      period,
                      exportBudgets
                    )
                  }
                  className="rounded-xl bg-indigo-600 px-5 py-3 text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Export PDF
                </button>

                <button
                  disabled={nothingToExport}
                  onClick={() => exportCSV(filteredTransactions, exportBudgets)}
                  className="rounded-xl border border-slate-300 px-5 py-3 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Export CSV
                </button>
              </div>

              {nothingToExport && (
                <p className="mt-3 text-sm text-slate-500">
                  Nothing to export for this selection.
                </p>
              )}
            </section>

            <p className="mt-7 text-center text-xs text-slate-400">
              PennyWise · Reports are calculated from your saved transactions.
            </p>
          </>
        ) : null}
      </div>
    </main>
  );
}