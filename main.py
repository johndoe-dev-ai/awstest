from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
from authlib.integrations.starlette_client import OAuth
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
load_dotenv()
import os
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

app = FastAPI()

# Enable sessions
app.add_middleware(SessionMiddleware, secret_key="supersecret")

# CORS for local Streamlit dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth = OAuth()
oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

@app.get("/login")
async def login(request: Request):
    redirect_uri = "http://localhost:8000/auth/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)

@app.get("/auth/callback")
async def auth_callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    print("OAuth token response:", token)  # Debug: print the token
    id_token = token.get("id_token")
    if not id_token:
        return JSONResponse(status_code=400, content={"error": "No id_token in token response", "token": token})
    # Do not call parse_id_token here
    return RedirectResponse(url=f"http://localhost:8501?token={id_token}")

@app.get("/verify")
async def verify(token: str):
    try:
        idinfo = google_id_token.verify_oauth2_token(token, google_requests.Request())
        return {"valid": True, "user": idinfo}
    except Exception as e:
        return JSONResponse(status_code=401, content={"valid": False, "error": str(e)})