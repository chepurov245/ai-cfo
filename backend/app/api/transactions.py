from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database.session import get_db
from app.models.company import Company
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.transaction import TransactionCreate


router = APIRouter(
    prefix="/transactions",
    tags=["Transactions"]
)


@router.post("")
def create_transaction(
    request: TransactionCreate,
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

    transaction = Transaction(
        company_id=company.id,
        type=request.type,
        amount=request.amount,
        category=request.category,
        description=request.description,
        transaction_date=request.transaction_date
    )

    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    return {
        "id": transaction.id,
        "company_id": transaction.company_id,
        "type": transaction.type,
        "amount": transaction.amount,
        "category": transaction.category,
        "description": transaction.description,
        "transaction_date": transaction.transaction_date
    }


@router.get("")
def get_transactions(
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
        .order_by(Transaction.transaction_date.desc())
        .all()
    )

    return [
        {
            "id": transaction.id,
            "company_id": transaction.company_id,
            "type": transaction.type,
            "amount": transaction.amount,
            "category": transaction.category,
            "description": transaction.description,
            "transaction_date": transaction.transaction_date
        }
        for transaction in transactions
    ]