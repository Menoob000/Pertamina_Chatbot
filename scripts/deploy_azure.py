"""Deploy backend FastAPI ke Azure Container Apps (cocok untuk Azure for Students).

Alur:
  1. Snapshot file ter-commit (git archive HEAD) tanpa Frontend/, output/, tests/ + Dockerfile container.
  2. Buat resource group, Azure Container Registry (Basic), dan Container Apps environment.
  3. Build image: `az acr build` (di cloud, tanpa Docker lokal). Jika ACR Tasks diblokir untuk
     langganan student, otomatis fallback ke `docker build` + `docker push` lokal (Docker Desktop harus jalan).
  4. Buat/update Container App dengan secrets dari .env, ingress publik port 8000.

Prasyarat: `az login` sudah dilakukan dan langganan Azure for Students aktif.

Contoh:
  .venv/Scripts/python.exe scripts/deploy_azure.py
  .venv/Scripts/python.exe scripts/deploy_azure.py --cors https://app.vercel.app --skip-build
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "deploy" / "hf-space" / "Dockerfile"  # Dockerfile non-root, juga dipakai untuk Azure
EXCLUDE_TOP = {"Frontend", "frontend", "output", "tests", ".github", ".vscode"}

# nama env var -> nama secret di Container Apps (huruf kecil, angka, '-')
SECRET_KEYS = ["DATABASE_URL", "OPENROUTER_API_KEY", "TAVILY_API_KEY", "LANGSMITH_API_KEY",
               "GDRIVE_CREDENTIALS_JSON", "GDRIVE_TOKEN_JSON"]
PLAIN_KEYS = ["EMBEDDING_MODEL", "LLM_MODEL_NAME", "LANGSMITH_TRACING", "LANGSMITH_ENDPOINT",
              "LANGSMITH_PROJECT", "CORS_ORIGIN_REGEX", "GDRIVE_FOLDER_ID"]

# az.cmd di "C:\Program Files\..." bermasalah saat dipanggil subprocess (spasi di path),
# jadi panggil Python bawaan Azure CLI langsung, sama seperti isi az.cmd.
_AZ_PY = Path(r"C:\Program Files\Microsoft SDKs\Azure\CLI2\python.exe")
if _AZ_PY.exists():
    AZ_CMD = [str(_AZ_PY), "-IBm", "azure.cli"]
elif shutil.which("az"):
    AZ_CMD = [shutil.which("az")]
else:
    AZ_CMD = []


def az(*args: str, capture: bool = True, check: bool = True) -> str:
    if not AZ_CMD:
        sys.exit("Azure CLI (az) tidak ditemukan. Install: winget install -e --id Microsoft.AzureCLI")
    r = subprocess.run([*AZ_CMD, *args], capture_output=capture, text=True)
    if check and r.returncode != 0:
        sys.exit(f"az {' '.join(args[:3])} gagal:\n{(r.stderr or '')[-2000:]}")
    return (r.stdout or "").strip()


def build_snapshot(dest: Path) -> None:
    archive = subprocess.run(["git", "archive", "--format=tar", "HEAD"], cwd=ROOT,
                             check=True, capture_output=True).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(dest, members=[m for m in tar.getmembers()
                                      if m.name.split("/", 1)[0] not in EXCLUDE_TOP])
    shutil.copy(DOCKERFILE, dest / "Dockerfile")
    (dest / ".dockerignore").write_text(".git\n__pycache__/\n*.pyc\n.env\n", encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--rg", default="pertamina-chatbot-rg")
    p.add_argument("--location", default="indonesiacentral")  # langganan student hanya boleh region tertentu
    # ACR Tasks (az acr build) tidak tersedia di indonesiacentral, jadi registry diletakkan di eastasia
    # (juga termasuk region yang diizinkan langganan student). Container App tetap di --location.
    p.add_argument("--acr-location", default="eastasia")
    p.add_argument("--app", default="pertamina-backend")
    p.add_argument("--env-name", default="pertamina-env")
    p.add_argument("--cors", default=None, help="Nilai CORS_ORIGINS, mis. https://app.vercel.app")
    p.add_argument("--skip-build", action="store_true", help="Pakai image yang sudah ada, hanya update app")
    p.add_argument("--local-build", action="store_true", help="Langsung pakai docker lokal, tanpa az acr build")
    p.add_argument("--image", default=None,
                   help="Image publik siap pakai (mis. ghcr.io/flax3-ops/pertamina-backend:latest dari GitHub Actions). "
                        "Jika diisi: tanpa ACR, tanpa build.")
    args = p.parse_args()

    env = dotenv_values(ROOT / ".env")
    sub = json.loads(az("account", "show", "-o", "json"))
    print(f"Langganan: {sub['name']} ({sub['id']})")

    # Nama ACR harus unik global: turunkan dari subscription id agar stabil.
    acr = "pertaminacb" + hashlib.sha1(sub["id"].encode()).hexdigest()[:8]
    external = bool(args.image)
    image = args.image or f"{acr}.azurecr.io/pertamina-backend:latest"

    for ns in ("Microsoft.App", "Microsoft.OperationalInsights", "Microsoft.ContainerRegistry"):
        az("provider", "register", "-n", ns, "--wait")
    az("extension", "add", "--name", "containerapp", "--upgrade", "--only-show-errors")

    print("Resource group & registry ...")
    az("group", "create", "-n", args.rg, "-l", args.location, "-o", "none")
    if not external and az("acr", "show", "-n", acr, "-g", args.rg, "--query", "name", "-o", "tsv", check=False) != acr:
        az("acr", "create", "-n", acr, "-g", args.rg, "-l", args.acr_location,
           "--sku", "Basic", "--admin-enabled", "true", "-o", "none")

    if not args.skip_build and not external:
        with tempfile.TemporaryDirectory(prefix="aca-build-") as tmp:
            build_snapshot(Path(tmp))
            emb = env.get("EMBEDDING_MODEL") or "sentence-transformers/all-minilm-l6-v2"
            ok = False
            if not args.local_build:
                print("Build image di Azure (az acr build), bisa 15-30 menit ...")
                r = subprocess.run([*AZ_CMD, "acr", "build", "-r", acr, "-t", "pertamina-backend:latest",
                                    "--build-arg", f"EMBEDDING_MODEL={emb}", tmp])
                ok = r.returncode == 0
                if not ok:
                    print("az acr build gagal (ACR Tasks mungkin diblokir untuk langganan ini). Fallback ke docker lokal.")
            if not ok:
                try:
                    docker_ok = subprocess.run(["docker", "info"], capture_output=True, timeout=30).returncode == 0
                except subprocess.TimeoutExpired:
                    docker_ok = False
                if not docker_ok:
                    sys.exit("Docker daemon tidak jalan. Buka Docker Desktop lalu ulangi dengan --local-build.")
                az("acr", "login", "-n", acr)
                subprocess.run(["docker", "build", "--build-arg", f"EMBEDDING_MODEL={emb}",
                                "-t", image, tmp], check=True)
                subprocess.run(["docker", "push", image], check=True)

    registry_args: list[str] = []
    secrets, env_vars = [], ["FASTAPI_HOST=0.0.0.0", "FASTAPI_PORT=8000"]
    if not external:
        creds = json.loads(az("acr", "credential", "show", "-n", acr, "-o", "json"))
        reg_user, reg_pass = creds["username"], creds["passwords"][0]["value"]
        registry_args = ["--registry-server", f"{acr}.azurecr.io",
                         "--registry-username", reg_user, "--registry-password", reg_pass]
    for k in SECRET_KEYS:
        if env.get(k):
            name = k.lower().replace("_", "-")
            secrets.append(f"{name}={env[k]}")
            env_vars.append(f"{k}=secretref:{name}")
    for k in PLAIN_KEYS:
        if env.get(k):
            env_vars.append(f"{k}={env[k]}")
    cors = args.cors or env.get("CORS_ORIGINS")
    if cors:
        env_vars.append(f"CORS_ORIGINS={cors}")

    if az("containerapp", "env", "show", "-n", args.env_name, "-g", args.rg, "--query", "name", "-o", "tsv",
          check=False) != args.env_name:
        print("Container Apps environment (beberapa menit) ...")
        az("containerapp", "env", "create", "-n", args.env_name, "-g", args.rg, "-l", args.location, "-o", "none")

    exists = az("containerapp", "show", "-n", args.app, "-g", args.rg, "--query", "name", "-o", "tsv",
                check=False) == args.app
    if not exists:
        print("Membuat Container App ...")
        az("containerapp", "create", "-n", args.app, "-g", args.rg, "--environment", args.env_name,
           "--image", image, *registry_args,
           "--target-port", "8000", "--ingress", "external",
           "--cpu", "1", "--memory", "2Gi", "--min-replicas", "0", "--max-replicas", "1",
           "--secrets", *secrets, "--env-vars", *env_vars, "-o", "none")
    else:
        print("Update Container App ...")
        az("containerapp", "secret", "set", "-n", args.app, "-g", args.rg, "--secrets", *secrets, "-o", "none")
        az("containerapp", "update", "-n", args.app, "-g", args.rg, "--image", image,
           "--set-env-vars", *env_vars, "-o", "none")

    fqdn = az("containerapp", "show", "-n", args.app, "-g", args.rg,
              "--query", "properties.configuration.ingress.fqdn", "-o", "tsv")
    print(f"\nURL API : https://{fqdn}")
    print(f"Health  : https://{fqdn}/api/health  (start pertama bisa 1-3 menit karena memuat model)")


if __name__ == "__main__":
    main()
