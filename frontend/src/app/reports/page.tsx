
"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

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

type Transaction = {
  id: number;
  description: string;
  category: string;
  amount: number;
  type: "income" | "expense";
  date: string;
};

const sampleTransactions: Transaction[] = [
  { id: 1, description: "Salary", category: "Income", amount: 45000, type: "income", date: "2026-10-26" },
  { id: 2, description: "Groceries", category: "Food", amount: 1250, type: "expense", date: "2026-10-25" },
  { id: 3, description: "Electricity Bill", category: "Utilities", amount: 1800, type: "expense", date: "2026-10-24" },
  { id: 4, description: "Freelance Work", category: "Income", amount: 6500, type: "income", date: "2026-10-23" },
  { id: 5, description: "Restaurant", category: "Food", amount: 850, type: "expense", date: "2026-10-22" },
  { id: 6, description: "Bus Pass", category: "Transport", amount: 1200, type: "expense", date: "2026-10-18" },
  { id: 7, description: "Online Course", category: "Education", amount: 2500, type: "expense", date: "2026-10-12" },
  { id: 8, description: "Shopping", category: "Shopping", amount: 3200, type: "expense", date: "2026-10-05" },
  { id: 9, description: "Part-time Work", category: "Income", amount: 8000, type: "income", date: "2026-09-20" },
  { id: 10, description: "Internet Bill", category: "Utilities", amount: 999, type: "expense", date: "2026-09-15" },
];

const money = (amount: number) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);

const dateLabel = (date: string) =>
  new Date(`${date}T00:00:00`).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });

  const exportPDF = (
  income: number,
  expenses: number,
  balance: number,
  filteredTransactions: Transaction[]
) => {
  const doc = new jsPDF();

  doc.setFontSize(18);
  doc.text("PennyWise Financial Report", 14, 20);

  doc.setFontSize(12);
  doc.text(`Income: ${money(income)}`, 14, 35);
  doc.text(`Expenses: ${money(expenses)}`, 14, 45);
  doc.text(`Net Savings: ${money(balance)}`, 14, 55);

  autoTable(doc, {
    startY: 70,
    head: [["Description", "Category", "Date", "Amount"]],
    body: filteredTransactions.map((t) => [
      t.description,
      t.category,
      dateLabel(t.date),
      `${t.type === "income" ? "+" : "-"}${money(t.amount)}`,
    ]),
  });

  doc.save("PennyWise_Report.pdf");
};

const exportCSV = (filteredTransactions: Transaction[]) => {
  const headers = ["Description", "Category", "Date", "Type", "Amount"];

  const rows = filteredTransactions.map((t) => [
    t.description,
    t.category,
    dateLabel(t.date),
    t.type,
    t.amount,
  ]);

  const csv =
    [headers, ...rows]
      .map((row) => row.join(","))
      .join("\n");

  const blob = new Blob([csv], {
    type: "text/csv;charset=utf-8;",
  });

  saveAs(blob, "PennyWise_Report.csv");
};


export default function ReportsPage() {
  const [period, setPeriod] = useState("month");
  const [category, setCategory] = useState("all");

  const filteredTransactions = useMemo(() => {
    const now = new Date();
    const start = new Date(now.getFullYear(), now.getMonth(), 1);

    if (period === "week") {
      start.setDate(now.getDate() - 6);
    } else if (period === "year") {
      start.setMonth(0, 1);
    } else if (period === "all") {
      start.setFullYear(2000, 0, 1);
    }

    return sampleTransactions.filter((transaction) => {
      const date = new Date(`${transaction.date}T00:00:00`);
      const withinPeriod = date >= start && date <= now;
      const matchesCategory =
        category === "all" || transaction.category === category;

      return withinPeriod && matchesCategory;
    });
  }, [period, category]);

  const income = filteredTransactions
    .filter((transaction) => transaction.type === "income")
    .reduce((sum, transaction) => sum + transaction.amount, 0);

  const expenses = filteredTransactions
    .filter((transaction) => transaction.type === "expense")
    .reduce((sum, transaction) => sum + transaction.amount, 0);

  const balance = income - expenses;
  const maxTotal = Math.max(income, expenses, 1);

  const categoryTotals = useMemo(() => {
    const totals = new Map<string, number>();

    filteredTransactions
      .filter((transaction) => transaction.type === "expense")
      .forEach((transaction) => {
        totals.set(
          transaction.category,
          (totals.get(transaction.category) ?? 0) + transaction.amount
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

  const categories = Array.from(
    new Set(sampleTransactions.map((transaction) => transaction.category))
  ).filter((item) => item !== "Income");

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
              onChange={(event) => setPeriod(event.target.value)}
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
              onChange={(event) => setCategory(event.target.value)}
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
            <p className={`mt-3 text-2xl font-bold ${balance < 0 ? "text-rose-600" : "text-indigo-600"}`}>
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
                { label: "Income", amount: income, color: "bg-emerald-500" },
                { label: "Expenses", amount: expenses, color: "bg-rose-500" },
              ].map((item) => (
                <div key={item.label}>
                  <div className="mb-2 flex justify-between gap-3 text-sm">
                    <span className="font-medium">{item.label}</span>
                    <span className="font-semibold">{money(item.amount)}</span>
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
                      style={{ width: `${(item.amount / maxTotal) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-8 rounded-xl bg-slate-50 p-4">
              <p className="text-sm text-slate-500">Savings rate</p>
              <p className="mt-1 text-xl font-bold">
                {income > 0 ? `${Math.round((balance / income) * 100)}%` : "—"}
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

            <div className="mt-6 h-72">
  <ResponsiveContainer width="100%" height="100%">
    <BarChart data={chartData}>
      <CartesianGrid strokeDasharray="3 3" />
      <XAxis dataKey="category" />
      <YAxis />
      <Tooltip />
      <Bar
        dataKey="amount"
        fill="#4F46E5"
        radius={[6, 6, 0, 0]}
      />
    </BarChart>
  </ResponsiveContainer>
</div>

            {categoryTotals.length === 0 ? (
              <div className="py-12 text-center text-sm text-slate-500">
                No expense data for this selection.
              </div>
            ) : (
              <>
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
                          width: `${(item.amount / maxCategoryTotal) * 100}%`,
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
              {filteredTransactions.length === 1 ? "" : "s"} in this selection
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
                    <th className="px-6 py-4 font-semibold">Description</th>
                    <th className="px-6 py-4 font-semibold">Category</th>
                    <th className="px-6 py-4 font-semibold">Date</th>
                    <th className="px-6 py-4 text-right font-semibold">Amount</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredTransactions
                    .slice()
                    .sort((a, b) => b.date.localeCompare(a.date))
                    .map((transaction) => (
                      <tr key={transaction.id} className="hover:bg-slate-50">
                        <td className="whitespace-nowrap px-6 py-4 font-medium">
                          {transaction.description}
                        </td>
                        <td className="whitespace-nowrap px-6 py-4 text-slate-500">
                          {transaction.category}
                        </td>
                        <td className="whitespace-nowrap px-6 py-4 text-slate-500">
                          {dateLabel(transaction.date)}
                        </td>
                        <td className={`whitespace-nowrap px-6 py-4 text-right font-semibold ${transaction.type === "income" ? "text-emerald-600" : "text-slate-800"}`}>
                          {transaction.type === "income" ? "+" : "−"}
                          {money(transaction.amount)}
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
    Download your report in different formats.
  </p>

  <div className="mt-5 flex gap-4">
    <button
      onClick={() =>
  exportPDF(income, expenses, balance, filteredTransactions)}
      className="rounded-xl bg-indigo-600 px-5 py-3 text-white hover:bg-indigo-700"
    >
      Export PDF
    </button>

    <button
      onClick={() => exportCSV(filteredTransactions)}
      className="rounded-xl border border-slate-300 px-5 py-3 hover:bg-slate-100"
    >
      Export CSV
    </button>
  </div>
</section>

        <p className="mt-7 text-center text-xs text-slate-400">
          PennyWise · Reports use sample transactions and are not connected to
          the live transaction list yet.
        </p>
      </div>
    </main>
  );
}
