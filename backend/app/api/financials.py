from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database.session import get_db
from app.models.company import Company
from app.models.transaction import Transaction
from app.models.user import User


router = APIRouter(
    prefix="/financials",
    tags=["Financials"]
)


@router.get("/summary")
def get_financial_summary(
    company_id: int,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    company = (
        db.query(Company)
        .filter(
            Company.id == company_id,
            Company.owner_id == current_user.id
        )
        .first()
    )

    if not company:
        raise HTTPException(
            status_code=404,
            detail="Company not found"
        )

    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date must be before end_date"
        )

    query = (
        db.query(Transaction)
        .filter(Transaction.company_id == company.id)
    )

    if start_date:
        query = query.filter(
            Transaction.transaction_date >= start_date
        )

    if end_date:
        query = query.filter(
            Transaction.transaction_date <= end_date
        )

    transactions = query.all()

    total_income = sum(
        (
            transaction.amount
            for transaction in transactions
            if transaction.type == "income"
        ),
        Decimal("0")
    )

    total_expense = sum(
        (
            transaction.amount
            for transaction in transactions
            if transaction.type == "expense"
        ),
        Decimal("0")
    )

    profit = total_income - total_expense

    if total_income > 0:
        profit_margin = (
            profit / total_income
        ) * Decimal("100")
    else:
        profit_margin = Decimal("0")

    expenses_by_category = {}

    for transaction in transactions:
        if transaction.type != "expense":
            continue

        category = transaction.category

        if category not in expenses_by_category:
            expenses_by_category[category] = Decimal("0")

        expenses_by_category[category] += transaction.amount

    expenses_by_category = dict(
        sorted(
            expenses_by_category.items(),
            key=lambda item: item[1],
            reverse=True
        )
    )

    return {
        "company_id": company.id,
        "currency": company.currency,
        "start_date": start_date,
        "end_date": end_date,
        "total_income": total_income,
        "total_expense": total_expense,
        "profit": profit,
        "profit_margin": round(profit_margin, 2),
        "transaction_count": len(transactions),
        "expenses_by_category": expenses_by_category
    }