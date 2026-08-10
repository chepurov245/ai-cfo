from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.transaction import Transaction
from app.models.user import User


def get_company(
    db: Session,
    company_id: int,
    current_user: User,
) -> Company:
    company = (
        db.query(Company)
        .filter(
            Company.id == company_id,
            Company.owner_id == current_user.id,
        )
        .first()
    )

    if not company:
        raise HTTPException(
            status_code=404,
            detail="Company not found",
        )

    return company


def validate_date_range(
    start_date: datetime | None,
    end_date: datetime | None,
) -> None:
    if (
        start_date
        and end_date
        and start_date > end_date
    ):
        raise HTTPException(
            status_code=400,
            detail="start_date must be before end_date",
        )


def get_transactions(
    db: Session,
    company_id: int,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
):
    query = (
        db.query(Transaction)
        .filter(
            Transaction.company_id == company_id
        )
    )

    if start_date:
        query = query.filter(
            Transaction.transaction_date >= start_date
        )

    if end_date:
        query = query.filter(
            Transaction.transaction_date <= end_date
        )

    return query.order_by(
        Transaction.transaction_date.asc()
    ).all()


def calculate_summary(
    transactions,
):
    total_income = sum(
        (
            transaction.amount
            for transaction in transactions
            if transaction.type == "income"
        ),
        Decimal("0"),
    )

    total_expense = sum(
        (
            transaction.amount
            for transaction in transactions
            if transaction.type == "expense"
        ),
        Decimal("0"),
    )

    profit = (
        total_income
        - total_expense
    )

    if total_income > 0:
        profit_margin = (
            profit / total_income
        ) * Decimal("100")
    else:
        profit_margin = Decimal("0")

    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "profit": profit,
        "profit_margin": round(
            profit_margin,
            2,
        ),
        "transaction_count": len(
            transactions
        ),
    }


def calculate_expenses_by_category(
    transactions,
):
    expenses_by_category = {}

    for transaction in transactions:
        if transaction.type != "expense":
            continue

        category = (
            transaction.category
            or "uncategorized"
        )

        if category not in expenses_by_category:
            expenses_by_category[category] = (
                Decimal("0")
            )

        expenses_by_category[category] += (
            transaction.amount
        )

    return dict(
        sorted(
            expenses_by_category.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    )


def calculate_revenue_by_category(
    transactions,
):
    revenue_by_category = {}

    for transaction in transactions:
        if transaction.type != "income":
            continue

        category = (
            transaction.category
            or "uncategorized"
        )

        if category not in revenue_by_category:
            revenue_by_category[category] = (
                Decimal("0")
            )

        revenue_by_category[category] += (
            transaction.amount
        )

    return dict(
        sorted(
            revenue_by_category.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    )


def calculate_cash_flow(
    transactions,
):
    cash_inflow = sum(
        (
            transaction.amount
            for transaction in transactions
            if transaction.type == "income"
        ),
        Decimal("0"),
    )

    cash_outflow = sum(
        (
            transaction.amount
            for transaction in transactions
            if transaction.type == "expense"
        ),
        Decimal("0"),
    )

    net_cash_flow = (
        cash_inflow
        - cash_outflow
    )

    return {
        "cash_inflow": cash_inflow,
        "cash_outflow": cash_outflow,
        "net_cash_flow": net_cash_flow,
    }


def calculate_kpi(
    transactions,
):
    summary = calculate_summary(
        transactions
    )

    transaction_count = (
        summary["transaction_count"]
    )

    income_transactions = [
        transaction
        for transaction in transactions
        if transaction.type == "income"
    ]

    expense_transactions = [
        transaction
        for transaction in transactions
        if transaction.type == "expense"
    ]

    if income_transactions:
        average_income_transaction = (
            summary["total_income"]
            / Decimal(
                str(len(income_transactions))
            )
        )
    else:
        average_income_transaction = (
            Decimal("0")
        )

    if expense_transactions:
        average_expense_transaction = (
            summary["total_expense"]
            / Decimal(
                str(len(expense_transactions))
            )
        )
    else:
        average_expense_transaction = (
            Decimal("0")
        )

    if transaction_count > 0:
        average_transaction = (
            (
                summary["total_income"]
                + summary["total_expense"]
            )
            / Decimal(
                str(transaction_count)
            )
        )
    else:
        average_transaction = Decimal("0")

    return {
        "transaction_count": transaction_count,
        "income_transaction_count": len(
            income_transactions
        ),
        "expense_transaction_count": len(
            expense_transactions
        ),
        "average_income_transaction": (
            round(
                average_income_transaction,
                2,
            )
        ),
        "average_expense_transaction": (
            round(
                average_expense_transaction,
                2,
            )
        ),
        "average_transaction": round(
            average_transaction,
            2,
        ),
        "profit": summary["profit"],
        "profit_margin": summary["profit_margin"],
    }


def calculate_forecast(
    transactions,
    forecast_days: int,
):
    """
    Рассчитывает простой прогноз на основе
    средней дневной финансовой активности.

    Прогноз не является фактическими данными
    и не записывается в transactions.
    """

    if forecast_days <= 0:
        raise HTTPException(
            status_code=400,
            detail="forecast_days must be greater than 0",
        )

    if not transactions:
        raise HTTPException(
            status_code=400,
            detail=(
                "Forecast cannot be calculated "
                "because there are no transactions."
            ),
        )

    first_transaction_date = min(
        transaction.transaction_date
        for transaction in transactions
    )

    last_transaction_date = max(
        transaction.transaction_date
        for transaction in transactions
    )

    historical_days = (
        last_transaction_date.date()
        - first_transaction_date.date()
    ).days + 1

    if historical_days <= 0:
        historical_days = 1

    total_income = sum(
        (
            transaction.amount
            for transaction in transactions
            if transaction.type == "income"
        ),
        Decimal("0"),
    )

    total_expense = sum(
        (
            transaction.amount
            for transaction in transactions
            if transaction.type == "expense"
        ),
        Decimal("0"),
    )

    historical_profit = (
        total_income
        - total_expense
    )

    average_daily_income = (
        total_income
        / Decimal(str(historical_days))
    )

    average_daily_expense = (
        total_expense
        / Decimal(str(historical_days))
    )

    average_daily_profit = (
        historical_profit
        / Decimal(str(historical_days))
    )

    forecast_income = (
        average_daily_income
        * Decimal(str(forecast_days))
    )

    forecast_expense = (
        average_daily_expense
        * Decimal(str(forecast_days))
    )

    forecast_profit = (
        forecast_income
        - forecast_expense
    )

    forecast_net_cash_flow = (
        forecast_profit
    )

    if historical_days < 7:
        confidence = "low"
    elif historical_days < 30:
        confidence = "medium"
    else:
        confidence = "high"

    return {
        "historical_days": historical_days,
        "historical_start_date": (
            first_transaction_date
        ),
        "historical_end_date": (
            last_transaction_date
        ),
        "confidence": confidence,
        "average_daily_income": round(
            average_daily_income,
            2,
        ),
        "average_daily_expense": round(
            average_daily_expense,
            2,
        ),
        "average_daily_profit": round(
            average_daily_profit,
            2,
        ),
        "forecast_income": round(
            forecast_income,
            2,
        ),
        "forecast_expense": round(
            forecast_expense,
            2,
        ),
        "forecast_profit": round(
            forecast_profit,
            2,
        ),
        "forecast_net_cash_flow": round(
            forecast_net_cash_flow,
            2,
        ),
    }