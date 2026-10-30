from pathlib import Path
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TERRA_", env_file=str(ROOT / ".env"), extra="ignore"
    )
    database_url: str = f"sqlite:///{ROOT / 'runtime/app.db'}"
    storage_dir: Path = ROOT / "runtime/assets"
    demo_dir: Path = ROOT / "data/demo"
    library_dir: Path = ROOT / "data/library"
    font_path: Path = ROOT / "data/fonts/NotoSansSC.ttf"
    redis_url: str = "redis://redis:6379/0"
    worker_mode: str = "local"
    secure_cookies: bool = False
    allowed_hosts: str = "localhost,127.0.0.1,testserver,api"
    session_hours: int = 12
    max_upload_bytes: int = 20 * 1024 * 1024
    max_pixels: int = 25_000_000
    model_service_url: str = ""
    model_service_token: str = ""
    model_transport: Literal["https", "ssh_tunnel"] = "https"
    model_timeout_seconds: int = 1800
    admin_username: str = "admin"
    admin_password: str = ""


settings = Settings()
