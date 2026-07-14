from src.translator.google_translator import GoogleTranslator
print("Testing Translator...")
try:
    t = GoogleTranslator()
    res = t.translate("Hello world")
    print(f"Result: {res}")
except Exception as e:
    print(f"Translation failed: {e}")
