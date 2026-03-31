# src/emotion_classifier.py

def classify_emotion(text: str) -> str:
    """
    Lightweight emotion classifier for tone adaptation.
    Returns one of: frustration, fatigue, sadness, anxiety, positive, neutral.
    """
    lower = text.lower()

    if any(w in lower for w in ["frustrated", "annoyed", "irritated", "angry"]):
        return "frustration"

    if any(w in lower for w in ["tired", "exhausted", "burned out", "fatigued"]):
        return "fatigue"

    if any(w in lower for w in ["sad", "upset", "down", "depressed"]):
        return "sadness"

    if any(w in lower for w in ["anxious", "worried", "nervous", "scared"]):
        return "anxiety"

    if any(w in lower for w in ["happy", "excited", "glad", "relieved"]):
        return "positive"

    return "neutral"
