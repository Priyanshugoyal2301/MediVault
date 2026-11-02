"""Run the local application against the isolated development PostgreSQL container.

Start DB first using docs/LOCAL_APPLICATION.md. Ctrl+C stops all owned services.
Secrets persist only in gitignored .env.local; existing .env is never modified.
"""
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    local = ROOT / ".env.local"
    from dotenv import dotenv_values
    if not local.exists():
        local.write_text("\n".join([
            "POSTGRES_HOST=127.0.0.1", "POSTGRES_PORT=54329", "POSTGRES_DB=medivault",
            "POSTGRES_USER=medivault_user", "POSTGRES_PASSWORD=local-development-only",
            "AUTH_SECRET_KEY=" + secrets.token_urlsafe(48),
            "INTERNAL_SERVICE_KEY=" + secrets.token_urlsafe(48), "COOKIE_SECURE=false",
            "FILE_ENCRYPTION_KEY=" + __import__("base64").urlsafe_b64encode(secrets.token_bytes(32)).decode(),
            "AUTH_SERVICE_URL=http://127.0.0.1:8001", "HEALTH_SERVICE_URL=http://127.0.0.1:8002",
            "AI_SERVICE_URL=http://127.0.0.1:8003", "CORS_ORIGINS=http://127.0.0.1:3000,http://localhost:3000",
            "STORAGE_LOCAL_PATH=./data/local-uploads",
        ]) + "\n", encoding="utf-8")
    env = {**os.environ, **{k:v for k,v in dotenv_values(local).items() if v is not None}}
    if not env.get("FILE_ENCRYPTION_KEY"):
        import base64
        env["FILE_ENCRYPTION_KEY"] = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
        with local.open("a", encoding="utf-8") as stream:
            stream.write("FILE_ENCRYPTION_KEY=" + env["FILE_ENCRYPTION_KEY"] + "\n")
    tesseract = shutil.which("tesseract")
    windows_tesseract = Path("C:/Program Files/Tesseract-OCR/tesseract.exe")
    if not tesseract and windows_tesseract.exists():
        tesseract = str(windows_tesseract)
    if tesseract:
        env["TESSERACT_CMD"] = tesseract
    # Local run is deterministic and does not call optional external AI backends.
    for flag in ("USE_UNLIMITED_OCR", "USE_ML_NORMALIZER", "USE_EMBEDDING_SEARCH", "USE_RISK_MODEL", "USE_HEALTH_SCORE_MODEL", "USE_OUTLIER_MODEL", "USE_IMAGE_QUALITY_MODEL"):
        env[flag] = "false"
    import psycopg2
    print("Waiting for the local database…", flush=True)
    for attempt in range(30):
        try:
            connection = psycopg2.connect(host=env["POSTGRES_HOST"], port=env["POSTGRES_PORT"],
                dbname=env["POSTGRES_DB"], user=env["POSTGRES_USER"], password=env["POSTGRES_PASSWORD"], connect_timeout=2)
            connection.close()
            break
        except psycopg2.OperationalError:
            if attempt == 29:
                raise SystemExit("Database unavailable. Start medivault-care-dev, then retry.") from None
            time.sleep(1)
    subprocess.run([sys.executable, "-m", "alembic", "-c", "infra/migrations/alembic.ini", "upgrade", "head"], cwd=ROOT, env=env, check=True)
    processes, logs = [], []
    log_dir = ROOT / ".local-logs"
    log_dir.mkdir(exist_ok=True)
    commands = [(name,[sys.executable,"scripts/run_service.py",module,str(port)]) for name,module,port in [
        ("auth","services.auth_service.main:app",8001), ("health","services.health_service.main:app",8002),
        ("ai","services.ai_service.main:app",8003), ("gateway","apps.api.main:app",8000)]]
    node = shutil.which("node")
    if not node:
        raise SystemExit("Install Node.js before starting the web application")
    commands.append(("web",[node,"apps/web/node_modules/vite/bin/vite.js","apps/web","--host","127.0.0.1","--port","3000","--strictPort"]))
    try:
        for name, command in commands:
            stream = (log_dir / f"{name}.log").open("w", encoding="utf-8")
            logs.append(stream)
            processes.append(subprocess.Popen(command,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT))
        print("MediVault: http://127.0.0.1:3000 · logs in .local-logs · Ctrl+C to stop", flush=True)
        while all(p.poll() is None for p in processes):
            time.sleep(1)
        raise SystemExit("A service exited. Inspect .local-logs for details.")
    except KeyboardInterrupt:
        pass
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
        for stream in logs:
            stream.close()


if __name__ == "__main__":
    main()
