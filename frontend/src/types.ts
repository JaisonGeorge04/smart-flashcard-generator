export interface User {
  id: number;
  email: string;
}

export interface Flashcard {
  id: number;
  set_id: number;
  question: string;
  answer: string;
  status: 'new' | 'known' | 'not_known';
  leitner_box: number;
  next_review_at: string;
  created_at: string;
}

export interface FlashcardSet {
  id: number;
  user_id: number;
  title: string;
  notes_content: string;
  created_at: string;
  card_count?: number;
  known_count?: number;
  cards?: Flashcard[];
}
