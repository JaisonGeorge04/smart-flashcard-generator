import urllib.request
import json
import time

API_URL = "http://127.0.0.1:8080"

def make_request(url, method="GET", data=None, token=None):
    headers = {
        "Content-Type": "application/json"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
        
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8") if data else None,
        headers=headers,
        method=method
    )
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode("utf-8")
        try:
            parsed_error = json.loads(error_msg)
            detail = parsed_error.get("detail", error_msg)
        except Exception:
            detail = error_msg
        print(f"Error {e.code}: {detail}")
        return e.code, detail

def run_checks():
    timestamp = int(time.time())
    email = f"student_{timestamp}@example.com"
    password = "SecurePassword123!"
    
    print("==================================================")
    print("          STARTING END-TO-END CHECKING            ")
    print("==================================================")
    
    # 1. Register User
    print(f"\n1. Registering user: {email}...")
    status, res = make_request(
        f"{API_URL}/auth/register", 
        "POST", 
        {"email": email, "password": password}
    )
    if status == 201:
        print("[OK] User registered successfully!")
    else:
        print("[ERR] Registration failed!")
        return

    # 2. Login User
    print("\n2. Logging in to obtain JWT Access Token...")
    status, res = make_request(
        f"{API_URL}/auth/login", 
        "POST", 
        {"email": email, "password": password}
    )
    if status == 200:
        token = res["access_token"]
        print("[OK] Login successful!")
        print(f"  Token (truncated): {token[:40]}...")
    else:
        print("[ERR] Login failed!")
        return

    # 3. Create Flashcard Set using NLP Paragraph
    print("\n3. Sending notes paragraph to generate AI flashcards...")
    notes = (
        "Cellular respiration is a set of metabolic reactions that take place in cells to convert "
        "chemical energy from nutrients into adenosine triphosphate. Mitochondria are the organelles "
        "responsible for producing ATP. Glycolysis is the first metabolic pathway of cellular respiration."
    )
    status, res = make_request(
        f"{API_URL}/sets",
        "POST",
        {
            "title": "Cell Biology 101",
            "notes_content": notes
        },
        token=token
    )
    if status == 201:
        set_id = res["id"]
        cards = res["cards"]
        print(f"[OK] Successfully created set: '{res['title']}' (ID: {set_id})")
        print(f"[OK] NLP Pipeline generated {len(cards)} flashcards!")
        for idx, card in enumerate(cards):
            print(f"  [{idx+1}] Q: {card['question'].replace(chr(10), ' ')}")
            print(f"      A: {card['answer']}")
    else:
        print("[ERR] Card generation failed!")
        return

    # 4. Fetch Cards Due for Review
    print("\n4. Retrieving cards due for review...")
    status, res = make_request(
        f"{API_URL}/sets/{set_id}/review",
        "GET",
        token=token
    )
    if status == 200:
        print(f"[OK] Found {len(res)} cards due for review.")
        if res:
            target_card = res[0]
            print(f"  Target card to review (ID: {target_card['id']}):")
            print(f"  Q: {target_card['question'].replace(chr(10), ' ')}")
    else:
        print("[ERR] Could not fetch review cards.")
        return

    # 5. Submit a Spaced Repetition Review (Known)
    print(f"\n5. Simulating review: Marking Card ID {target_card['id']} as 'known'...")
    status, res = make_request(
        f"{API_URL}/cards/{target_card['id']}/review",
        "POST",
        {"status": "known"},
        token=token
    )
    if status == 200:
        print("[OK] Spaced repetition review submitted successfully!")
        print(f"  New Leitner Box: {res['leitner_box']}")
        print(f"  Next Review Scheduled At: {res['next_review_at']}")
    else:
        print("[ERR] Review submission failed.")
        return

    print("\n==================================================")
    print("      [SUCCESS] ALL ENDPOINTS FUNCTIONING PERFECTLY!      ")
    print("==================================================")

if __name__ == "__main__":
    run_checks()
