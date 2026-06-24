import re
import math
from collections import Counter
import logging

logger = logging.getLogger("nlp")

# Global flags for available libraries
SPACY_AVAILABLE = False
NLTK_AVAILABLE = False

# Try to load spaCy
try:
    import spacy
    try:
        nlp = spacy.load("en_core_web_sm")
        SPACY_AVAILABLE = True
        logger.info("spaCy en_core_web_sm loaded successfully.")
    except Exception as e:
        logger.warning(f"spaCy model en_core_web_sm not found. Attempting fallback to NLTK. Error: {e}")
except ImportError:
    logger.warning("spaCy not installed. Attempting fallback to NLTK.")

# Try to load NLTK
if not SPACY_AVAILABLE:
    try:
        import nltk
        from nltk.tokenize import sent_tokenize, word_tokenize
        from nltk import pos_tag, ne_chunk
        NLTK_AVAILABLE = True
        logger.info("NLTK loaded successfully.")
    except Exception as e:
        logger.error(f"NLTK failed to load: {e}")


def clean_text(text: str) -> str:
    """Basic cleaning of notes text."""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def calculate_sentence_scores(sentences: list, all_text: str) -> dict:
    """
    Ranks sentences using a simple word-frequency scoring (TF-IDF-like heuristic).
    Sentences containing more frequent content words get higher scores.
    """
    # Simple tokenization for word frequencies
    words = re.findall(r'\b\w{4,}\b', all_text.lower())
    word_counts = Counter(words)
    
    scores = {}
    for i, sent in enumerate(sentences):
        sent_words = re.findall(r'\b\w{4,}\b', sent.lower())
        if not sent_words:
            scores[i] = 0
            continue
        
        # Sum of frequencies of words in sentence, normalized by sentence length
        score = sum(word_counts[w] for w in sent_words) / math.sqrt(len(sent_words))
        
        # Boost sentences that look like definitions (contain "is", "are", "refers to", etc.)
        if re.search(r'\b(is|are|was|were|refers to|means|defined as|denotes)\b', sent.lower()):
            score *= 1.5
            
        scores[i] = score
        
    return scores


def generate_flashcards_spacy(text: str, max_cards: int = 7) -> list:
    """Generates flashcards using spaCy."""
    doc = nlp(text)
    sentences = [sent.text.strip() for sent in doc.sents if len(sent.text.strip()) > 15]
    
    if not sentences:
        return []
        
    sentence_scores = calculate_sentence_scores(sentences, text)
    # Sort sentences by score descending
    ranked_indices = sorted(sentence_scores.keys(), key=lambda k: sentence_scores[k], reverse=True)
    
    flashcards = []
    used_questions = set()
    
    # Process top sentences to extract definition questions or clozes
    for idx in ranked_indices[:min(len(ranked_indices), max_cards * 2)]:
        sent_text = sentences[idx]
        sent_doc = nlp(sent_text)
        
        # Try to find definition patterns: "X is Y" or "X refers to Y"
        definition_found = False
        
        # Look for root copula "be" or verbs like "refer", "mean", "define", "represent"
        for token in sent_doc:
            if token.pos_ == "VERB" or token.lemma_ == "be":
                # Check for "is/are/was/were"
                is_copula = token.lemma_ == "be"
                is_definition_verb = token.lemma_ in ["refer", "mean", "define", "represent", "denote"]
                
                if is_copula or is_definition_verb:
                    # Find subject (nsubj) - only active subjects for definitions
                    subjects = [w for w in token.lefts if w.dep_ == "nsubj"]
                    if not subjects:
                        # Try finding subject in the whole sentence before the verb
                        subjects = [w for w in sent_doc if w.dep_ == "nsubj" and w.i < token.i]
                        
                    if subjects:
                        subj = subjects[0]
                        
                        # Skip pronoun subjects for definition questions
                        if subj.pos_ == "PRON" or subj.text.lower() in ("it", "they", "he", "she", "we", "i", "you", "this", "that", "these", "those"):
                            continue
                            
                        # Reconstruct the full subject phrase (e.g. "Photosynthesis")
                        # Get all subtree tokens of the subject that come before the verb
                        subj_phrase = " ".join([w.text for w in subj.subtree if w.i < token.i]).strip()
                        
                        # Reconstruct definition phrase (everything from verb onwards)
                        def_phrase = " ".join([w.text for w in sent_doc if w.i >= token.i]).strip()
                        
                        if len(subj_phrase) > 2 and len(def_phrase) > 10:
                            # Let's format the question nicely
                            question = f"What is {subj_phrase}?" if is_copula else f"What does {subj_phrase} {token.lemma_}?"
                            # Capitalize first letter, ensure trailing question mark
                            question = question[0].upper() + question[1:]
                            if not question.endswith("?"):
                                question += "?"
                                
                            answer = sent_text
                            
                            if question not in used_questions:
                                flashcards.append({"question": question, "answer": answer})
                                used_questions.add(question)
                                definition_found = True
                                break
                                
        if definition_found:
            if len(flashcards) >= max_cards:
                break
            continue
            
        # Cloze Deletion Fallback: Find the most important noun chunk or entity in this sentence
        # Get entities
        ents = [ent for ent in sent_doc.ents if ent.label_ in ("PERSON", "ORG", "GPE", "PRODUCT", "WORK_OF_ART", "EVENT", "LAW", "NORP")]
        
        target_phrase = None
        if ents:
            # Pick the longest named entity as the target
            target_phrase = sorted(ents, key=lambda e: len(e.text), reverse=True)[0].text
        else:
            # Fall back to noun chunks
            noun_chunks = [chunk for chunk in sent_doc.noun_chunks if len(chunk.text) > 3]
            # Avoid chunks that contain pronouns or common short words
            filtered_chunks = [c for c in noun_chunks if not any(w.lower_ in ("it", "they", "he", "she", "this", "these", "that", "those", "what", "which") for w in c)]
            if filtered_chunks:
                # Pick the chunk with the highest average word length (likely technical terms)
                target_phrase = sorted(filtered_chunks, key=lambda c: sum(len(w.text) for w in c)/len(c), reverse=True)[0].text
                
        if target_phrase and len(target_phrase) > 2:
            # Create a Cloze question
            # Escape target_phrase for safe regex replacement
            escaped_target = re.escape(target_phrase)
            # Match case-insensitively but respect word boundaries if possible
            pattern = re.compile(rf'\b{escaped_target}\b', re.IGNORECASE)
            
            # If word boundaries don't match, try literal replacement
            if not pattern.search(sent_text):
                pattern = re.compile(escaped_target, re.IGNORECASE)
                
            cloze_text = pattern.sub("_______", sent_text)
            
            if "_______" in cloze_text:
                question = f"Fill in the blank:\n{cloze_text}"
                answer = target_phrase
                
                if question not in used_questions:
                    flashcards.append({"question": question, "answer": answer})
                    used_questions.add(question)
                    
        if len(flashcards) >= max_cards:
            break
            
    return flashcards


def generate_flashcards_nltk(text: str, max_cards: int = 7) -> list:
    """Generates flashcards using NLTK as a pure-python fallback."""
    try:
        sentences = sent_tokenize(text)
    except Exception:
        # Simplest sentence splitter if NLTK data isn't loaded properly
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if len(s.strip()) > 15]
        
    sentences = [s for s in sentences if len(s) > 15]
    if not sentences:
        return []
        
    sentence_scores = calculate_sentence_scores(sentences, text)
    ranked_indices = sorted(sentence_scores.keys(), key=lambda k: sentence_scores[k], reverse=True)
    
    flashcards = []
    used_questions = set()
    
    for idx in ranked_indices[:min(len(ranked_indices), max_cards * 2)]:
        sent_text = sentences[idx]
        
        # Check for definition pattern using regex
        def_match = re.search(r'\b([^,.?;:]+?)\s+(is|are|was|were|refers to|means|represents)\s+([^,.?;:]+)', sent_text, re.IGNORECASE)
        if def_match:
            term = def_match.group(1).strip()
            verb = def_match.group(2).strip().lower()
            definition = def_match.group(3).strip()
            
            # Filter out pronouns and very short words
            if len(term) > 3 and not any(w in term.lower().split() for w in ["it", "they", "he", "she", "there", "this"]):
                question = f"What is {term}?" if verb in ["is", "are", "was", "were"] else f"What does {term} {verb}?"
                question = question[0].upper() + question[1:]
                answer = sent_text
                
                if question not in used_questions:
                    flashcards.append({"question": question, "answer": answer})
                    used_questions.add(question)
                    if len(flashcards) >= max_cards:
                        break
                    continue
                    
        # Cloze Deletion Fallback
        # Tokenize and POS tag
        try:
            words = word_tokenize(sent_text)
            tagged = pos_tag(words)
            # Find Proper Nouns (NNP) or Nouns (NN/NNS)
            nouns = [w for w, tag in tagged if tag in ("NNP", "NN", "NNS") and len(w) > 3]
        except Exception:
            # Regex fallback for words
            nouns = [w for w in re.findall(r'\b\w{4,}\b', sent_text) if w.lower() not in ["this", "that", "with", "from", "their"]]
            
        if nouns:
            # Pick a noun (prefer NNP if present)
            # We sort Noun candidates: Proper nouns first, then count length
            # To simulate POS check without tagging if POS tagging fails:
            nnp_candidates = [w for w in nouns if w[0].isupper()]
            best_noun = nnp_candidates[0] if nnp_candidates else sorted(nouns, key=len, reverse=True)[0]
            
            # Replace noun
            escaped_noun = re.escape(best_noun)
            pattern = re.compile(rf'\b{escaped_noun}\b', re.IGNORECASE)
            cloze_text = pattern.sub("_______", sent_text)
            
            if "_______" in cloze_text:
                question = f"Fill in the blank:\n{cloze_text}"
                answer = best_noun
                
                if question not in used_questions:
                    flashcards.append({"question": question, "answer": answer})
                    used_questions.add(question)
                    
        if len(flashcards) >= max_cards:
            break
            
    return flashcards


def generate_flashcards(text: str, max_cards: int = 7) -> list:
    """Main generation entry point. Routes to spaCy or NLTK depending on availability."""
    cleaned = clean_text(text)
    if not cleaned or len(cleaned) < 10:
        return []
        
    if SPACY_AVAILABLE:
        try:
            return generate_flashcards_spacy(cleaned, max_cards)
        except Exception as e:
            logger.error(f"Error generating with spaCy, falling back to NLTK: {e}")
            
    if NLTK_AVAILABLE:
        try:
            return generate_flashcards_nltk(cleaned, max_cards)
        except Exception as e:
            logger.error(f"Error generating with NLTK, falling back to basic regex: {e}")
            
    # Basic Regex Fallback (completely self-contained, no external tools required)
    return generate_flashcards_nltk(cleaned, max_cards)
