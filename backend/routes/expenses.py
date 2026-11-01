from routes.transaction_router import build_transaction_router

router = build_transaction_router("expense", "/expenses", "Expenses")
