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

    transactions = (
        db.query(Transaction)
        .filter(Transaction.company_id == company.id)
        .all()
    )

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

    return {
        "company_id": company.id,
        "currency": company.currency,
        "total_income": total_income,
        "total_expense": total_expense,
        "profit": profit,
        "transaction_count": len(transactions)
    }