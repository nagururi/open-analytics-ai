from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.core.database import get_metadata_connection
from app.core.security import (
    hash_password, verify_password, create_access_token, get_current_user
)

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

@router.post("/login")
def login(req: LoginRequest):
    conn = get_metadata_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE username=? AND is_active=1", (req.username,)
    ).fetchone()
    conn.close()
    if not user or not verify_password(req.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": req.username, "role": user["role"]})
    return {"access_token": token, "token_type": "bearer",
            "user": {"username": user["username"], "email": user["email"], "role": user["role"]}}

@router.post("/register")
def register(req: RegisterRequest):
    conn = get_metadata_connection()
    try:
        conn.execute(
            "INSERT INTO users (username, email, hashed_password) VALUES (?,?,?)",
            (req.username, req.email, hash_password(req.password))
        )
        conn.commit()
    except Exception:
        raise HTTPException(status_code=400, detail="Username or email already exists")
    finally:
        conn.close()
    token = create_access_token({"sub": req.username, "role": "viewer"})
    return {"access_token": token, "token_type": "bearer",
            "user": {"username": req.username, "email": req.email, "role": "viewer"}}

@router.get("/me")
def me(user=Depends(get_current_user)):
    return {"username": user["username"], "email": user["email"], "role": user["role"]}
