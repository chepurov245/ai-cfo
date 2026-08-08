from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database.session import get_db
from app.models.company import Company
from app.models.user import User
from app.schemas.company import CompanyCreate


router = APIRouter(
    prefix="/companies",
    tags=["Companies"]
)


@router.post("")
def create_company(
    request: CompanyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    company = Company(
        owner_id=current_user.id,
        name=request.name,
        currency=request.currency.upper()
    )

    db.add(company)
    db.commit()
    db.refresh(company)

    return {
        "id": company.id,
        "name": company.name,
        "currency": company.currency,
        "owner_id": company.owner_id
    }


@router.get("")
def get_companies(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    companies = (
        db.query(Company)
        .filter(Company.owner_id == current_user.id)
        .order_by(Company.id.asc())
        .all()
    )

    return [
        {
            "id": company.id,
            "name": company.name,
            "currency": company.currency,
            "owner_id": company.owner_id
        }
        for company in companies
    ]