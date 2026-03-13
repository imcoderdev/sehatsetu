import os
from supabase import create_client
from dotenv import load_dotenv

# Load env from root
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(base_dir, '.env')
load_dotenv(dotenv_path=env_path)

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")  # Fixed variable name

if not url or not key:
    print(f"Error: Missing credentials in {env_path}")
    exit(1)

supabase = create_client(url, key)

users = [
    {"email": "doctor@sehatsetu.com", "password": "password123"},
    {"email": "pharmacist@sehatsetu.com", "password": "password123"}
]

print("--- SehatSetu Test User Creation ---")

for user in users:
    try:
        # Sign up users
        supabase.auth.sign_up({
            "email": user["email"],
            "password": user["password"]
        })
        print(f"Success: Created {user['email']}")
    except Exception as e:
        if "already registered" in str(e).lower():
            print(f"Info: {user['email']} already exists.")
        else:
            print(f"Error creating {user['email']}: {str(e)}")

print("\nCredentials for testing:")
print("Doctor: doctor@sehatsetu.com / password123")
print("Pharmacist: pharmacist@sehatsetu.com / password123")
