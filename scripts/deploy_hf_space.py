"""Deploy backend FastAPI ke Hugging Face Spaces (SDK Docker).

Langkah:
  1. Ambil snapshot file yang ter-commit (git archive HEAD), tanpa Frontend/, output/, tests/.
  2. Tambahkan deploy/hf-space/Dockerfile dan README.md ke root snapshot.
  3. Buat Space (bila belum ada), set secrets & variables dari .env, lalu upload.

Token HF diambil dari (urutan): --token, env HF_DEPLOY_TOKEN, login `hf auth login`.
HF_TOKEN di .env sengaja TIDAK dipakai (itu token baca untuk runtime).

Contoh:
  .venv/Scripts/python.exe scripts/deploy_hf_space.py --space pertamina-chatbot-backend
  .venv/Scripts/python.exe scripts/deploy_hf_space.py --space <nama> --cors https://app.vercel.app --skip-upload
"""
from __future__ import annotations

import argparse
import io
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

from dotenv import dotenv_values
from huggingface_hub import HfApi, get_token

ROOT = Path(__file__).resolve().parents[1]
HF_DIR = ROOT / "deploy" / "hf-space"

# Folder/file ter-commit yang tidak perlu ada di image backend.
EXCLUDE_TOP = {"Frontend", "frontend", "output", "tests", ".github", ".vscode"}

# Dikirim sebagai Secret (tersembunyi).
SECRET_KEYS = [
    "DATABASE_URL",
    "OPENROUTER_API_KEY",
    "TAVILY_API_KEY",
    "LANGSMITH_API_KEY",
    "GDRIVE_CREDENTIALS_JSON",
    "GDRIVE_TOKEN_JSON",
]
# Dikirim sebagai Variable (terlihat publik, jangan isi rahasia).
VARIABLE_KEYS = [
    "EMBEDDING_MODEL",
    "LLM_MODEL_NAME",
    "LANGSMITH_TRACING",
    "LANGSMITH_ENDPOINT",
    "LANGSMITH_PROJECT",
    "CORS_ORIGIN_REGEX",
]


def resolve_token(cli_token: str | None) -> str:
    token = cli_token or os.getenv("HF_DEPLOY_TOKEN") or get_token()
    if not token:
        sys.exit("Token HF tidak ditemukan. Jalankan `.venv/Scripts/hf.exe auth login` (token write) dulu.")
    return token


def build_snapshot(dest: Path) -> None:
    archive = subprocess.run(["git", "archive", "--format=tar", "HEAD"], cwd=ROOT,
                             check=True, capture_output=True).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        members = [m for m in tar.getmembers() if m.name.split("/", 1)[0] not in EXCLUDE_TOP]
        tar.extractall(dest, members=members)
    shutil.copy(HF_DIR / "Dockerfile", dest / "Dockerfile")
    shutil.copy(HF_DIR / "README.md", dest / "README.md")
    (dest / ".dockerignore").write_text(".git\n__pycache__/\n*.pyc\n.env\n", encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--space", default="pertamina-chatbot-backend", help="Nama Space (tanpa username)")
    p.add_argument("--token", default=None)
    p.add_argument("--cors", default=None, help="Nilai CORS_ORIGINS, mis. https://app.vercel.app")
    p.add_argument("--skip-upload", action="store_true", help="Hanya update secrets/variables")
    p.add_argument("--dry-run", action="store_true", help="Buat snapshot lokal saja, tanpa ke HF")
    args = p.parse_args()

    env = dotenv_values(ROOT / ".env")

    with tempfile.TemporaryDirectory(prefix="hf-space-") as tmp:
        snap = Path(tmp)
        if not args.skip_upload:
            build_snapshot(snap)
            files = [f for f in snap.rglob("*") if f.is_file()]
            size = sum(f.stat().st_size for f in files) / 1e6
            print(f"Snapshot: {len(files)} file, {size:.1f} MB")
        if args.dry_run:
            for f in sorted({f.relative_to(snap).parts[0] for f in snap.rglob('*') if f.is_file()}):
                print("  ", f)
            missing = [k for k in ("DATABASE_URL", "OPENROUTER_API_KEY") if not env.get(k)]
            print("Secret wajib yang kosong di .env:", missing or "tidak ada")
            return

        api = HfApi(token=resolve_token(args.token))
        user = api.whoami()["name"]
        repo_id = f"{user}/{args.space}"
        api.create_repo(repo_id, repo_type="space", space_sdk="docker", private=False, exist_ok=True)
        print(f"Space: https://huggingface.co/spaces/{repo_id}")

        # Secrets & variables di-set sebelum upload, karena variable dipakai sebagai build arg.
        for k in SECRET_KEYS:
            if env.get(k):
                api.add_space_secret(repo_id, k, env[k])
                print("  secret  :", k)
        for k in VARIABLE_KEYS:
            if env.get(k):
                api.add_space_variable(repo_id, k, env[k])
                print("  variable:", k, "=", env[k])
        cors = args.cors or env.get("CORS_ORIGINS")
        if cors:
            api.add_space_variable(repo_id, "CORS_ORIGINS", cors)
            print("  variable: CORS_ORIGINS =", cors)

        if not args.skip_upload:
            api.upload_folder(repo_id=repo_id, repo_type="space", folder_path=str(snap),
                              commit_message="Deploy backend dari scripts/deploy_hf_space.py",
                              delete_patterns=["*"])
            print("Upload selesai. Build berjalan di HF (bisa 15-30 menit untuk build pertama).")
        elif cors:
            api.restart_space(repo_id)
            print("Space di-restart agar variabel baru terbaca.")

        sub = f"{user}-{args.space}".lower().replace("_", "-").replace(".", "-")
        print(f"URL API: https://{sub}.hf.space  (health: /api/health)")


if __name__ == "__main__":
    main()
