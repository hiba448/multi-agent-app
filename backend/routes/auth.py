from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import or_

from db.models import engine, Student

router = APIRouter()


class RegisterRequest(BaseModel):
    name: str
    username: str
    email: str
    password: str


class AuthResponse(BaseModel):
    student_id: int
    name: str
    username: str
    email: str


class LoginRequest(BaseModel):
    username_or_email: str
    password: str


@router.post("/register", response_model=AuthResponse)
def register(request: RegisterRequest):
    with DBSession(engine) as session:
        existing_user = session.query(Student).filter(
            or_(
                Student.username == request.username,
                Student.email == request.email
            )
        ).first()

        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Username or email already exists."
            )

        student = Student(
            name=request.name,
            full_name=request.name,
            username=request.username,
            email=request.email,
            password_hash=request.password
        )

        session.add(student)
        session.commit()
        session.refresh(student)

        return AuthResponse(
            student_id=student.id,
            name=student.name,
            username=student.username,
            email=student.email
        )


@router.post("/login", response_model=AuthResponse)
def login(request: LoginRequest):
    with DBSession(engine) as session:
        student = session.query(Student).filter(
            or_(
                Student.username == request.username_or_email,
                Student.email == request.username_or_email
            )
        ).first()

        if not student:
            raise HTTPException(
                status_code=401,
                detail="Invalid username/email or password."
            )

        if student.password_hash != request.password:
            raise HTTPException(
                status_code=401,
                detail="Invalid username/email or password."
            )

        return AuthResponse(
            student_id=student.id,
            name=student.name,
            username=student.username,
            email=student.email
        )