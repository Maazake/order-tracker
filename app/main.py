from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app import services
from app.database import get_db
from app.exceptions import ConflictError, NotFoundError
from app.models import EmployeeDB, OrderDB, OrderStepDB, UserDB
from app.schemas import (
    Employee,
    EmployeeResponse,
    Order,
    OrderResponse,
    OrderStepResponse,
    SortOrder,
    StepComplete,
    StepStart,
    StepStatus,
    Token,
    UserCreate,
    UserResponse,
    UserRole,
)
from app.security import (
    create_access_token,
    get_current_user,
    hash_password,
    require_admin,
    verify_password,
)

DbSession = Annotated[Session, Depends(get_db)]

app = FastAPI()


@app.exception_handler(NotFoundError)
async def handle_not_found(request: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ConflictError)
async def handle_conflict_error(request: Request, exc: ConflictError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.get("/orders", response_model=list[OrderResponse])
def get_all_orders(
    db: DbSession,
    _: Annotated[UserDB, Depends(get_current_user)],
    step_status: Annotated[StepStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    offset: Annotated[int, Query(ge=0)] = 0,
    sort: Annotated[SortOrder, Query()] = SortOrder.ID,
    desc: bool = False,
):
    query = select(OrderDB)
    if step_status is not None:
        query = query.where(OrderDB.steps.any(OrderStepDB.status == step_status))

    columns = {
        SortOrder.ID: OrderDB.id,
        SortOrder.COUNT: OrderDB.count,
        SortOrder.ELEMENT_NAME: OrderDB.element_name,
        SortOrder.PLANNED_COMPLETION_DATE: OrderDB.planned_completion_date,
    }
    column = columns[sort]

    if desc:
        column = column.desc()

    return db.scalars(
        query.order_by(column, OrderDB.id)
        .limit(limit)
        .offset(offset)
        .options(
            selectinload(OrderDB.steps).selectinload(OrderStepDB.assigned_employee)
        )
    ).all()


def find_order_or_404(order_id: int, db: Session, options=None):
    order = db.get(
        OrderDB,
        order_id,
        options=options,
    )
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order ID {order_id} does not exist",
        )
    return order


@app.get("/orders/{order_id}", response_model=OrderResponse)
def get_single_order(
    order_id: int,
    db: DbSession,
    _: Annotated[UserDB, Depends(get_current_user)],
):
    order = find_order_or_404(
        order_id,
        db,
        options=[
            selectinload(OrderDB.steps).selectinload(OrderStepDB.assigned_employee)
        ],
    )
    return order


@app.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_new_order(
    order_data: Order, db: DbSession, _: Annotated[UserDB, Depends(require_admin)]
):

    new_order = services.create_order(db, order_data)

    db.commit()
    db.refresh(new_order)
    return new_order


@app.post("/steps/{step_id}/start", response_model=OrderStepResponse)
def start_step(
    step_id: int,
    db: DbSession,
    data: StepStart,
    _: Annotated[UserDB, Depends(get_current_user)],
):
    step = services.start_step(db, step_id, data.employee_id)
    db.commit()
    db.refresh(step)
    return step


@app.post("/steps/{step_id}/complete", response_model=OrderStepResponse)
def complete_step(
    step_id: int,
    data: StepComplete,
    db: DbSession,
    _: Annotated[UserDB, Depends(get_current_user)],
):
    step = services.complete_step(db, step_id, data.note)
    db.commit()
    db.refresh(step)
    return step


@app.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(
    order_id: int,
    db: DbSession,
    _: Annotated[UserDB, Depends(require_admin)],
):
    order = find_order_or_404(order_id, db)
    db.delete(order)
    db.commit()


@app.get("/employees", response_model=list[EmployeeResponse])
def get_all_employees(db: DbSession, _: Annotated[UserDB, Depends(require_admin)]):
    return db.scalars(select(EmployeeDB).order_by(EmployeeDB.id)).all()


@app.post(
    "/employees", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED
)
def create_new_employee(
    employee_data: Employee, db: DbSession, _: Annotated[UserDB, Depends(require_admin)]
):

    new_employee = EmployeeDB(**employee_data.model_dump())
    db.add(new_employee)
    db.commit()
    db.refresh(new_employee)
    return new_employee


@app.post(
    "/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def register_user(user_in: UserCreate, db: DbSession):
    user = db.scalars(select(UserDB).where(UserDB.username == user_in.username)).first()
    if user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already registered",
        )

    hashed = hash_password(user_in.password)
    new_user = UserDB(
        username=user_in.username, hashed_password=hashed, role=UserRole.OPERATOR
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.post("/auth/login", response_model=Token)
def login_for_access_token(
    db: DbSession, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
):
    user = db.scalars(
        select(UserDB).where(UserDB.username == form_data.username)
    ).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value}
    )

    return Token(access_token=access_token, token_type="bearer")


@app.get("/users/me", response_model=UserResponse)
def get_me(current_user: Annotated[UserDB, Depends(get_current_user)]):
    return current_user


@app.get("/users", response_model=list[UserResponse])
def get_all_users(db: DbSession, _: Annotated[UserDB, Depends(require_admin)]):
    return db.scalars(select(UserDB)).all()
