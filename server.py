from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, date
import io
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import bcrypt
import jwt


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

JWT_SECRET = os.environ.get('JWT_SECRET', 'ayder-app-secret-key-2025')
SMTP_EMAIL = os.environ.get('SMTP_EMAIL', '')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))

import random
import string

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', '')
if not mongo_url:
    print("WARNING: MONGO_URL not set. Please add it in Railway Variables tab.")
    # Use a placeholder so the server can at least start for healthcheck
    mongo_url = "mongodb://localhost:27017"
client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=5000)
db = client[os.environ.get('DB_NAME', 'ayder_production')]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

from fastapi import Header

# Helper to get user_id from request header
def get_user_id(x_user_id: str = Header(default="")) -> str:
    return x_user_id


# Define Models

# Auth Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    password_hash: str
    name: str = ""
    role: str = "user"  # user, admin
    verified: bool = False
    accepted_terms: bool = False
    accepted_terms_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str = ""

class LoginRequest(BaseModel):
    email: str
    password: str

class VerifyRequest(BaseModel):
    email: str
    code: str

class ResendCodeRequest(BaseModel):
    email: str

class AcceptTermsRequest(BaseModel):
    email: str
class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str = ""
    location: str = ""
    date: str
    completed: bool = False
    completed_notes: str = ""
    completed_photo: str = ""
    completed_at: Optional[str] = None
    order: int = 0
    user_id: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)

class TaskCreate(BaseModel):
    title: str
    description: str = ""
    location: str = ""
    date: str  # ISO date string YYYY-MM-DD

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    date: Optional[str] = None
    completed: Optional[bool] = None
    completed_notes: Optional[str] = None
    completed_photo: Optional[str] = None
    completed_at: Optional[str] = None
    order: Optional[int] = None

class TaskReorder(BaseModel):
    task_ids: List[str]  # Ordered list of task IDs

class TaskCompleteRequest(BaseModel):
    notes: str = ""
    photo: str = ""  # Base64 encoded photo

class Client(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    organization: str = ""
    service_type: str = "Domestic Assistance"
    schedule: str = "Mon – Fri | 09:00 – 01:00 PM"
    days_left: int = 30
    avatar: str = ""  # Base64 encoded image
    email: str = ""
    phone: str = ""
    address: str = ""
    postcode: str = ""
    ndis_number: str = ""
    notes: str = ""
    archived: bool = False
    user_id: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ClientCreate(BaseModel):
    name: str
    organization: str = ""
    service_type: str = "Domestic Assistance"
    schedule: str = "Mon – Fri | 09:00 – 01:00 PM"
    days_left: int = 30
    avatar: str = ""
    email: str = ""
    phone: str = ""
    address: str = ""
    postcode: str = ""
    ndis_number: str = ""
    notes: str = ""
    archived: bool = False

class ClientUpdate(BaseModel):
    name: Optional[str] = None
    organization: Optional[str] = None
    service_type: Optional[str] = None
    schedule: Optional[str] = None
    days_left: Optional[int] = None
    avatar: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    postcode: Optional[str] = None
    ndis_number: Optional[str] = None
    notes: Optional[str] = None
    archived: Optional[bool] = None

class UserProfile(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    bio: str = ""
    phone: str = ""
    email: str = ""
    avatar: str = ""
    open_to_work: bool = True
    weekday_rate: str = ""
    weekend_rate: str = ""
    holiday_rate: str = ""
    # NDIS Provider fields
    business_name: str = ""
    abn: str = ""
    business_email: str = ""
    business_address: str = ""
    business_city: str = ""
    business_state: str = ""
    business_postcode: str = ""
    # Payment details
    payment_account_name: str = ""
    payment_bsb: str = ""
    payment_account_number: str = ""
    availability: dict = Field(default_factory=lambda: {
        "Monday": "Add details",
        "Tuesday": "Add details",
        "Wednesday": "Add details",
        "Thursday": "Add details",
        "Friday": "Add details",
        "Saturday": "Add details",
        "Sunday": "Add details",
    })
    about_me_tags: list = Field(default_factory=list)
    qualifications: list = Field(default_factory=list)
    references: list = Field(default_factory=list)
    work_experience: list = Field(default_factory=list)
    profile_photo: str = ""
    cover_image: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    bio: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    avatar: Optional[str] = None
    open_to_work: Optional[bool] = None
    weekday_rate: Optional[str] = None
    weekend_rate: Optional[str] = None
    holiday_rate: Optional[str] = None
    business_name: Optional[str] = None
    abn: Optional[str] = None
    business_email: Optional[str] = None
    business_address: Optional[str] = None
    business_city: Optional[str] = None
    business_state: Optional[str] = None
    business_postcode: Optional[str] = None
    payment_account_name: Optional[str] = None
    payment_bsb: Optional[str] = None
    payment_account_number: Optional[str] = None
    availability: Optional[dict] = None
    about_me_tags: Optional[list] = None
    qualifications: Optional[list] = None
    references: Optional[list] = None
    work_experience: Optional[list] = None
    profile_photo: Optional[str] = None
    cover_image: Optional[str] = None

class Advert(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    location: str = ""
    title: str
    description: str = ""
    hourly_rate: str = ""
    profile_visible: bool = False
    is_draft: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AdvertCreate(BaseModel):
    location: str = ""
    title: str
    description: str = ""
    hourly_rate: str = ""
    profile_visible: bool = False
    is_draft: bool = True

class Shift(BaseModel):
    date: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    break_start: Optional[str] = None
    break_end: Optional[str] = None
    client_name: Optional[str] = None
    phase: Optional[str] = None
    invoice_id: Optional[str] = None

class Receipt(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    amount: float = 0.0
    gst: float = 0.0
    cost_code: str = ""
    client_id: str = ""
    client_name: str = ""
    description: str = ""
    attachment: str = ""  # Base64 encoded file
    attachment_name: str = ""
    status: str = "submitted"  # submitted, approved, rejected
    invoice_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ReceiptCreate(BaseModel):
    title: str
    amount: float = 0.0
    gst: float = 0.0
    cost_code: str = ""
    client_id: str = ""
    client_name: str = ""
    description: str = ""
    attachment: str = ""
    attachment_name: str = ""

class ReceiptUpdate(BaseModel):
    title: Optional[str] = None
    amount: Optional[float] = None
    gst: Optional[float] = None
    cost_code: Optional[str] = None
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    description: Optional[str] = None
    attachment: Optional[str] = None
    attachment_name: Optional[str] = None
    status: Optional[str] = None

class InvoiceLineItem(BaseModel):
    support_item_number: str = ""
    support_item_name: str = ""
    claim_type: str = "standard"  # standard, non_face_to_face, provider_travel, short_notice_cancellation, ndis_requested_report
    date_of_service: str = ""
    unit_price: float = 0.0
    quantity: float = 1.0
    total: float = 0.0
    source_type: str = ""  # shift, receipt, travel, manual
    source_id: str = ""  # ID/date of the source record

class Invoice(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    invoice_number: str = ""
    # Provider info
    provider_business_name: str = ""
    provider_abn: str = ""
    # Participant info
    participant_name: str = ""
    participant_ndis_number: str = ""
    participant_address: str = ""
    # Line items
    line_items: list = Field(default_factory=list)
    # Totals
    subtotal: float = 0.0
    gst: float = 0.0
    total_amount: float = 0.0
    gst_applicable: bool = False
    # For plan managers
    third_party_provider_abn: str = ""
    # Legacy compat
    title: str = ""
    amount: float = 0.0
    client_id: str = ""
    client_name: str = ""
    description: str = ""
    due_date: str = ""
    notes: str = ""
    status: str = "draft"  # draft, sent, paid, overdue
    created_at: datetime = Field(default_factory=datetime.utcnow)

class InvoiceCreate(BaseModel):
    invoice_number: str = ""
    provider_business_name: str = ""
    provider_abn: str = ""
    participant_name: str = ""
    participant_ndis_number: str = ""
    participant_address: str = ""
    line_items: list = Field(default_factory=list)
    subtotal: float = 0.0
    gst: float = 0.0
    total_amount: float = 0.0
    gst_applicable: bool = False
    third_party_provider_abn: str = ""
    title: str = ""
    amount: float = 0.0
    client_id: str = ""
    client_name: str = ""
    description: str = ""
    due_date: str = ""
    notes: str = ""

class InvoiceUpdate(BaseModel):
    invoice_number: Optional[str] = None
    provider_business_name: Optional[str] = None
    provider_abn: Optional[str] = None
    participant_name: Optional[str] = None
    participant_ndis_number: Optional[str] = None
    participant_address: Optional[str] = None
    line_items: Optional[list] = None
    subtotal: Optional[float] = None
    gst: Optional[float] = None
    total_amount: Optional[float] = None
    gst_applicable: Optional[bool] = None
    third_party_provider_abn: Optional[str] = None
    title: Optional[str] = None
    amount: Optional[float] = None
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None

class Report(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    participant_name: str
    date: str = ""
    time_start: str = ""
    time_end: str = ""
    support_worker: str = ""
    observations: str = ""
    supports_goals: str = ""
    health_medication: str = ""
    bowel_movement: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ReportCreate(BaseModel):
    participant_name: str
    date: str = ""
    time_start: str = ""
    time_end: str = ""
    support_worker: str = ""
    observations: str = ""
    supports_goals: str = ""
    health_medication: str = ""
    bowel_movement: str = ""

class WHSIncident(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str = ""
    date: str = ""
    time: str = ""
    hospital_required: bool = False
    attachment: str = ""
    attachment_name: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)

class WHSIncidentCreate(BaseModel):
    title: str
    description: str = ""
    date: str = ""
    time: str = ""
    hospital_required: bool = False
    attachment: str = ""
    attachment_name: str = ""

class TravelRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    date: str
    travel_from: str
    travel_to: str
    start_km: float
    end_km: float
    total_km: float = 0
    client_name: Optional[str] = None
    client_id: Optional[str] = None
    invoice_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class TravelRecordCreate(BaseModel):
    date: str
    travel_from: str
    travel_to: str
    start_km: float
    end_km: float
    client_name: Optional[str] = None
    client_id: Optional[str] = None


# Health check
@api_router.get("/")
async def root():
    return {"message": "Task Manager API", "status": "running"}


# ====== EMAIL HELPER ======

def generate_verification_code() -> str:
    return ''.join(random.choices(string.digits, k=6))

def send_verification_email(to_email: str, code: str, name: str = "") -> bool:
    try:
        if not SMTP_EMAIL or not SMTP_PASSWORD:
            logging.warning("SMTP not configured, cannot send verification email")
            return False
        
        msg = MIMEMultipart('alternative')
        msg['From'] = f"Ayder <{SMTP_EMAIL}>"
        msg['To'] = to_email
        msg['Subject'] = f"Your Ayder Verification Code: {code}"
        
        html_body = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 480px; margin: 0 auto; padding: 40px 24px; background-color: #F0F4F8;">
            <div style="text-align: center; margin-bottom: 32px;">
                <h1 style="color: #00B8A9; font-size: 28px; margin: 0;">Ayder</h1>
                <p style="color: #666; font-size: 14px; margin-top: 4px;">Task & Client Management</p>
            </div>
            <div style="background: white; border-radius: 20px; padding: 32px; box-shadow: 0 2px 12px rgba(0,0,0,0.08);">
                <h2 style="color: #1A3C40; font-size: 20px; font-weight: 800; margin-top: 0;">Verify Your Email</h2>
                <p style="color: #666; font-size: 14px; line-height: 1.5;">
                    Hi{' ' + name if name else ''},<br><br>
                    Welcome to Ayder! Please use the verification code below to complete your registration:
                </p>
                <div style="text-align: center; margin: 28px 0;">
                    <div style="display: inline-block; background: #E8F8F7; border: 2px solid #00B8A9; border-radius: 16px; padding: 16px 40px;">
                        <span style="font-size: 36px; font-weight: 900; letter-spacing: 8px; color: #00B8A9;">{code}</span>
                    </div>
                </div>
                <p style="color: #999; font-size: 12px; text-align: center;">
                    This code expires in 10 minutes.<br>
                    If you didn't create an account, you can safely ignore this email.
                </p>
            </div>
            <p style="color: #999; font-size: 11px; text-align: center; margin-top: 24px;">
                &copy; 2025 Ayder. All rights reserved.
            </p>
        </div>
        """
        
        msg.attach(MIMEText(html_body, 'html'))
        
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        logging.info(f"Verification email sent to {to_email}")
        return True
    except Exception as e:
        logging.error(f"Failed to send verification email: {e}")
        return False


# ====== AUTH ENDPOINTS ======

@api_router.post("/auth/register")
async def register(req: RegisterRequest):
    existing = await db.users.find_one({"email": req.email.lower().strip()})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    password_hash = bcrypt.hashpw(req.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user = User(
        email=req.email.lower().strip(),
        password_hash=password_hash,
        name=req.name.strip(),
        role="user",
        verified=False,
    )
    await db.users.insert_one(user.dict())
    
    # Generate and store verification code
    code = generate_verification_code()
    await db.verification_codes.delete_many({"email": user.email})
    await db.verification_codes.insert_one({
        "email": user.email,
        "code": code,
        "created_at": datetime.utcnow(),
        "attempts": 0,
    })
    
    # Send verification email
    email_sent = send_verification_email(user.email, code, user.name)
    
    token = jwt.encode({"user_id": user.id, "email": user.email, "role": user.role}, JWT_SECRET, algorithm="HS256")
    return {
        "token": token,
        "user": {"id": user.id, "email": user.email, "name": user.name, "role": user.role, "verified": False, "accepted_terms": False},
        "email_sent": email_sent,
        "requires_verification": True,
    }


@api_router.post("/auth/verify")
async def verify_email(req: VerifyRequest):
    email = req.email.lower().strip()
    record = await db.verification_codes.find_one({"email": email})
    if not record:
        raise HTTPException(status_code=400, detail="No verification code found. Please request a new one.")
    
    # Check expiry (10 minutes)
    elapsed = (datetime.utcnow() - record['created_at']).total_seconds()
    if elapsed > 600:
        await db.verification_codes.delete_one({"email": email})
        raise HTTPException(status_code=400, detail="Verification code expired. Please request a new one.")
    
    # Check max attempts
    if record.get('attempts', 0) >= 5:
        await db.verification_codes.delete_one({"email": email})
        raise HTTPException(status_code=400, detail="Too many attempts. Please request a new code.")
    
    if record['code'] != req.code.strip():
        await db.verification_codes.update_one({"email": email}, {"$inc": {"attempts": 1}})
        raise HTTPException(status_code=400, detail="Invalid verification code")
    
    # Mark user as verified
    await db.users.update_one({"email": email}, {"$set": {"verified": True}})
    await db.verification_codes.delete_one({"email": email})
    
    user = await db.users.find_one({"email": email})
    token = jwt.encode({"user_id": user['id'], "email": user['email'], "role": user.get('role', 'user')}, JWT_SECRET, algorithm="HS256")
    return {
        "token": token,
        "user": {"id": user['id'], "email": user['email'], "name": user.get('name', ''), "role": user.get('role', 'user'), "verified": True, "accepted_terms": user.get('accepted_terms', False)},
        "message": "Email verified successfully",
    }


@api_router.post("/auth/resend-code")
async def resend_verification_code(req: ResendCodeRequest):
    email = req.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.get('verified', False):
        raise HTTPException(status_code=400, detail="Email already verified")
    
    # Rate limit: check if last code was sent less than 60 seconds ago
    existing = await db.verification_codes.find_one({"email": email})
    if existing:
        elapsed = (datetime.utcnow() - existing['created_at']).total_seconds()
        if elapsed < 60:
            raise HTTPException(status_code=429, detail=f"Please wait {int(60 - elapsed)} seconds before requesting a new code")
    
    # Generate new code
    code = generate_verification_code()
    await db.verification_codes.delete_many({"email": email})
    await db.verification_codes.insert_one({
        "email": email,
        "code": code,
        "created_at": datetime.utcnow(),
        "attempts": 0,
    })
    
    email_sent = send_verification_email(email, code, user.get('name', ''))
    return {"email_sent": email_sent, "message": "Verification code sent"}


@api_router.post("/auth/login")
async def login(req: LoginRequest):
    user = await db.users.find_one({"email": req.email.lower().strip()})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not bcrypt.checkpw(req.password.encode('utf-8'), user['password_hash'].encode('utf-8')):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    is_verified = user.get('verified', True)  # Default True for existing/admin users
    has_accepted_terms = user.get('accepted_terms', True)  # Default True for existing/admin users
    token = jwt.encode({"user_id": user['id'], "email": user['email'], "role": user.get('role', 'user')}, JWT_SECRET, algorithm="HS256")
    return {
        "token": token,
        "user": {"id": user['id'], "email": user['email'], "name": user.get('name', ''), "role": user.get('role', 'user'), "verified": is_verified, "accepted_terms": has_accepted_terms},
        "requires_verification": not is_verified,
    }


@api_router.post("/auth/accept-terms")
async def accept_terms(req: AcceptTermsRequest):
    email = req.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await db.users.update_one({"email": email}, {"$set": {"accepted_terms": True, "accepted_terms_at": datetime.utcnow()}})
    
    user = await db.users.find_one({"email": email})
    token = jwt.encode({"user_id": user['id'], "email": user['email'], "role": user.get('role', 'user')}, JWT_SECRET, algorithm="HS256")
    return {
        "token": token,
        "user": {"id": user['id'], "email": user['email'], "name": user.get('name', ''), "role": user.get('role', 'user'), "verified": user.get('verified', True), "accepted_terms": True},
        "message": "Terms accepted successfully",
    }


# Task Endpoints
@api_router.post("/tasks", response_model=Task)
async def create_task(task_input: TaskCreate, x_user_id: str = Header(default="")):
    max_order_task = await db.tasks.find_one({"user_id": x_user_id}, sort=[("order", -1)])
    next_order = (max_order_task["order"] + 1) if max_order_task else 0
    task_dict = task_input.dict()
    task_obj = Task(**task_dict, order=next_order, user_id=x_user_id)
    await db.tasks.insert_one(task_obj.dict())
    return task_obj

@api_router.get("/tasks", response_model=List[Task])
async def get_tasks(date: Optional[str] = None, x_user_id: str = Header(default="")):
    query: dict = {"user_id": x_user_id} if x_user_id else {}
    if date:
        query["date"] = date
    tasks = await db.tasks.find(query).sort("order", 1).to_list(1000)
    return [Task(**task) for task in tasks]

@api_router.get("/task-dates")
async def get_task_dates(x_user_id: str = Header(default="")):
    query = {"user_id": x_user_id} if x_user_id else {}
    pipeline = [{"$match": query}, {"$group": {"_id": "$date"}}]
    dates = []
    async for doc in db.tasks.aggregate(pipeline):
        if doc["_id"]:
            dates.append(doc["_id"])
    return dates

@api_router.get("/tasks/{task_id}", response_model=Task)
async def get_task(task_id: str):
    task = await db.tasks.find_one({"id": task_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return Task(**task)

@api_router.put("/tasks/{task_id}", response_model=Task)
async def update_task(task_id: str, task_update: TaskUpdate):
    task = await db.tasks.find_one({"id": task_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    update_data = {k: v for k, v in task_update.dict().items() if v is not None}
    if update_data:
        await db.tasks.update_one({"id": task_id}, {"$set": update_data})
    
    updated_task = await db.tasks.find_one({"id": task_id})
    return Task(**updated_task)

@api_router.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    result = await db.tasks.delete_one({"id": task_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task deleted successfully"}

@api_router.post("/tasks/reorder")
async def reorder_tasks(reorder: TaskReorder):
    for index, task_id in enumerate(reorder.task_ids):
        await db.tasks.update_one({"id": task_id}, {"$set": {"order": index}})
    return {"message": "Tasks reordered successfully"}

@api_router.post("/tasks/{task_id}/toggle-complete", response_model=Task)
async def toggle_task_complete(task_id: str, body: Optional[TaskCompleteRequest] = None):
    task = await db.tasks.find_one({"id": task_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    new_completed = not task.get("completed", False)
    update_data = {"completed": new_completed}
    
    if new_completed:
        update_data["completed_at"] = datetime.utcnow().isoformat()
        if body:
            update_data["completed_notes"] = body.notes
            update_data["completed_photo"] = body.photo
    else:
        update_data["completed_at"] = None
        update_data["completed_notes"] = ""
        update_data["completed_photo"] = ""
    
    await db.tasks.update_one({"id": task_id}, {"$set": update_data})
    
    updated_task = await db.tasks.find_one({"id": task_id})
    return Task(**updated_task)

# Client Endpoints
@api_router.post("/clients", response_model=Client)
async def create_client(client_input: ClientCreate, x_user_id: str = Header(default="")):
    client_dict = client_input.dict()
    client_obj = Client(**client_dict, user_id=x_user_id)
    await db.clients.insert_one(client_obj.dict())
    return client_obj

@api_router.get("/clients", response_model=List[Client])
async def get_clients(x_user_id: str = Header(default="")):
    query = {"user_id": x_user_id} if x_user_id else {}
    clients = await db.clients.find(query).sort("created_at", -1).to_list(1000)
    return [Client(**client) for client in clients]

@api_router.get("/clients/{client_id}", response_model=Client)
async def get_client(client_id: str):
    client = await db.clients.find_one({"id": client_id})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return Client(**client)

@api_router.put("/clients/{client_id}", response_model=Client)
async def update_client(client_id: str, client_update: ClientUpdate):
    client = await db.clients.find_one({"id": client_id})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    update_data = {k: v for k, v in client_update.dict().items() if v is not None}
    if update_data:
        await db.clients.update_one({"id": client_id}, {"$set": update_data})
    
    updated_client = await db.clients.find_one({"id": client_id})
    return Client(**updated_client)

@api_router.delete("/clients/{client_id}")
async def delete_client(client_id: str):
    result = await db.clients.delete_one({"id": client_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"message": "Client deleted successfully"}

# User Profile Endpoint
@api_router.get("/profile", response_model=UserProfile)
async def get_profile(x_user_id: str = Header(default="")):
    query = {"user_id": x_user_id} if x_user_id else {}
    profile = await db.profile.find_one(query)
    if not profile:
        # Fetch user's real name and email from auth
        default_profile = UserProfile()
        default_profile_dict = default_profile.dict()
        default_profile_dict["user_id"] = x_user_id
        if x_user_id:
            user = await db.users.find_one({"id": x_user_id})
            if user:
                default_profile_dict["name"] = user.get("name", "")
                default_profile_dict["email"] = user.get("email", "")
        await db.profile.insert_one(default_profile_dict)
        return UserProfile(**default_profile_dict)
    return UserProfile(**profile)

@api_router.put("/profile", response_model=UserProfile)
async def update_profile(profile_update: ProfileUpdate, x_user_id: str = Header(default="")):
    query = {"user_id": x_user_id} if x_user_id else {}
    profile = await db.profile.find_one(query)
    if not profile:
        default_profile = UserProfile()
        default_profile_dict = default_profile.dict()
        default_profile_dict["user_id"] = x_user_id
        await db.profile.insert_one(default_profile_dict)
        profile = default_profile_dict

    update_data = {k: v for k, v in profile_update.dict().items() if v is not None}
    if update_data:
        await db.profile.update_one(query, {"$set": update_data})

    updated_profile = await db.profile.find_one(query)
    return UserProfile(**updated_profile)

# Advert Endpoints
@api_router.post("/adverts", response_model=Advert)
async def create_advert(advert_input: AdvertCreate):
    advert_obj = Advert(**advert_input.dict())
    await db.adverts.insert_one(advert_obj.dict())
    return advert_obj

@api_router.get("/adverts", response_model=List[Advert])
async def get_adverts():
    adverts = await db.adverts.find().sort("created_at", -1).to_list(1000)
    return [Advert(**a) for a in adverts]

@api_router.delete("/adverts/{advert_id}")
async def delete_advert(advert_id: str):
    result = await db.adverts.delete_one({"id": advert_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Advert not found")
    return {"message": "Advert deleted"}

@api_router.put("/adverts/{advert_id}", response_model=Advert)
async def update_advert(advert_id: str, advert_input: AdvertCreate):
    existing = await db.adverts.find_one({"id": advert_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Advert not found")
    update_data = advert_input.dict()
    await db.adverts.update_one({"id": advert_id}, {"$set": update_data})
    updated = await db.adverts.find_one({"id": advert_id})
    return Advert(**updated)

# Shift Endpoints
@api_router.get("/shifts")
async def get_all_shifts(x_user_id: str = Header(default="")):
    query = {"user_id": x_user_id} if x_user_id else {}
    shifts = await db.shifts.find(query).sort("date", -1).to_list(200)
    results = []
    for s in shifts:
        if s.get("start_time") or s.get("end_time"):
            results.append(Shift(**s))
    return results

@api_router.get("/shifts/{date}", response_model=Shift)
async def get_shift(date: str, x_user_id: str = Header(default="")):
    query = {"date": date}
    if x_user_id:
        query["user_id"] = x_user_id
    shift = await db.shifts.find_one(query)
    if not shift:
        return Shift(date=date, user_id=x_user_id)
    return Shift(**shift)

@api_router.put("/shifts/{date}", response_model=Shift)
async def save_shift(date: str, shift: Shift, x_user_id: str = Header(default="")):
    shift_dict = shift.dict()
    shift_dict["user_id"] = x_user_id
    query = {"date": date}
    if x_user_id:
        query["user_id"] = x_user_id
    existing = await db.shifts.find_one(query)
    if existing:
        await db.shifts.update_one(query, {"$set": shift_dict})
    else:
        await db.shifts.insert_one(shift_dict)
    saved = await db.shifts.find_one(query)
    return Shift(**saved)

@api_router.delete("/shifts/{date}")
async def delete_shift(date: str, x_user_id: str = Header(default="")):
    query = {"date": date}
    if x_user_id:
        query["user_id"] = x_user_id
    result = await db.shifts.delete_one(query)
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Shift not found")
    return {"message": "Shift deleted"}

# Receipt Endpoints
@api_router.post("/receipts", response_model=Receipt)
async def create_receipt(receipt_input: ReceiptCreate, x_user_id: str = Header(default="")):
    receipt_dict = receipt_input.dict()
    receipt_obj = Receipt(**receipt_dict, user_id=x_user_id)
    await db.receipts.insert_one(receipt_obj.dict())
    return receipt_obj

@api_router.get("/receipts", response_model=List[Receipt])
async def get_receipts(x_user_id: str = Header(default="")):
    query = {"user_id": x_user_id} if x_user_id else {}
    receipts = await db.receipts.find(query).sort("created_at", -1).to_list(1000)
    return [Receipt(**r) for r in receipts]

@api_router.get("/receipts/{receipt_id}", response_model=Receipt)
async def get_receipt(receipt_id: str):
    receipt = await db.receipts.find_one({"id": receipt_id})
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return Receipt(**receipt)

@api_router.put("/receipts/{receipt_id}", response_model=Receipt)
async def update_receipt(receipt_id: str, receipt_update: ReceiptUpdate):
    receipt = await db.receipts.find_one({"id": receipt_id})
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    update_data = {k: v for k, v in receipt_update.dict().items() if v is not None}
    if update_data:
        await db.receipts.update_one({"id": receipt_id}, {"$set": update_data})
    updated = await db.receipts.find_one({"id": receipt_id})
    return Receipt(**updated)

@api_router.delete("/receipts/{receipt_id}")
async def delete_receipt(receipt_id: str):
    result = await db.receipts.delete_one({"id": receipt_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return {"message": "Receipt deleted successfully"}

# Invoice Endpoints
@api_router.post("/invoices", response_model=Invoice)
async def create_invoice(invoice_input: InvoiceCreate, x_user_id: str = Header(default="")):
    invoice_dict = invoice_input.dict()
    invoice_obj = Invoice(**invoice_dict)
    invoice_data = invoice_obj.dict()
    invoice_data["user_id"] = x_user_id
    if not invoice_obj.invoice_number:
        count = await db.invoices.count_documents({"user_id": x_user_id})
        invoice_data["invoice_number"] = f"INV-{count + 1:04d}"
    await db.invoices.insert_one(invoice_data)

    # Mark source records as invoiced
    for item in invoice_obj.line_items:
        source_type = item.get("source_type", "") if isinstance(item, dict) else ""
        source_id = item.get("source_id", "") if isinstance(item, dict) else ""
        if source_type and source_id:
            if source_type == "shift":
                await db.shifts.update_one({"date": source_id}, {"$set": {"invoice_id": invoice_obj.id}})
            elif source_type == "receipt":
                await db.receipts.update_one({"id": source_id}, {"$set": {"invoice_id": invoice_obj.id}})
            elif source_type == "travel":
                await db.travel_records.update_one({"id": source_id}, {"$set": {"invoice_id": invoice_obj.id}})

    return Invoice(**invoice_data)


@api_router.get("/uninvoiced-items/{client_name}")
async def get_uninvoiced_items(client_name: str, x_user_id: str = Header(default="")):
    from urllib.parse import unquote
    decoded_name = unquote(client_name)
    user_filter = {"user_id": x_user_id} if x_user_id else {}

    shifts_cursor = db.shifts.find({
        "client_name": decoded_name,
        "$or": [{"invoice_id": None}, {"invoice_id": {"$exists": False}}, {"invoice_id": ""}],
        **user_filter
    })
    shifts = []
    async for s in shifts_cursor:
        s.pop("_id", None)
        shifts.append(s)

    receipts_cursor = db.receipts.find({
        "client_name": decoded_name,
        "$or": [{"invoice_id": None}, {"invoice_id": {"$exists": False}}, {"invoice_id": ""}],
        **user_filter
    })
    receipts = []
    async for r in receipts_cursor:
        r.pop("_id", None)
        receipts.append(r)

    travel_cursor = db.travel_records.find({
        "client_name": decoded_name,
        "$or": [{"invoice_id": None}, {"invoice_id": {"$exists": False}}, {"invoice_id": ""}],
        **user_filter
    })
    travel_records = []
    async for t in travel_cursor:
        t.pop("_id", None)
        travel_records.append(t)

    return {"shifts": shifts, "receipts": receipts, "travel_records": travel_records}

@api_router.get("/invoices", response_model=List[Invoice])
async def get_invoices(x_user_id: str = Header(default="")):
    query = {"user_id": x_user_id} if x_user_id else {}
    invoices = await db.invoices.find(query).sort("created_at", -1).to_list(1000)
    return [Invoice(**i) for i in invoices]

@api_router.get("/invoices/{invoice_id}", response_model=Invoice)
async def get_invoice(invoice_id: str):
    invoice = await db.invoices.find_one({"id": invoice_id})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return Invoice(**invoice)

@api_router.put("/invoices/{invoice_id}", response_model=Invoice)
async def update_invoice(invoice_id: str, invoice_update: InvoiceUpdate):
    invoice = await db.invoices.find_one({"id": invoice_id})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    update_data = {k: v for k, v in invoice_update.dict().items() if v is not None}
    if update_data:
        await db.invoices.update_one({"id": invoice_id}, {"$set": update_data})
    updated = await db.invoices.find_one({"id": invoice_id})
    return Invoice(**updated)

@api_router.delete("/invoices/{invoice_id}")
async def delete_invoice(invoice_id: str):
    result = await db.invoices.delete_one({"id": invoice_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return {"message": "Invoice deleted successfully"}

# Report Endpoints
@api_router.post("/reports", response_model=Report)
async def create_report(report_input: ReportCreate):
    report_dict = report_input.dict()
    report_obj = Report(**report_dict)
    await db.reports.insert_one(report_obj.dict())
    return report_obj

@api_router.get("/reports", response_model=List[Report])
async def get_reports():
    reports = await db.reports.find().sort("created_at", -1).to_list(1000)
    return [Report(**r) for r in reports]

@api_router.put("/reports/{report_id}", response_model=Report)
async def update_report(report_id: str, report_input: ReportCreate):
    existing = await db.reports.find_one({"id": report_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Report not found")
    update_data = report_input.dict()
    await db.reports.update_one({"id": report_id}, {"$set": update_data})
    updated = await db.reports.find_one({"id": report_id})
    return Report(**updated)

@api_router.delete("/reports/{report_id}")
async def delete_report(report_id: str):
    result = await db.reports.delete_one({"id": report_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"message": "Report deleted successfully"}

# WHS Incident Endpoints
@api_router.post("/whs-incidents", response_model=WHSIncident)
async def create_whs_incident(incident_input: WHSIncidentCreate):
    incident_dict = incident_input.dict()
    incident_obj = WHSIncident(**incident_dict)
    await db.whs_incidents.insert_one(incident_obj.dict())
    return incident_obj

@api_router.get("/whs-incidents", response_model=List[WHSIncident])
async def get_whs_incidents():
    incidents = await db.whs_incidents.find().sort("created_at", -1).to_list(1000)
    return [WHSIncident(**i) for i in incidents]

@api_router.delete("/whs-incidents/{incident_id}")
async def delete_whs_incident(incident_id: str):
    result = await db.whs_incidents.delete_one({"id": incident_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="WHS Incident not found")
    return {"message": "WHS Incident deleted successfully"}

# Travel Record Endpoints
@api_router.post("/travel-records", response_model=TravelRecord)
async def create_travel_record(record_input: TravelRecordCreate, x_user_id: str = Header(default="")):
    record_dict = record_input.dict()
    total_km = max(0, record_dict["end_km"] - record_dict["start_km"])
    record_obj = TravelRecord(**record_dict, total_km=total_km)
    record_data = record_obj.dict()
    record_data["user_id"] = x_user_id
    await db.travel_records.insert_one(record_data)
    return TravelRecord(**record_data)

@api_router.get("/travel-records", response_model=List[TravelRecord])
async def get_travel_records(x_user_id: str = Header(default="")):
    query = {"user_id": x_user_id} if x_user_id else {}
    records = await db.travel_records.find(query).sort("created_at", -1).to_list(100)
    return [TravelRecord(**r) for r in records]

@api_router.delete("/travel-records/{record_id}")
async def delete_travel_record(record_id: str):
    result = await db.travel_records.delete_one({"id": record_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Travel record not found")
    return {"message": "Travel record deleted successfully"}

@api_router.get("/travel-records/{record_id}", response_model=TravelRecord)
async def get_travel_record(record_id: str):
    record = await db.travel_records.find_one({"id": record_id})
    if not record:
        raise HTTPException(status_code=404, detail="Travel record not found")
    return TravelRecord(**record)

@api_router.put("/travel-records/{record_id}", response_model=TravelRecord)
async def update_travel_record(record_id: str, record_input: TravelRecordCreate):
    existing = await db.travel_records.find_one({"id": record_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Travel record not found")
    update_data = record_input.dict()
    update_data["total_km"] = max(0, update_data["end_km"] - update_data["start_km"])
    await db.travel_records.update_one({"id": record_id}, {"$set": update_data})
    updated = await db.travel_records.find_one({"id": record_id})
    return TravelRecord(**updated)

# PDF Generation helper
def generate_invoice_pdf(invoice_data: dict, profile_data: dict) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm, topMargin=15*mm, bottomMargin=15*mm)
    story = []
    styles = getSampleStyleSheet()

    teal = HexColor('#00B8A9')
    dark = HexColor('#1A3C40')
    grey = HexColor('#666666')
    light_grey = HexColor('#F0F0F0')
    white = HexColor('#FFFFFF')

    # Custom styles
    title_style = ParagraphStyle('InvoiceTitle', parent=styles['Heading1'], fontSize=28, textColor=dark, spaceAfter=2*mm, fontName='Helvetica-Bold')
    header_style = ParagraphStyle('Header', parent=styles['Normal'], fontSize=10, textColor=dark, fontName='Helvetica-Bold')
    normal_style = ParagraphStyle('NormalText', parent=styles['Normal'], fontSize=9, textColor=grey, leading=13)
    small_style = ParagraphStyle('Small', parent=styles['Normal'], fontSize=8, textColor=grey, leading=11)
    label_style = ParagraphStyle('Label', parent=styles['Normal'], fontSize=8, textColor=grey, fontName='Helvetica-Bold', leading=11)
    value_style = ParagraphStyle('Value', parent=styles['Normal'], fontSize=10, textColor=dark, fontName='Helvetica-Bold', leading=14)
    right_style = ParagraphStyle('Right', parent=styles['Normal'], fontSize=9, textColor=grey, alignment=TA_RIGHT)
    right_bold = ParagraphStyle('RightBold', parent=styles['Normal'], fontSize=10, textColor=dark, fontName='Helvetica-Bold', alignment=TA_RIGHT)

    biz_name = profile_data.get('business_name') or profile_data.get('name', '')
    biz_abn = profile_data.get('abn', '')
    biz_email = profile_data.get('business_email') or profile_data.get('email', '')
    biz_address = profile_data.get('business_address', '')
    biz_city = profile_data.get('business_city', '')
    biz_state = profile_data.get('business_state', '')
    biz_postcode = profile_data.get('business_postcode', '')
    full_biz_addr = f"{biz_address}, {biz_city} {biz_state} {biz_postcode}".strip(', ')

    # Header: Business info
    header_data = [
        [Paragraph(f"<b>{biz_name}</b>", ParagraphStyle('BizName', parent=styles['Normal'], fontSize=14, textColor=dark, fontName='Helvetica-Bold')),
         Paragraph('INVOICE', title_style)],
        [Paragraph(f"ABN: {biz_abn}", small_style), ''],
        [Paragraph(biz_email, small_style), ''],
        [Paragraph(full_biz_addr, small_style), ''],
    ]
    header_table = Table(header_data, colWidths=[90*mm, 80*mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 6*mm))

    # Teal divider
    divider_data = [['', '']]
    divider_table = Table(divider_data, colWidths=[170*mm, 0])
    divider_table.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (0, 0), 2, teal),
    ]))
    story.append(divider_table)
    story.append(Spacer(1, 6*mm))

    # Invoice To and Invoice Details
    inv_num = invoice_data.get('invoice_number', '')
    inv_date = invoice_data.get('created_at', datetime.utcnow().strftime('%Y-%m-%d'))
    if isinstance(inv_date, str) and 'T' in inv_date:
        inv_date = inv_date.split('T')[0]
    due_date = invoice_data.get('due_date', '')
    participant = invoice_data.get('participant_name', '')
    ndis_num = invoice_data.get('participant_ndis_number', '')
    p_address = invoice_data.get('participant_address', '')

    details_left = [
        [Paragraph('<b>Invoice To</b>', label_style)],
        [Paragraph(f"<b>{participant}</b>", value_style)],
        [Paragraph(f"NDIS Number: {ndis_num}", small_style)],
    ]
    if p_address:
        details_left.append([Paragraph(p_address, small_style)])

    details_right = [
        [Paragraph('Invoice Number', label_style), Paragraph(inv_num, ParagraphStyle('Val', parent=styles['Normal'], fontSize=9, textColor=dark, alignment=TA_RIGHT))],
        [Paragraph('Date', label_style), Paragraph(str(inv_date), ParagraphStyle('Val', parent=styles['Normal'], fontSize=9, textColor=dark, alignment=TA_RIGHT))],
        [Paragraph('Due Date', label_style), Paragraph(due_date or 'On receipt', ParagraphStyle('Val', parent=styles['Normal'], fontSize=9, textColor=dark, alignment=TA_RIGHT))],
    ]

    left_table = Table(details_left, colWidths=[85*mm])
    right_table = Table(details_right, colWidths=[35*mm, 50*mm])
    right_table.setStyle(TableStyle([
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))

    combined = Table([[left_table, right_table]], colWidths=[90*mm, 85*mm])
    combined.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    story.append(combined)
    story.append(Spacer(1, 8*mm))

    # Line items table
    line_items = invoice_data.get('line_items', [])
    gst_applicable = invoice_data.get('gst_applicable', False)

    th_style = ParagraphStyle('TH', parent=styles['Normal'], fontSize=8, textColor=white, fontName='Helvetica-Bold')
    td_style = ParagraphStyle('TD', parent=styles['Normal'], fontSize=8, textColor=dark, leading=11)
    td_right = ParagraphStyle('TDR', parent=styles['Normal'], fontSize=8, textColor=dark, alignment=TA_RIGHT, leading=11)

    table_data = [
        [Paragraph('Date', th_style), Paragraph('Description', th_style), Paragraph('Qty', th_style),
         Paragraph('Rate', th_style), Paragraph('GST', th_style), Paragraph('Amount', th_style)]
    ]

    subtotal = 0
    for item in line_items:
        price = float(item.get('unit_price', 0))
        qty = float(item.get('quantity', 0))
        line_total = price * qty
        gst_val = line_total * 0.1 if gst_applicable else 0
        subtotal += line_total

        desc_text = item.get('support_item_name', '')
        code = item.get('support_item_number', '')
        if code:
            desc_text = f"{desc_text}<br/><font size=7 color='#6366F1'>{code}</font>"

        table_data.append([
            Paragraph(item.get('date_of_service', ''), td_style),
            Paragraph(desc_text, td_style),
            Paragraph(str(qty), td_right),
            Paragraph(f"${price:.2f}", td_right),
            Paragraph(f"${gst_val:.2f}" if gst_applicable else 'N/A', td_right),
            Paragraph(f"${line_total:.2f}", td_right),
        ])

    items_table = Table(table_data, colWidths=[22*mm, 68*mm, 15*mm, 22*mm, 20*mm, 23*mm])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), dark),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('BACKGROUND', (0, 1), (-1, -1), white),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, light_grey]),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#E0E0E0')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 1), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 6*mm))

    # Totals
    gst_total = subtotal * 0.1 if gst_applicable else 0
    grand_total = subtotal + gst_total

    totals_data = [
        ['', Paragraph('Subtotal', ParagraphStyle('TR', parent=styles['Normal'], fontSize=9, textColor=grey, alignment=TA_RIGHT)),
         Paragraph(f"${subtotal:.2f}", td_right)],
    ]
    if gst_applicable:
        totals_data.append([
            '', Paragraph('GST (10%)', ParagraphStyle('TR', parent=styles['Normal'], fontSize=9, textColor=grey, alignment=TA_RIGHT)),
            Paragraph(f"${gst_total:.2f}", td_right)
        ])
    totals_data.append([
        '', Paragraph('<b>Balance Due</b>', ParagraphStyle('TR', parent=styles['Normal'], fontSize=11, textColor=dark, fontName='Helvetica-Bold', alignment=TA_RIGHT)),
        Paragraph(f"<b>${grand_total:.2f}</b>", ParagraphStyle('TRV', parent=styles['Normal'], fontSize=11, textColor=teal, fontName='Helvetica-Bold', alignment=TA_RIGHT))
    ])

    totals_table = Table(totals_data, colWidths=[100*mm, 40*mm, 30*mm])
    totals_table.setStyle(TableStyle([
        ('LINEABOVE', (1, -1), (-1, -1), 1, dark),
        ('TOPPADDING', (0, -1), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(totals_table)
    story.append(Spacer(1, 10*mm))

    # Payment Details
    acct_name = profile_data.get('payment_account_name', '')
    bsb = profile_data.get('payment_bsb', '')
    acct_num = profile_data.get('payment_account_number', '')

    if acct_name or bsb or acct_num:
        story.append(Paragraph('<b>Payment Details</b>', ParagraphStyle('PayTitle', parent=styles['Normal'], fontSize=10, textColor=dark, fontName='Helvetica-Bold', spaceAfter=3*mm)))
        pay_data = []
        if acct_name:
            pay_data.append([Paragraph('Account Name', label_style), Paragraph(acct_name, normal_style)])
        if bsb:
            pay_data.append([Paragraph('BSB', label_style), Paragraph(bsb, normal_style)])
        if acct_num:
            pay_data.append([Paragraph('Account Number', label_style), Paragraph(acct_num, normal_style)])
        pay_table = Table(pay_data, colWidths=[35*mm, 80*mm])
        pay_table.setStyle(TableStyle([
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(pay_table)
        story.append(Spacer(1, 6*mm))

    # Notes
    notes = invoice_data.get('notes', '')
    if notes:
        story.append(Paragraph('<b>Notes</b>', ParagraphStyle('NotesTitle', parent=styles['Normal'], fontSize=9, textColor=dark, fontName='Helvetica-Bold', spaceAfter=2*mm)))
        story.append(Paragraph(notes, normal_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# Email sending request model
class SendInvoiceEmailRequest(BaseModel):
    invoice_id: str
    recipient_email: str
    subject: str = ""
    message: str = ""

@api_router.get("/invoices/{invoice_id}/generate-pdf")
async def generate_invoice_pdf_endpoint(invoice_id: str):
    invoice = await db.invoices.find_one({"id": invoice_id})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    profile = await db.profile.find_one()
    profile_data = profile if profile else {}

    pdf_bytes = generate_invoice_pdf(invoice, profile_data)

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=invoice_{invoice.get('invoice_number', invoice_id)}.pdf"}
    )

@api_router.post("/invoices/{invoice_id}/send-email")
async def send_invoice_email(invoice_id: str, req: SendInvoiceEmailRequest):
    invoice = await db.invoices.find_one({"id": invoice_id})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    profile = await db.profile.find_one()
    profile_data = profile if profile else {}

    # Generate PDF
    pdf_bytes = generate_invoice_pdf(invoice, profile_data)
    inv_num = invoice.get('invoice_number', invoice_id)
    participant = invoice.get('participant_name', 'Participant')
    total = invoice.get('total_amount', 0)
    biz_name = profile_data.get('business_name') or profile_data.get('name', 'Provider')

    # Check for SMTP credentials
    smtp_user = os.environ.get('SMTP_EMAIL', '')
    smtp_pass = os.environ.get('SMTP_PASSWORD', '')

    if not smtp_user or not smtp_pass:
        # MOCKED: Save PDF and return success without actually sending
        await db.invoices.update_one({"id": invoice_id}, {"$set": {"status": "sent", "sent_to": req.recipient_email, "sent_at": datetime.utcnow().isoformat()}})
        return {
            "success": True,
            "mocked": True,
            "message": f"Invoice {inv_num} generated successfully. Email sending is mocked (no SMTP credentials configured). Set SMTP_EMAIL and SMTP_PASSWORD in .env to enable real email sending.",
            "recipient": req.recipient_email,
            "pdf_size": len(pdf_bytes)
        }

    # Real email sending with Gmail SMTP
    try:
        subject = req.subject or f"Invoice {inv_num} from {biz_name}"
        body = req.message or f"""Dear {participant},

Please find attached invoice {inv_num} for the amount of ${total:.2f}.

If you have any questions regarding this invoice, please don't hesitate to contact us.

Kind regards,
{biz_name}"""

        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = req.recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        attachment = MIMEBase('application', 'pdf')
        attachment.set_payload(pdf_bytes)
        encoders.encode_base64(attachment)
        attachment.add_header('Content-Disposition', f'attachment; filename="Invoice_{inv_num}.pdf"')
        msg.attach(attachment)

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, req.recipient_email, msg.as_string())

        await db.invoices.update_one({"id": invoice_id}, {"$set": {"status": "sent", "sent_to": req.recipient_email, "sent_at": datetime.utcnow().isoformat()}})

        return {
            "success": True,
            "mocked": False,
            "message": f"Invoice {inv_num} sent successfully to {req.recipient_email}",
            "recipient": req.recipient_email
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")


# Include the router in the main app
app.include_router(api_router)

# Temporary download endpoint for deployment files
@app.get("/api/download-backend")
async def download_backend_zip():
    zip_path = Path(__file__).parent / "ayder-backend-deploy.zip"
    if zip_path.exists():
        return FileResponse(
            path=str(zip_path),
            filename="ayder-backend-deploy.zip",
            media_type="application/zip"
        )
    raise HTTPException(status_code=404, detail="Zip file not found")

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def seed_admin():
    existing = await db.users.find_one({"email": "tristan.evans@ayder.com.au"})
    if not existing:
        password_hash = bcrypt.hashpw("1234".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        admin = User(
            email="tristan.evans@ayder.com.au",
            password_hash=password_hash,
            name="Tristan Evans",
            role="admin",
            verified=True,
            accepted_terms=True,
        )
        await db.users.insert_one(admin.dict())
        print("Admin account seeded: tristan.evans@ayder.com.au")
    else:
        # Ensure existing admin is verified and has accepted terms
        await db.users.update_one({"email": "tristan.evans@ayder.com.au"}, {"$set": {"verified": True, "accepted_terms": True}})
    # Create TTL index for verification codes (auto-expire after 10 min)
    await db.verification_codes.create_index("created_at", expireAfterSeconds=600)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
