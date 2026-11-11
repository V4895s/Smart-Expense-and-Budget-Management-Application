
"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import SignOutButton from "@/components/SignOutButton";
import BudgetAlerts from "@/components/BudgetAlerts";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

type Transaction = {
  id: string;
  type: "income" | "expense";
  amount: number;
};

type Budget = {
  id: string;
  category_id: string;
  amount: number;
  period: "weekly" | "monthly";
  spent: number;
  remaining: number;
};

function formatMoney(amount: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(amount);
}

export default function Home() {
  const [loggedIn, setLoggedIn] = useState(false);
  const [userName, setUserName] = useState("");

  const [availableBalance, setAvailableBalance] = useState(0);
  const [remainingBudget, setRemainingBudget] = useState(0);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadDashboard = useCallback(async () => {
    const token = localStorage.getItem("pennywise-access-token");

    if (!token) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError("");

    
      const headers = {
        Authorization: `Bearer ${token}`,
      };

      const [transactionsResponse, budgetsResponse] =
        await Promise.all([
          fetch(`${API_URL}/transactions`, { headers }),
          fetch(`${API_URL}/budgets`, { headers }),
        ]);

      if (!transactionsResponse.ok) {
        throw new Error("Could not load transactions.");
      }

      if (!budgetsResponse.ok) {
        throw new Error("Could not load budgets.");
      }

      const transactions: Transaction[] =
        await transactionsResponse.json();

      const budgets: Budget[] = await budgetsResponse.json();

      const totalIncome = transactions
        .filter((transaction) => transaction.type === "income")
        .reduce(
          (sum, transaction) => sum + Number(transaction.amount),
          0
        );

      const totalExpenses = transactions
        .filter((transaction) => transaction.type === "expense")
        .reduce(
          (sum, transaction) => sum + Number(transaction.amount),
          0
        );

      // Keep only one budget per category.
      // Monthly takes priority over weekly to avoid overlapping spending.
      const budgetsByCategory = new Map<string, Budget>();

      budgets.forEach((budget) => {
        const existing = budgetsByCategory.get(budget.category_id);

        if (
          !existing ||
          (budget.period === "monthly" && existing.period === "weekly")
        ) {
          budgetsByCategory.set(budget.category_id, budget);
        }
      });

      const remaining = Array.from(budgetsByCategory.values()).reduce(
        (sum, budget) => sum + Number(budget.remaining),
        0
      );

      setAvailableBalance(totalIncome - totalExpenses);
      setRemainingBudget(remaining);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Something went wrong while loading dashboard data."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const token = localStorage.getItem("pennywise-access-token");
    const status = localStorage.getItem("pennywise-logged-in");

    if (token && status === "true") {
      setLoggedIn(true);
      setUserName(
        localStorage.getItem("pennywise-user-name") || "User"
      );
      loadDashboard();
    } else {
      setLoading(false);
    }
  }, [loadDashboard]);

  if (!loggedIn) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#f6f7fb] p-5">
        <section className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm sm:p-10">
          <p className="text-sm font-semibold uppercase tracking-[0.22em] text-indigo-600">
            PennyWise
          </p>

          <h1 className="mt-4 text-3xl font-bold text-slate-900 sm:text-4xl">
            Welcome to smart money management
          </h1>

          <p className="mt-3 text-sm text-slate-500 sm:text-base">
            Please sign in to continue, or create a new account to get started.
          </p>

          <div className="mt-8 grid gap-3 sm:grid-cols-2">
            <Link
              href="/login"
              className="rounded-xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white hover:bg-slate-700"
            >
              Log in
            </Link>

            <Link
              href="/register"
              className="rounded-xl border border-indigo-200 bg-indigo-50 px-5 py-3 text-sm font-semibold text-indigo-700 hover:bg-indigo-100"
            >
              Sign up
            </Link>
          </div>
        </section>
      </main>
    );
  }

  const sections = [
    {
      name: "Transactions",
      description: "Manage your income and expenses",
      href: "/transactions",
    },
    {
      name: "Budgets",
      description: "Track your spending limits",
      href: "/budgets",
    },
    {
      name: "Reports",
      description: "Review your financial reports",
      href: "/reports",
    },
    {
      name: "Savings Goals",
      description: "Set targets and track your savings",
      href: "/goals",
    },
    {
       name: "Recurring",
      description: "Automate salary, rent and subscriptions",
      href: "/recurring",
    },
    {
      name: "Profile",
      description: "Manage your account",
      href: "/profile",
    },
  ];

  return (
    <main className="min-h-screen bg-[#f6f7fb] p-6 sm:p-10">
      <div className="mx-auto max-w-6xl">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-sm font-semibold uppercase tracking-widest text-indigo-600">
              PennyWise
            </p>
            <h1 className="mt-2 text-3xl font-bold text-slate-900">
              Welcome, {userName}!
            </h1>
            <p className="mt-2 text-slate-500">
              Your personal finance dashboard
            </p>
          </div>

          <SignOutButton />
        </header>

        {/* Financial summary */}
        <section className="mt-10">
          <h2 className="text-xl font-semibold text-slate-900">
            Financial overview
          </h2>

          {error && (
            <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
              {error}
              <button
                onClick={loadDashboard}
                className="ml-2 font-semibold underline"
              >
                Retry
              </button>
            </div>
          )}

          <div className="mt-5 grid gap-5 sm:grid-cols-2">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <p className="text-sm font-medium text-slate-500">
                Available balance
              </p>

              <p
                className={`mt-3 text-2xl font-bold ${
                  availableBalance < 0 ? "text-rose-600" : "text-slate-900"
                }`}
              >
                {loading ? "Loading..." : formatMoney(availableBalance)}
              </p>
              
              <p className="mt-2 text-sm text-slate-500">
                Total income minus total expenses
              </p>
            </div>
              
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <p className="text-sm font-medium text-slate-500">
                Remaining budget
              </p>
              
              <p
                className={`mt-3 text-2xl font-bold ${
                  remainingBudget < 0 ? "text-rose-600" : "text-indigo-600"
                }`}
              >
                {loading ? "Loading..." : formatMoney(remainingBudget)}
              </p>
              
              <p className="mt-2 text-sm text-slate-500">
                Based on your active category budgets
              </p>
            </div>
          </div>
        </section>
        <BudgetAlerts />
        {/* Workspace */}
        <section className="mt-10">
          <h2 className="text-xl font-semibold text-slate-900">
            Your workspace
          </h2>

          <div className="mt-5 grid gap-5 sm:grid-cols-2 lg:grid-cols-5">
            {sections.map((section) => (
              <Link
                key={section.href}
                href={section.href}
                className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition hover:-translate-y-1 hover:shadow-md"
              >
                <h3 className="text-lg font-semibold text-slate-900">
                  {section.name}
                </h3>

                <p className="mt-2 text-sm text-slate-500">
                  {section.description}
                </p>

                <p className="mt-5 text-sm font-semibold text-indigo-600">
                  Open section →
                </p>
              </Link>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
