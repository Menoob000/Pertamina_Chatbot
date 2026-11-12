"""Streamlit UI component for Google Drive RKS integration inside Pengaturan Tambahan."""
from __future__ import annotations

import importlib
import streamlit as st
from . import auth
from .sync import load_gdrive_config, sync_google_drive


def render_gdrive_settings_section():
    """Renders the Google Drive integration section inside an expander or settings block."""
    importlib.reload(auth)
    get_auth_status = auth.get_auth_status
    get_drive_service = auth.get_drive_service
    disconnect_google_drive = auth.disconnect_google_drive
    st.markdown("**☁️ Integrasi Google Drive (RKS Knowledge Base)**")
    st.caption("Sinkronkan dokumen contoh RKS dari folder Google Drive langsung ke database PostgreSQL & Vector Store.")

    auth_status = get_auth_status()
    cfg = load_gdrive_config()

    if not auth_status["has_credentials_file"]:
        st.warning(
            "⚠️ Berkas `credentials.json` belum ditemukan di direktori proyek.\n\n"
            "**Langkah penyiapan:**\n"
            "1. Buka **Google Cloud Console** dan aktifkan **Google Drive API**.\n"
            "2. Buat **OAuth 2.0 Client ID** (pilih tipe *Desktop App*).\n"
            "3. Unduh berkas JSON kredensial tersebut, beri nama `credentials.json`, dan letakkan di root folder proyek ini."
        )
        return

    # Connection Status
    if auth_status["is_authenticated"]:
        email_str = auth_status.get("email") or "Akun Google"
        st.success(f"🟢 **Terhubung**: `{email_str}`")
        if st.button("🚪 Putuskan Akun Google", key="btn_gdrive_disconnect"):
            disconnect_google_drive()
            st.rerun()
    else:
        st.info("⚪ Akun Google belum terhubung. Klik tombol di bawah untuk otorisasi melalui browser.")
        if st.button("🔗 Hubungkan Akun Google Drive", key="btn_gdrive_connect", type="primary", use_container_width=True):
            with st.spinner("Membuka browser untuk otorisasi akun Google..."):
                try:
                    svc = get_drive_service(interactive=True, port=0)
                    if svc:
                        st.success("✅ Berhasil menghubungkan akun Google!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Gagal melakukan otorisasi: {e}")
            return

    st.write("")

    # Folder ID Input & Synchronization
    folder_id = st.text_input(
        "Google Drive Folder ID atau URL Folder",
        value=cfg.get("folder_id", ""),
        help="Salin ID folder dari URL Google Drive (contoh: 1BxiMVs0XRA5nFMdKvBHK...)",
        key="gdrive_folder_id_input",
    )

    last_sync = cfg.get("last_sync") or "Belum pernah"
    total_files = cfg.get("total_synced_files", 0)
    st.caption(f"🕒 Terakhir disinkronkan: **{last_sync}** · Total berkas di Drive: **{total_files} file**")

    if st.button("🔄 Sinkronkan Sekarang", key="btn_run_gdrive_sync", type="primary", use_container_width=True):
        if not folder_id.strip():
            st.error("Masukkan Google Drive Folder ID terlebih dahulu.")
        else:
            with st.spinner("Menghubungi Google Drive dan menyinkronkan dokumen ke PostgreSQL..."):
                res = sync_google_drive(folder_id=folder_id)
                if res.get("success"):
                    st.success(f"✅ {res.get('message')}")
                    # Show detailed chips
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("File Baru", len(res.get("downloaded", [])))
                    c2.metric("Diperbarui", len(res.get("updated", [])))
                    c3.metric("Dihapus", len(res.get("deleted", [])))
                    c4.metric("Tidak Berubah", len(res.get("skipped", [])))
                    st.rerun()
                else:
                    st.error(f"Gagal sinkronisasi: {res.get('message')}")
