import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import nlp

def run_test():
    test_text = (
        "Photosynthesis is a process used by plants and other organisms to convert light energy "
        "into chemical energy. During this process, light energy is captured and used to convert "
        "water, carbon dioxide, and minerals into oxygen and energy-rich organic compounds. "
        "Mitochondria are double-membrane-bound organelles found in most eukaryotic organisms. "
        "They generate most of the cell's supply of adenosine triphosphate, which is used as "
        "a source of chemical energy. The term mitochondrion comes from the Greek words mitos, "
        "meaning thread, and chondros, meaning granule."
    )
    
    print("--- INPUT TEXT ---")
    print(test_text)
    print("\n--- RUNNING GENERATION ---")
    
    # Try generating cards
    cards = nlp.generate_flashcards(test_text, max_cards=5)
    
    print(f"\nSuccessfully generated {len(cards)} cards:")
    for i, card in enumerate(cards):
        print(f"\n[Card {i+1}]")
        print(f"Q: {card['question']}")
        print(f"A: {card['answer']}")

if __name__ == "__main__":
    run_test()
