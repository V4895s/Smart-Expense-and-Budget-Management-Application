
"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

type Transaction = {
  id: string;
  title: string;
  category: string;
  date: string;
  amount: number;
  type: "Income" | "Expense";
};

type Category = {
  id: string;
  name: string;
  type: "income" | "expense";
};

type ApiTransaction = {
  id: string;
  type: "income" | "expense";
  amount: number;
  category_name: string;
  date: string;
  description: string;
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
    // ignore body parse errors
  }
  return "Something went wrong. Please try again.";
}

function fromApi(item: ApiTransaction): Transaction {
  return {
    id: item.id,
    title: item.description || item.category_name,
    category: item.category_name,
    date: item.date,
    amount: item.amount,
    type: item.type === "income" ? "Income" : "Expense",
  };
}

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [allCategories, setAllCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("All");
  const [categoryFilter, setCategoryFilter] = useState("All");
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [amount, setAmount] = useState("");
  const [type, setType] = useState<"Income" | "Expense">("Expense");
  const [error, setError] = useState("");

  const formCategories = allCategories.filter(
    (item) => item.type === type.toLowerCase()
  );
  const categories = Array.from(
    new Set(allCategories.map((item) => item.name))
  ).sort();

  const load = useCallback(async () => {
    try {
      const headers = authHeaders();
      const [categoryResponse, transactionResponse] = await Promise.all([
        fetch(`${API_URL}/categories`, { headers }),
        fetch(`${API_URL}/transactions`, { headers }),
      ]);

      if (!categoryResponse.ok || !transactionResponse.ok) {
        throw new Error(
          await errorMessage(
            categoryResponse.ok ? transactionResponse : categoryResponse
          )
        );
      }

      setAllCategories(await categoryResponse.json());
      setTransactions(
        ((await transactionResponse.json()) as ApiTransaction[]).map(fromApi)
      );
      setError("");
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not load your transactions."
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
    // keep the selected category valid when the transaction type changes
    const valid = allCategories.filter(
      (item) => item.type === type.toLowerCase()
    );
    if (!valid.some((item) => item.id === categoryId)) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setCategoryId(valid[0]?.id ?? "");
    }
  }, [type, allCategories, categoryId]);

  const filteredTransactions = useMemo(() => {
    return transactions.filter((transaction) => {
      const matchesSearch =
        transaction.title.toLowerCase().includes(search.toLowerCase()) ||
        transaction.category.toLowerCase().includes(search.toLowerCase());

      const matchesType =
        typeFilter === "All" || transaction.type === typeFilter;

      const matchesCategory =
        categoryFilter === "All" ||
        transaction.category === categoryFilter;

      return matchesSearch && matchesType && matchesCategory;
    });
  }, [transactions, search, typeFilter, categoryFilter]);

  const totalIncome = transactions
    .filter((transaction) => transaction.type === "Income")
    .reduce((sum, transaction) => sum + transaction.amount, 0);

  const totalExpenses = transactions
    .filter((transaction) => transaction.type === "Expense")
    .reduce((sum, transaction) => sum + transaction.amount, 0);

  async function addTransaction(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const numericAmount = Number(amount);

    if (!title.trim() || !amount || numericAmount <= 0 || !categoryId) {
      setError("Enter a description, a category and an amount greater than zero.");
      return;
    }

    setSaving(true);
    try {
      const response = await fetch(
        `${API_URL}/${type === "Income" ? "income" : "expenses"}`,
        {
          method: "POST",
          headers: authHeaders(),
          body: JSON.stringify({
            amount: amount,
            category_id: categoryId,
            date,
            description: title.trim(),
          }),
        }
      );

      if (!response.ok) {
        setError(await errorMessage(response));
        return;
      }

      const created = fromApi(await response.json());
      setTransactions((current) => [created, ...current]);
      setTitle("");
      setAmount("");
      setDate(new Date().toISOString().slice(0, 10));
      setError("");
      setShowForm(false);
    } catch {
      setError("Could not reach the server. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  async function deleteTransaction(item: Transaction) {
    if (!window.confirm("Delete this transaction?")) return;

    try {
      const response = await fetch(
        `${API_URL}/${item.type === "Income" ? "income" : "expenses"}/${item.id}`,
        { method: "DELETE", headers: authHeaders() }
      );

      if (!response.ok) {
        setError(await errorMessage(response));
        return;
      }

      setTransactions((current) =>
        current.filter((transaction) => transaction.id !== item.id)
      );
      setError("");
    } catch {
      setError("Could not reach the server. Please try again.");
    }
  }

  return (
    <main className="min-h-screen bg-slate-50 p-5 text-slate-800 sm:p-8">
      <div className="mx-auto max-w-7xl">
        <header className="mb-8 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <p className="mb-1 text-sm font-medium text-indigo-600">
              PENNYWISE / FINANCES
            </p>
            <Link
                href="/"
                className="mb-4 inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50"
            >
              <span aria-hidden="true">←</span>
                Back to Dashboard
            </Link>
            <h1 className="text-3xl font-bold tracking-tight">
              Transactions
            </h1>
            <p className="mt-2 text-slate-500">
              Track and manage your income and expenses.
            </p>
          </div>

          <button
            onClick={() => {
              setShowForm(!showForm);
              setError("");
            }}
            className="rounded-xl bg-indigo-600 px-5 py-3 font-semibold text-white shadow-sm transition hover:bg-indigo-700"
          >
            {showForm ? "Cancel" : "+ Add Transaction"}
          </button>
        </header>

        <section className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <p className="text-sm text-slate-500">Total Income</p>
            <p className="mt-3 text-2xl font-bold text-emerald-600">
              {money(totalIncome)}
            </p>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <p className="text-sm text-slate-500">Total Expenses</p>
            <p className="mt-3 text-2xl font-bold text-rose-600">
              {money(totalExpenses)}
            </p>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:col-span-2 lg:col-span-1">
            <p className="text-sm text-slate-500">Net Balance</p>
            <p
              className={`mt-3 text-2xl font-bold ${
                totalIncome - totalExpenses >= 0
                  ? "text-indigo-600"
                  : "text-rose-600"
              }`}
            >
              {money(totalIncome - totalExpenses)}
            </p>
          </div>
        </section>

        {error && !showForm && (
          <p className="mb-6 rounded-xl bg-rose-50 p-4 text-sm text-rose-700" role="alert">
            {error}
          </p>
        )}

        {showForm && (
          <section className="mb-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="mb-5 text-xl font-bold">Add a transaction</h2>

            <form onSubmit={addTransaction} className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              <div>
                <label className="mb-2 block text-sm font-medium">
                  Description
                </label>
                <input
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  placeholder="e.g. Grocery shopping"
                  className="w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-indigo-500"
                  required
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium">
                  Amount (₹)
                </label>
                <input
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={amount}
                  onChange={(event) => setAmount(event.target.value)}
                  placeholder="Enter amount"
                  className="w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-indigo-500"
                  required
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium">Type</label>
                <select
                  value={type}
                  onChange={(event) =>
                    setType(event.target.value as "Income" | "Expense")
                  }
                  className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3"
                >
                  <option value="Expense">Expense</option>
                  <option value="Income">Income</option>
                </select>
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium">
                  Category
                </label>
                <select
                  value={categoryId}
                  onChange={(event) => setCategoryId(event.target.value)}
                  className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3"
                >
                  {formCategories.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium">Date</label>
                <input
                  type="date"
                  value={date}
                  onChange={(event) => setDate(event.target.value)}
                  className="w-full rounded-xl border border-slate-300 px-4 py-3"
                  required
                />
              </div>

              <div className="flex items-end">
                <button
                  type="submit"
                  disabled={saving}
                  className="w-full rounded-xl bg-indigo-600 px-5 py-3 font-semibold text-white hover:bg-indigo-700 disabled:opacity-60"
                >
                  {saving ? "Saving..." : "Save Transaction"}
                </button>
              </div>

              {error && (
                <p className="text-sm text-rose-600 sm:col-span-2 lg:col-span-3">
                  {error}
                </p>
              )}
            </form>
          </section>
        )}

        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-200 p-5">
            <h2 className="text-xl font-bold">All Transactions</h2>
            <p className="mt-1 text-sm text-slate-500">
              {filteredTransactions.length} transaction(s) found
            </p>

            <div className="mt-5 grid gap-3 md:grid-cols-3">
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search description or category..."
                className="rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-indigo-500"
              />

              <select
                value={typeFilter}
                onChange={(event) => setTypeFilter(event.target.value)}
                className="rounded-xl border border-slate-300 bg-white px-4 py-3"
              >
                <option value="All">All transaction types</option>
                <option value="Income">Income only</option>
                <option value="Expense">Expenses only</option>
              </select>

              <select
                value={categoryFilter}
                onChange={(event) => setCategoryFilter(event.target.value)}
                className="rounded-xl border border-slate-300 bg-white px-4 py-3"
              >
                <option value="All">All categories</option>
                {categories.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-6 py-4">Description</th>
                  <th className="px-6 py-4">Category</th>
                  <th className="px-6 py-4">Date</th>
                  <th className="px-6 py-4">Type</th>
                  <th className="px-6 py-4 text-right">Amount</th>
                  <th className="px-6 py-4 text-right">Action</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100">
                {filteredTransactions.map((transaction) => (
                  <tr key={transaction.id} className="hover:bg-slate-50">
                    <td className="px-6 py-4 font-semibold">
                      {transaction.title}
                    </td>
                    <td className="px-6 py-4 text-slate-600">
                      {transaction.category}
                    </td>
                    <td className="px-6 py-4 text-slate-600">
                      {transaction.date}
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`rounded-full px-3 py-1 text-xs font-semibold ${
                          transaction.type === "Income"
                            ? "bg-emerald-100 text-emerald-700"
                            : "bg-rose-100 text-rose-700"
                        }`}
                      >
                        {transaction.type}
                      </span>
                    </td>
                    <td
                      className={`px-6 py-4 text-right font-semibold ${
                        transaction.type === "Income"
                          ? "text-emerald-600"
                          : "text-rose-600"
                      }`}
                    >
                      {transaction.type === "Income" ? "+" : "-"}
                      {money(transaction.amount)}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() => deleteTransaction(transaction)}
                        className="font-medium text-rose-600 hover:text-rose-800"
                        aria-label={`Delete ${transaction.title}`}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}

                {filteredTransactions.length === 0 && (
                  <tr>
                    <td
                      colSpan={6}
                      className="px-6 py-12 text-center text-slate-500"
                    >
                      {loading
                        ? "Loading transactions..."
                        : "No transactions found. Try changing your search or filters."}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

      </div>
    </main>
  );
}
