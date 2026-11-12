"""Google Drive OAuth 2.0 Authentication handler."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Dict, Any

# Allow oauthlib to proceed when scopes are adjusted by the authorization server
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource

# Scope for reading files and metadata from Google Drive
SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]

CREDENTIALS_PATH = Path("credentials.json")
TOKEN_PATH = Path("token.json")


def _sync_credentials_from_secrets() -> None:
    """Ensure credentials.json and token.json are written to disk if provided via environment or Streamlit secrets."""
    if not CREDENTIALS_PATH.exists():
        creds_json = os.getenv("GDRIVE_CREDENTIALS_JSON")
        if not creds_json:
            try:
                import streamlit as st
                if "GDRIVE_CREDENTIALS_JSON" in st.secrets:
                    creds_json = str(st.secrets["GDRIVE_CREDENTIALS_JSON"])
            except Exception:
                pass
        if creds_json:
            CREDENTIALS_PATH.write_text(creds_json.strip(), encoding="utf-8")

    if not TOKEN_PATH.exists():
        token_json = os.getenv("GDRIVE_TOKEN_JSON")
        if not token_json:
            try:
                import streamlit as st
                if "GDRIVE_TOKEN_JSON" in st.secrets:
                    token_json = str(st.secrets["GDRIVE_TOKEN_JSON"])
            except Exception:
                pass
        if token_json:
            TOKEN_PATH.write_text(token_json.strip(), encoding="utf-8")


def get_auth_status() -> Dict[str, Any]:
    """Check whether credentials.json exists and if a valid token.json is present."""
    _sync_credentials_from_secrets()
    has_creds = CREDENTIALS_PATH.exists()
    has_token = TOKEN_PATH.exists()
    is_valid = False
    user_email = None
    err_msg = None

    if has_token:
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
            if creds and creds.valid:
                is_valid = True
            elif creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    with open(TOKEN_PATH, "w") as token_file:
                        token_file.write(creds.to_json())
                    is_valid = True
                except Exception as rf_err:
                    err_msg = f"Token kadaluarsa dan gagal diperbarui: {rf_err}"
            # Attempt to fetch user email if valid
            if is_valid:
                try:
                    oauth2_service = build("oauth2", "v2", credentials=creds)
                    info = oauth2_service.userinfo().get().execute()
                    user_email = info.get("email")
                except Exception:
                    pass
        except Exception as e:
            err_msg = str(e)

    return {
        "is_authenticated": is_valid,
        "has_credentials_file": has_creds,
        "token_exists": has_token,
        "email": user_email,
        "error": err_msg,
    }


def authenticate_google_drive(port: int = 0) -> Optional[Credentials]:
    """Run interactive OAuth 2.0 authorization flow in local browser and save token.json."""
    if not CREDENTIALS_PATH.exists():
        raise FileNotFoundError(
            "File 'credentials.json' tidak ditemukan di root direktori proyek. "
            "Harap unduh OAuth Client ID (Desktop App) dari Google Cloud Console dan simpan sebagai credentials.json."
        )

    creds = None
    if TOKEN_PATH.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None

        if not creds:
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
            creds = flow.run_local_server(
                port=port,
                prompt="consent",
                access_type="offline",
                timeout_seconds=180,
            )

        # Check if the Drive scope was actually granted by the user
        granted_scopes = creds.scopes or []
        if not any("drive" in s for s in granted_scopes):
            raise PermissionError(
                "Kotak centang izin akses Google Drive belum dicentang di halaman persetujuan Google.\n\n"
                "Harap ulangi klik tombol hubungkan, lalu pastikan Anda mencentang (ceklis) opsi "
                "'Lihat dan unduh semua file Google Drive Anda' sebelum menekan Lanjutkan / Continue."
            )

        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())

    return creds


def get_drive_service(interactive: bool = False, port: int = 0) -> Optional[Resource]:
    """Return an authorized Google Drive v3 Resource service instance."""
    status = get_auth_status()
    if status["is_authenticated"]:
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
        return build("drive", "v3", credentials=creds)

    if interactive:
        creds = authenticate_google_drive(port=port)
        if creds:
            return build("drive", "v3", credentials=creds)

    return None


def disconnect_google_drive() -> None:
    """Remove local token.json to disconnect the Google account."""
    if TOKEN_PATH.exists():
        TOKEN_PATH.unlink()
