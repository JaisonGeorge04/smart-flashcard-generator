# SmartCards - Smart Flashcard Generator (Option A)

SmartCards is a web-based educational tool that helps students automatically convert their textbooks, study notes, or lecture transcripts into structured question-and-answer and Cloze deletion flashcards. It implements a spaced repetition system using the Leitner method to ensure difficult cards appear more frequently in review sessions.

---

## 🛠️ Tech Stack

- **Frontend**: React (Vite + TypeScript)
- **Styling**: Modern, premium custom Vanilla CSS featuring a dark glassmorphic design and interactive 3D card-flip animations.
- **Backend**: FastAPI (Python 3.13)
- **Database**: SQLite (SQLAlchemy ORM)
- **Natural Language Processing (NLP)**: `spaCy` (specifically `en_core_web_sm` model) with syntax dependency parsing and Named Entity Recognition (NER), with a pure-Python `NLTK` fallback mechanism.
- **Security & Authentication**: Secure user login and registration using custom PBKDF2 password hashing (built-in SHA-256) and JWT-based authentication tokens.

---

## 🧠 How the AI/ML (NLP) Flashcard Generator Works

Rather than simply splitting sentences or utilizing pre-defined static patterns, SmartCards uses a robust, rule-based semantic NLP pipeline to analyze the syntactic structure of the input notes:

1. **Sentence Tokenization & Filtering**: The note input is first segmented into distinct sentences using `spaCy` (or sentence boundaries in NLTK). Short or irrelevant text lines are pruned.
2. **Frequency-based Sentence Ranking**: We rank sentences using an information-density score based on word frequencies. Sentences rich in content words receive higher priority for flashcard candidates, preventing clutter.
3. **Definition Verb Parsing (Dependency Trees)**:
   - We inspect each sentence's dependency structure to find copula linkages (e.g. `[Term] is/are [Definition]`) or definition verbs (e.g. `refers to`, `means`, `represents`, `defines`).
   - We verify the subject (`nsubj` dependency label) is active and is **not** a pronoun (`token.pos_ != "PRON"` or common pronouns like *they, it, he, she*).
   - If a valid definition structure is found, we extract the term and definition to construct a clean Q&A card (e.g. *Question*: `"What is Photosynthesis?"` / *Answer*: `"[Full Sentence definition]"`).
4. **Cloze Deletion (Fill-in-the-blank) Fallback**:
   - For informative sentences that do not fit a direct definition pattern, we run Named Entity Recognition (NER) to look for highly relevant entities (such as locations, organizations, dates, or proper nouns).
   - If no entities are present, we extract noun chunks and score them based on length and technicality.
   - The selected key term is hidden and replaced with `_______` to form a fill-in-the-blank question, with the hidden term serving as the correct answer.

---

## ⚙️ How to Run Locally

### Prerequisites
- Node.js (v24 or later)
- Python (3.11 or later)

### 1. Run Backend API
1. Navigate to the `backend/` directory:
   ```bash
   cd backend
   ```
2. Create and activate a python virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On Unix/macOS:
   source venv/bin/activate
   ```
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the FastAPI server:
   ```bash
   uvicorn main:app --host 127.0.0.1 --port 8080
   ```
   *The backend will be running at `http://127.0.0.1:8080`.*

### 2. Run Frontend Client
1. Navigate to the `frontend/` directory:
   ```bash
   cd frontend
   ```
2. Install npm packages:
   ```bash
   npm install
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```
   *Open `http://localhost:5173` in your browser to view the application.*

---

## 🔄 Spaced Repetition (Leitner System)
We have implemented a **5-Box Leitner Spaced Repetition System**. To make it easy to evaluate and demo without waiting for days, we have mapped the review intervals to shorter periods:
- **Box 1**: 5 seconds
- **Box 2**: 30 seconds
- **Box 3**: 2 minutes
- **Box 4**: 10 minutes
- **Box 5**: 1 hour

### Logic:
- New cards begin in **Box 1** and are due immediately.
- When marked as **Known**, the card moves up one Box (up to Box 5), pushing its next review time further out.
- When marked as **Not Known**, the card resets to **Box 1**, scheduling it to reappear within 5 seconds to help reinforce learning.
