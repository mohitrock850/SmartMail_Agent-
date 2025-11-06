import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

# --- CRITICAL ---
# This SALT *must* be the exact same as the one in your
# 'gmail_service.py' file.
SALT = b'salt_password123' 

def get_encryption_key(password: str) -> bytes:
    """Derives a Fernet-compatible key from a password."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=SALT,
        iterations=100000,
        backend=default_backend()
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key

def encrypt_file():
    """Creates a test file and encrypts it."""
    
    # 1. Create a dummy file to encrypt
    file_to_encrypt = "test.txt"
    content = (
        "This is a top-secret message. If you are reading this, "
        "the decryption was successful!"
    )
    with open(file_to_encrypt, 'w') as f:
        f.write(content)
    
    print(f"Created '{file_to_encrypt}' with secret content.")

    # 2. Get password
    password = input("Enter a password for your file: ")
    if not password:
        print("Password cannot be empty.")
        return

    # 3. Generate key and encrypt
    try:
        key = get_encryption_key(password)
        f = Fernet(key)
        
        with open(file_to_encrypt, 'rb') as f_in:
            data = f_in.read()
        
        encrypted_data = f.encrypt(data)
        
        # 4. Write the new encrypted file
        encrypted_filename = f"{file_to_encrypt}.enc"
        with open(encrypted_filename, 'wb') as f_out:
            f_out.write(encrypted_data)
            
        print("-" * 30)
        print(f"✅ Success! Encrypted file saved as: {encrypted_filename}")
        print(f"Your password is: {password}")
        print("Now, email this file to yourself!")
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    encrypt_file()