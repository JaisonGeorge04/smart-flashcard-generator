import datetime
import logging
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from typing import List, Optional

import database as db_mod
import auth
import nlp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

# Initialize database tables
db_mod.init_db()

app = FastAPI(title="Smart Flashcard Generator API")

# Configure CORS for local development (React client)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for development convenience
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Schemas ---
class UserAuth(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class SetCreate(BaseModel):
    title: str
    notes_content: str

class FlashcardResponse(BaseModel):
    id: int
    set_id: int
    question: str
    answer: str
    status: str
    leitner_box: int
    next_review_at: datetime.datetime
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class FlashcardSetResponse(BaseModel):
    id: int
    user_id: int
    title: str
    notes_content: str
    created_at: datetime.datetime
    card_count: int = 0
    known_count: int = 0

    class Config:
        from_attributes = True

class SetDetailResponse(BaseModel):
    id: int
    title: str
    notes_content: str
    created_at: datetime.datetime
    cards: List[FlashcardResponse]

    class Config:
        from_attributes = True

class ReviewAction(BaseModel):
    status: str  # "known" or "not_known"

# --- Leitner Intervals (Short for testing/demo, scalable for prod) ---
# Box 1: 5 seconds
# Box 2: 30 seconds
# Box 3: 2 minutes
# Box 4: 10 minutes
# Box 5: 1 hour
LEITNER_INTERVALS = {
    1: datetime.timedelta(seconds=5),
    2: datetime.timedelta(seconds=30),
    3: datetime.timedelta(minutes=2),
    4: datetime.timedelta(minutes=10),
    5: datetime.timedelta(hours=1),
}


# --- Endpoints ---

@app.get("/")
def read_root():
    return {"message": "Welcome to Smart Flashcard Generator API!"}

@app.post("/auth/register", status_code=status.HTTP_201_CREATED)
def register(user_data: UserAuth, db: Session = Depends(db_mod.get_db)):
    # Check if user already exists
    existing_user = db.query(db_mod.User).filter(db_mod.User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists"
        )
    
    # Hash password and save user
    hashed = auth.hash_password(user_data.password)
    new_user = db_mod.User(email=user_data.email, hashed_password=hashed)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"message": "User registered successfully"}


@app.post("/auth/login", response_model=Token)
def login(user_data: UserAuth, db: Session = Depends(db_mod.get_db)):
    user = db.query(db_mod.User).filter(db_mod.User.email == user_data.email).first()
    if not user or not auth.verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Generate token
    token = auth.create_access_token(data={"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}


@app.get("/sets", response_model=List[FlashcardSetResponse])
def get_sets(current_user: db_mod.User = Depends(auth.get_current_user), db: Session = Depends(db_mod.get_db)):
    sets = db.query(db_mod.FlashcardSet).filter(db_mod.FlashcardSet.user_id == current_user.id).all()
    
    # Enrich with counts
    enriched_sets = []
    for s in sets:
        card_count = db.query(db_mod.Flashcard).filter(db_mod.Flashcard.set_id == s.id).count()
        known_count = db.query(db_mod.Flashcard).filter(
            db_mod.Flashcard.set_id == s.id, 
            db_mod.Flashcard.status == "known"
        ).count()
        
        set_dict = {
            "id": s.id,
            "user_id": s.user_id,
            "title": s.title,
            "notes_content": s.notes_content,
            "created_at": s.created_at,
            "card_count": card_count,
            "known_count": known_count
        }
        enriched_sets.append(set_dict)
        
    return enriched_sets


@app.post("/sets", response_model=SetDetailResponse, status_code=status.HTTP_201_CREATED)
def create_set(set_data: SetCreate, current_user: db_mod.User = Depends(auth.get_current_user), db: Session = Depends(db_mod.get_db)):
    if not set_data.title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty")
        
    if not set_data.notes_content.strip() or len(set_data.notes_content.strip()) < 15:
        raise HTTPException(status_code=400, detail="Notes content must be at least 15 characters long")
        
    # Generate Q&A flashcards using NLP module
    generated_cards = nlp.generate_flashcards(set_data.notes_content)
    
    if not generated_cards:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not generate flashcards. Please check if the notes contain descriptive sentences or facts."
        )
    
    # Save set
    new_set = db_mod.FlashcardSet(
        user_id=current_user.id,
        title=set_data.title,
        notes_content=set_data.notes_content
    )
    db.add(new_set)
    db.commit()
    db.refresh(new_set)
    
    # Save flashcards
    db_cards = []
    for card in generated_cards:
        db_card = db_mod.Flashcard(
            set_id=new_set.id,
            question=card["question"],
            answer=card["answer"],
            status="new",
            leitner_box=1,
            next_review_at=datetime.datetime.utcnow()
        )
        db.add(db_card)
        db_cards.append(db_card)
        
    db.commit()
    
    # Refresh to load IDs
    for card in db_cards:
        db.refresh(card)
        
    return {
        "id": new_set.id,
        "title": new_set.title,
        "notes_content": new_set.notes_content,
        "created_at": new_set.created_at,
        "cards": db_cards
    }


@app.get("/sets/{set_id}", response_model=SetDetailResponse)
def get_set_details(set_id: int, current_user: db_mod.User = Depends(auth.get_current_user), db: Session = Depends(db_mod.get_db)):
    flash_set = db.query(db_mod.FlashcardSet).filter(
        db_mod.FlashcardSet.id == set_id, 
        db_mod.FlashcardSet.user_id == current_user.id
    ).first()
    
    if not flash_set:
        raise HTTPException(status_code=404, detail="Flashcard set not found")
        
    return flash_set


@app.get("/sets/{set_id}/review", response_model=List[FlashcardResponse])
def get_cards_for_review(set_id: int, include_all: Optional[bool] = False, current_user: db_mod.User = Depends(auth.get_current_user), db: Session = Depends(db_mod.get_db)):
    # Verify set belongs to user
    flash_set = db.query(db_mod.FlashcardSet).filter(
        db_mod.FlashcardSet.id == set_id, 
        db_mod.FlashcardSet.user_id == current_user.id
    ).first()
    
    if not flash_set:
        raise HTTPException(status_code=404, detail="Flashcard set not found")
        
    now = datetime.datetime.utcnow()
    
    query = db.query(db_mod.Flashcard).filter(db_mod.Flashcard.set_id == set_id)
    
    # If not include_all, only return due cards (next_review_at <= now)
    if not include_all:
        query = query.filter(db_mod.Flashcard.next_review_at <= now)
        
    # Order by next_review_at so the most urgent cards appear first
    cards = query.order_by(db_mod.Flashcard.next_review_at.asc()).all()
    return cards


@app.post("/cards/{card_id}/review", response_model=FlashcardResponse)
def review_card(card_id: int, action: ReviewAction, current_user: db_mod.User = Depends(auth.get_current_user), db: Session = Depends(db_mod.get_db)):
    # Retrieve card and verify it belongs to user
    card = db.query(db_mod.Flashcard).join(db_mod.FlashcardSet).filter(
        db_mod.Flashcard.id == card_id,
        db_mod.FlashcardSet.user_id == current_user.id
    ).first()
    
    if not card:
        raise HTTPException(status_code=404, detail="Flashcard not found")
        
    if action.status not in ("known", "not_known"):
        raise HTTPException(status_code=400, detail="Invalid review status. Must be 'known' or 'not_known'")
        
    now = datetime.datetime.utcnow()
    
    if action.status == "known":
        # Advance card to next box (up to 5)
        new_box = min(card.leitner_box + 1, 5)
        card.leitner_box = new_box
        card.status = "known"
        # Schedule next review based on box
        card.next_review_at = now + LEITNER_INTERVALS[new_box]
    else:
        # Reset card to Box 1
        card.leitner_box = 1
        card.status = "not_known"
        # Schedule next review for Box 1 (5 seconds)
        card.next_review_at = now + LEITNER_INTERVALS[1]
        
    db.commit()
    db.refresh(card)
    return card
