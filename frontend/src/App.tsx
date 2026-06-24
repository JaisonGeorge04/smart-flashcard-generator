import React, { useState, useEffect } from 'react';
import { 
  Plus, 
  BookOpen, 
  BrainCircuit, 
  LogOut, 
  CheckCircle2, 
  XCircle, 
  Layers, 
  ChevronLeft, 
  HelpCircle, 
  RotateCcw,
  Sparkles,
  Lock,
  Mail
} from 'lucide-react';
import type { Flashcard, FlashcardSet } from './types';

const API_URL = 'http://127.0.0.1:8080';

export default function App() {
  // Navigation & Auth State
  const [view, setView] = useState<'auth' | 'dashboard' | 'create' | 'review' | 'completion'>('auth');
  const [authMode, setAuthMode] = useState<'login' | 'signup'>('login');
  const [token, setToken] = useState<string | null>(localStorage.getItem('jwt_token'));
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  // Core Data State
  const [sets, setSets] = useState<FlashcardSet[]>([]);
  const [selectedSet, setSelectedSet] = useState<FlashcardSet | null>(null);
  const [reviewCards, setReviewCards] = useState<Flashcard[]>([]);
  const [currentReviewIndex, setCurrentReviewIndex] = useState(0);
  const [isCardFlipped, setIsCardFlipped] = useState(false);
  const [reviewAll, setReviewAll] = useState(false);

  // Forms State
  const [setTitle, setSetTitle] = useState('');
  const [notesContent, setNotesContent] = useState('');

  // Session Stats State
  const [sessionKnownCount, setSessionKnownCount] = useState(0);
  const [sessionNotKnownCount, setSessionNotKnownCount] = useState(0);

  // Status State
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Auto-route on load if token exists
  useEffect(() => {
    if (token) {
      setView('dashboard');
      loadSets();
    } else {
      setView('auth');
    }
  }, [token]);

  // Clear errors when view changes
  useEffect(() => {
    setError(null);
    setSuccess(null);
  }, [view, authMode]);

  // Helper for API calls
  const apiCall = async (endpoint: string, method: string = 'GET', body: any = null) => {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const options: RequestInit = {
      method,
      headers,
    };
    if (body) {
      options.body = JSON.stringify(body);
    }

    const response = await fetch(`${API_URL}${endpoint}`, options);
    const data = await response.json().catch(() => ({}));
    
    if (!response.ok) {
      throw new Error(data.detail || 'Request failed. Please try again.');
    }
    return data;
  };

  // Auth Operations
  const handleAuthSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password.trim()) {
      setError('Please fill in all fields.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      if (authMode === 'signup') {
        await apiCall('/auth/register', 'POST', { email, password });
        setSuccess('Registration successful! Please log in.');
        setAuthMode('login');
        setPassword('');
      } else {
        const data = await apiCall('/auth/login', 'POST', { email, password });
        localStorage.setItem('jwt_token', data.access_token);
        setToken(data.access_token);
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('jwt_token');
    setToken(null);
    setSets([]);
    setSelectedSet(null);
    setView('auth');
    setEmail('');
    setPassword('');
  };

  // Dashboard Operations
  const loadSets = async () => {
    setLoading(true);
    try {
      const data = await apiCall('/sets');
      setSets(data);
    } catch (err: any) {
      setError('Failed to load flashcard sets.');
    } finally {
      setLoading(false);
    }
  };

  // Flashcard Generation
  const handleCreateSet = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!setTitle.trim()) {
      setError('Please enter a title for the flashcard set.');
      return;
    }
    if (!notesContent.trim() || notesContent.length < 15) {
      setError('Please enter notes text of at least 15 characters.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const newSet = await apiCall('/sets', 'POST', {
        title: setTitle,
        notes_content: notesContent
      });
      setSetTitle('');
      setNotesContent('');
      setSuccess('Flashcards successfully generated!');
      
      // Navigate to review session for the new set directly
      setSelectedSet(newSet);
      setReviewCards(newSet.cards);
      setCurrentReviewIndex(0);
      setIsCardFlipped(false);
      setReviewAll(true);
      setSessionKnownCount(0);
      setSessionNotKnownCount(0);
      setView('review');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Start Review Session
  const startReview = async (set: FlashcardSet, all: boolean = false) => {
    setLoading(true);
    setError(null);
    try {
      const cards = await apiCall(`/sets/${set.id}/review?include_all=${all}`);
      setSelectedSet(set);
      setReviewCards(cards);
      setCurrentReviewIndex(0);
      setIsCardFlipped(false);
      setReviewAll(all);
      setSessionKnownCount(0);
      setSessionNotKnownCount(0);
      setView('review');
    } catch (err: any) {
      setError('Could not fetch review cards.');
    } finally {
      setLoading(false);
    }
  };

  // Submit Card Review (Known vs Not Known)
  const handleReviewAction = async (status: 'known' | 'not_known') => {
    if (reviewCards.length === 0) return;
    const currentCard = reviewCards[currentReviewIndex];

    try {
      // Optimistic update of local status/Leitner box to smooth transition
      await apiCall(`/cards/${currentCard.id}/review`, 'POST', { status });
      
      if (status === 'known') {
        setSessionKnownCount(prev => prev + 1);
      } else {
        setSessionNotKnownCount(prev => prev + 1);
      }

      // Check if we have more cards in the current session queue
      if (currentReviewIndex + 1 < reviewCards.length) {
        setIsCardFlipped(false);
        // Short timeout for visual rotation completion before index increment
        setTimeout(() => {
          setCurrentReviewIndex(prev => prev + 1);
        }, 150);
      } else {
        setView('completion');
      }
    } catch (err: any) {
      setError('Failed to update flashcard progress.');
    }
  };

  // Render Helper functions for Views
  const renderAuth = () => (
    <div className="auth-container">
      <div className="auth-card glass-panel">
        <div className="brand">
          <BrainCircuit size={32} className="brand-icon" />
          <span className="brand-name">SmartCards</span>
        </div>
        
        <h2 className="auth-title">
          {authMode === 'login' ? 'Welcome Back' : 'Get Started'}
        </h2>
        <p className="auth-subtitle">
          {authMode === 'login' 
            ? 'Sign in to access your study library' 
            : 'Create an account to build study flashcards with NLP'}
        </p>

        {error && <div className="error-message">{error}</div>}
        {success && <div className="error-message" style={{background: 'rgba(16, 185, 129, 0.1)', borderColor: 'var(--success)', color: 'var(--success)'}}>{success}</div>}

        <form onSubmit={handleAuthSubmit}>
          <div className="form-group">
            <label className="form-label">Email Address</label>
            <div className="input-wrapper">
              <Mail size={18} className="input-icon" />
              <input 
                type="email" 
                className="form-input" 
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Password</label>
            <div className="input-wrapper">
              <Lock size={18} className="input-icon" />
              <input 
                type="password" 
                className="form-input" 
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
          </div>

          <button type="submit" className="btn" disabled={loading}>
            {loading ? <span className="spinner" style={{width: 20, height: 20, borderTopColor: '#fff'}}></span> : (authMode === 'login' ? 'Sign In' : 'Sign Up')}
          </button>
        </form>

        <div className="auth-toggle">
          {authMode === 'login' ? (
            <>
              Don't have an account?{' '}
              <span className="auth-toggle-link" onClick={() => setAuthMode('signup')}>
                Register
              </span>
            </>
          ) : (
            <>
              Already have an account?{' '}
              <span className="auth-toggle-link" onClick={() => setAuthMode('login')}>
                Sign In
              </span>
            </>
          )}
        </div>
      </div>
    </div>
  );

  const renderDashboard = () => (
    <div className="content-container">
      <div className="dashboard-header">
        <div>
          <h1 className="dashboard-title">My Study Library</h1>
          <p className="dashboard-subtitle">Select a set to review or generate new flashcards</p>
        </div>
        <button className="btn btn-create" onClick={() => setView('create')}>
          <Plus size={20} />
          Create Flashcards
        </button>
      </div>

      {loading && sets.length === 0 ? (
        <div className="loading-overlay">
          <div className="spinner"></div>
          <span className="loading-text">Loading study library...</span>
        </div>
      ) : sets.length === 0 ? (
        <div className="empty-state glass-panel">
          <BookOpen size={48} className="empty-icon" />
          <h3 className="empty-title">Your library is empty</h3>
          <p className="empty-desc">
            Paste your biology, history, or science notes, and our AI will automatically parse the concepts and definitions into structured study cards.
          </p>
          <button className="btn" style={{width: 'auto'}} onClick={() => setView('create')}>
            Generate Your First Set
          </button>
        </div>
      ) : (
        <div className="sets-grid">
          {sets.map((set) => (
            <div 
              key={set.id} 
              className="set-card glass-panel"
              onClick={() => startReview(set, false)}
            >
              <h3 className="set-card-title">{set.title}</h3>
              <p className="set-card-notes">{set.notes_content}</p>
              
              <div className="set-card-footer">
                <span className="set-date">
                  {new Date(set.created_at).toLocaleDateString(undefined, {month: 'short', day: 'numeric'})}
                </span>
                <div className="set-stats">
                  <span className="stat-tag">{set.card_count} cards</span>
                  {set.known_count !== undefined && set.known_count > 0 && (
                    <span className="stat-tag known">{set.known_count} known</span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );

  const renderCreate = () => (
    <div className="content-container">
      <button className="btn btn-secondary btn-back" onClick={() => setView('dashboard')}>
        <ChevronLeft size={16} />
        Library Dashboard
      </button>

      <div className="generator-layout" style={{marginTop: 24}}>
        <div className="generator-card glass-panel">
          <h2 className="generator-title">Generate Smart Flashcards</h2>
          
          {error && <div className="error-message">{error}</div>}

          {loading ? (
            <div className="loading-overlay">
              <div className="spinner"></div>
              <span className="loading-text">NLP Pipeline Extracting Core Concepts & Building Questions...</span>
            </div>
          ) : (
            <form onSubmit={handleCreateSet}>
              <div className="form-group">
                <label className="form-label">Set Title</label>
                <div className="input-wrapper">
                  <input 
                    type="text" 
                    className="form-input" 
                    placeholder="e.g., Photosynthesis Chapter 3, American Revolution"
                    value={setTitle}
                    onChange={(e) => setSetTitle(e.target.value)}
                    style={{paddingLeft: 16}}
                    required
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Study Notes (Paste textbook paragraph or study notes)</label>
                <textarea 
                  className="form-input textarea-input"
                  placeholder="Paste your paragraph here. E.g., 'Photosynthesis is a process used by plants and other organisms to convert light energy into chemical energy. Cellular respiration is a set of metabolic reactions and processes that take place in the cells of organisms to convert biochemical energy from nutrients into adenosine triphosphate.'"
                  value={notesContent}
                  onChange={(e) => setNotesContent(e.target.value)}
                  required
                />
              </div>

              <div className="generator-actions">
                <button type="submit" className="btn">
                  <Sparkles size={18} />
                  Analyze and Generate
                </button>
                <button type="button" className="btn btn-secondary" onClick={() => setView('dashboard')}>
                  Cancel
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );

  const renderReview = () => {
    const isQueueEmpty = reviewCards.length === 0;
    const currentCard = !isQueueEmpty ? reviewCards[currentReviewIndex] : null;
    const progressPercent = isQueueEmpty 
      ? 0 
      : ((currentReviewIndex) / reviewCards.length) * 100;

    return (
      <div className="content-container">
        <div className="review-header">
          <button className="btn btn-secondary btn-back" onClick={() => { loadSets(); setView('dashboard'); }}>
            <ChevronLeft size={16} />
            Library Dashboard
          </button>
          
          {!isQueueEmpty && (
            <div className="review-progress">
              <span className="progress-text">Card {currentReviewIndex + 1} of {reviewCards.length}</span>
              <div className="progress-bar-bg">
                <div className="progress-bar-fill" style={{width: `${progressPercent}%`}}></div>
              </div>
            </div>
          )}
        </div>

        {error && <div className="error-message">{error}</div>}

        {isQueueEmpty ? (
          <div className="empty-state glass-panel">
            <CheckCircle2 size={48} className="empty-icon" style={{color: 'var(--success)'}} />
            <h3 className="empty-title">All Caught Up!</h3>
            <p className="empty-desc">
              You have no cards due for review in <strong>{selectedSet?.title}</strong> right now. This is spaced repetition working!
            </p>
            <div style={{display: 'flex', gap: 16, marginTop: 12}}>
              <button 
                className="btn btn-secondary" 
                style={{width: 'auto'}}
                onClick={() => startReview(selectedSet!, true)}
              >
                <RotateCcw size={16} />
                Review All Anyway
              </button>
              <button 
                className="btn" 
                style={{width: 'auto'}}
                onClick={() => { loadSets(); setView('dashboard'); }}
              >
                Back to Dashboard
              </button>
            </div>
          </div>
        ) : (
          <div className="card-viewer">
            <div className="review-mode-toggle">
              <button 
                className={`toggle-opt ${!reviewAll ? 'active' : ''}`}
                onClick={() => startReview(selectedSet!, false)}
              >
                Due Cards Only
              </button>
              <button 
                className={`toggle-opt ${reviewAll ? 'active' : ''}`}
                onClick={() => startReview(selectedSet!, true)}
              >
                All Cards
              </button>
            </div>

            <div className="flashcard-wrapper">
              <div 
                className={`flashcard-3d ${isCardFlipped ? 'is-flipped' : ''}`}
                onClick={() => setIsCardFlipped(!isCardFlipped)}
              >
                {/* Front Face */}
                <div className="flashcard-face flashcard-front">
                  <span className="leitner-badge">Box {currentCard?.leitner_box}</span>
                  <div className="card-label">Question</div>
                  <div className="card-text cloze-text">{currentCard?.question}</div>
                  <div className="card-hint">
                    <HelpCircle size={14} /> Click card to flip
                  </div>
                </div>

                {/* Back Face */}
                <div className="flashcard-face flashcard-back">
                  <span className="leitner-badge">Box {currentCard?.leitner_box}</span>
                  <div className="card-label">Answer</div>
                  <div className="card-text">{currentCard?.answer}</div>
                  <div className="card-hint">
                    <HelpCircle size={14} /> Click to view question
                  </div>
                </div>
              </div>
            </div>

            {/* Verification controls */}
            {isCardFlipped && (
              <div className="card-controls">
                <button 
                  className="btn btn-not-known" 
                  onClick={() => handleReviewAction('not_known')}
                >
                  <XCircle size={18} />
                  Not Known (Repeats soon)
                </button>
                <button 
                  className="btn btn-known" 
                  onClick={() => handleReviewAction('known')}
                >
                  <CheckCircle2 size={18} />
                  Known (Pass Box)
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  const renderCompletion = () => (
    <div className="content-container">
      <div className="completion-card glass-panel">
        <Layers size={48} className="completion-icon" />
        <h2 className="completion-title">Session Complete!</h2>
        <p className="completion-desc">
          You've completed your review session for <strong>{selectedSet?.title}</strong>.
        </p>

        <div className="completion-stats">
          <div className="comp-stat-box">
            <div className="comp-stat-val" style={{color: 'var(--success)'}}>{sessionKnownCount}</div>
            <div className="comp-stat-lbl">Known</div>
          </div>
          <div className="comp-stat-box">
            <div className="comp-stat-val" style={{color: 'var(--danger)'}}>{sessionNotKnownCount}</div>
            <div className="comp-stat-lbl">Not Known</div>
          </div>
        </div>

        <div style={{display: 'flex', gap: 16, width: '100%', marginTop: 8}}>
          <button className="btn" onClick={() => startReview(selectedSet!, false)}>
            <RotateCcw size={16} />
            Review Again
          </button>
          <button className="btn btn-secondary" onClick={() => { loadSets(); setView('dashboard'); }}>
            Dashboard
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="app-layout">
      {view !== 'auth' && (
        <header className="navbar">
          <div className="brand" style={{marginBottom: 0, cursor: 'pointer'}} onClick={() => { loadSets(); setView('dashboard'); }}>
            <BrainCircuit size={24} className="brand-icon" />
            <span className="brand-name">SmartCards</span>
          </div>
          <div className="nav-user">
            <button className="btn-logout" onClick={handleLogout}>
              <LogOut size={14} />
              Logout
            </button>
          </div>
        </header>
      )}

      {view === 'auth' && renderAuth()}
      {view === 'dashboard' && renderDashboard()}
      {view === 'create' && renderCreate()}
      {view === 'review' && renderReview()}
      {view === 'completion' && renderCompletion()}
    </div>
  );
}
