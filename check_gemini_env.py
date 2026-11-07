import os

key = os.getenv("GEMINI_API_KEY")

print("GEMINI_API_KEY found:", key is not None)
print("Key length:", len(key) if key else 0)
print("Starts with:", key[:6] + "..." if key else "NONE")
print("Contains quotes:", key.startswith(('"', "'")) if key else False)
print("Contains spaces:", any(c.isspace() for c in key) if key else False)
