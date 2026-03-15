from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import json
from db import get_token, save_token
import os

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

async def get_drive_service():
    token = await get_token()
    if token:
        creds = Credentials.from_authorized_user_info(json.loads(token), SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
    else:
        credentials_json = json.loads(os.getenv("GOOGLE_CREDENTIALS_JSON"))
        flow = InstalledAppFlow.from_client_config(credentials_json, SCOPES)
        creds = flow.run_local_server(port=0)

    await save_token(creds.to_json())
    return build("drive", "v3", credentials=creds)