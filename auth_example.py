import time
from auth import verify_hku_credentials

# Test example
print("HKU Portal Authentication Test")
print("=" * 50)

# Get email and password from user input
test_email = "u3665467@connect.hku.hk"
test_password = "Renliubo1891412"

print("\nStarting verification...")
start = time.time()
result = verify_hku_credentials(test_email, test_password, headless=True, verbose=True)
end = time.time()
print("\n" + "=" * 50)
print("Verification Result:")
print(result)
print(f"Verification completed in {end - start:.2f} seconds")
print("=" * 50)
