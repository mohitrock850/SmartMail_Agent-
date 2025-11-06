import typer
from google_auth_oauthlib.flow import InstalledAppFlow

# --- Define all scopes here ---
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send' 
]
REDIRECT_URI = 'http://localhost:5001/'


def main():
    """
    Runs the Google OAuth flow to get token.json
    """
    print("Starting authentication flow...")
    
    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', 
            SCOPES,  
            redirect_uri=REDIRECT_URI
        )
        
        # We explicitly ask for 'offline' access (to get a refresh_token)
        # and 'consent' to ensure the user is re-prompted.
        creds = flow.run_local_server(
            port=5001,
            access_type='offline',
            prompt='consent'
        )
        
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
            
        print("\n✅ Authentication successful! 'token.json' saved.")
        print("You can now start the FastAPI server with: uvicorn main:app --reload")
        
    except FileNotFoundError:
        print("\n❌ ERROR: 'credentials.json' not found.")
        print("Please make sure you have downloaded your credentials from Google Cloud.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    typer.run(main)