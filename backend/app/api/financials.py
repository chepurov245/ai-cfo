from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.services.financial_service import (
    calculate_cash_flow,
    calculate_expenses_by_category,
    calculate_kpi,
    calculate_revenue_by_category,
    calculate_summary,
    get_company,
    get_transactions,
    validate_date_range,
)


router = APIRouter(
    prefix="/financials",
    tags=["Financials"],
)


@router.get("/summary")
def get_financial_summary(
    company_id: int,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):
    validate_date_range(
        start_date,
        end_date,
    )

    company = get_company(
        db=db,
        company_id=company_id,
        current_user=current_user,
    )

    transactions = get_transactions(
        db=db,
        company_id=company.id,
        start_date=start_date,
        end_date=end_date,
    )

    summary = calculate_summary(
        transactions
    )

    expenses_by_category = (
        calculate_expenses_by_category(
            transactions
        )
    )

    return {
        "company_id": company.id,
        "currency": company.currency,
        "start_date": start_date,
        "end_date": end_date,
        "total_income": summary[
            "total_income"
        ],
        "total_expense": summary[
            "total_expense"
        ],
        "profit": summary["profit"],
        "profit_margin": summary[
            "profit_margin"
        ],
        "transaction_count": summary[
            "transaction_count"
        ],
        "expenses_by_category": (
            expenses_by_category
        ),
    }


@router.get("/cash-flow")
def get_cash_flow(
    company_id: int,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):
    validate_date_range(
        start_date,
        end_date,
    )

    company = get_company(
        db=db,
        company_id=company_id,
        current_user=current_user,
    )

    transactions = get_transactions(
        db=db,
        company_id=company.id,
        start_date=start_date,
        end_date=end_date,
    )

    cash_flow = calculate_cash_flow(
        transactions
    )

    return {
        "company_id": company.id,
        "currency": company.currency,
        "start_date": start_date,
        "end_date": end_date,
        "cash_inflow": cash_flow[
            "cash_inflow"
        ],
        "cash_outflow": cash_flow[
            "cash_outflow"
        ],
        "net_cash_flow": cash_flow[
            "net_cash_flow"
        ],
        "transaction_count": len(
            transactions
        ),
    }


@router.get("/expenses")
def get_expense_analytics(
    company_id: int,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):
    validate_date_range(
        start_date,
        end_date,
    )

    company = get_company(
        db=db,
        company_id=company_id,
        current_user=current_user,
    )

    transactions = get_transactions(
        db=db,
        company_id=company.id,
        start_date=start_date,
        end_date=end_date,
    )

    expenses = (
        calculate_expenses_by_category(
            transactions
        )
    )

    total_expense = sum(
        expenses.values()
    )

    categories = []

    for category, amount in expenses.items():

        if total_expense > 0:
            percentage = (
                amount
                / total_expense
            ) * 100
        else:
            percentage = 0

        categories.append(
            {
                "category": category,
                "amount": amount,
                "percentage": round(
                    percentage,
                    2,
                ),
            }
        )

    return {
        "company_id": company.id,
        "currency": company.currency,
        "start_date": start_date,
        "end_date": end_date,
        "total_expense": total_expense,
        "categories": categories,
    }


@router.get("/revenue")
def get_revenue_analytics(
    company_id: int,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):
    validate_date_range(
        start_date,
        end_date,
    )

    company = get_company(
        db=db,
        company_id=company_id,
        current_user=current_user,
    )

    transactions = get_transactions(
        db=db,
        company_id=company.id,
        start_date=start_date,
        end_date=end_date,
    )

    revenue = (
        calculate_revenue_by_category(
            transactions
        )
    )

    total_income = sum(
        revenue.values()
    )

    categories = []

    for category, amount in revenue.items():

        if total_income > 0:
            percentage = (
                amount
                / total_income
            ) * 100
        else:
            percentage = 0

        categories.append(
            {
                "category": category,
                "amount": amount,
                "percentage": round(
                    percentage,
                    2,
                ),
            }
        )

    return {
        "company_id": company.id,
        "currency": company.currency,
        "start_date": start_date,
        "end_date": end_date,
        "total_income": total_income,
        "categories": categories,
    }


@router.get("/kpi")
def get_financial_kpi(
    company_id: int,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):
    validate_date_range(
        start_date,
        end_date,
    )

    company = get_company(
        db=db,
        company_id=company_id,
        current_user=current_user,
    )

    transactions = get_transactions(
        db=db,
        company_id=company.id,
        start_date=start_date,
        end_date=end_date,
    )

    kpi = calculate_kpi(
        transactions
    )

    return {
        "company_id": company.id,
        "currency": company.currency,
        "start_date": start_date,
        "end_date": end_date,
        **kpi,
    }