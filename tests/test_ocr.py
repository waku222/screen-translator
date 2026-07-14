from ocrmac import ocrmac
print("Import successful")
try:
    # Use a dummy small white image or just check initialization
    print("Testing OCR initialization...")
    # annotation = ocrmac.OCR('test.png').recognize()
    print("OCR module seems loadable.")
except Exception as e:
    print(f"Error: {e}")
