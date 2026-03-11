import os
from dataclasses import dataclass, field
from pathlib import Path

_ENV_LOADED = False
_ROOT_DIR = Path(__file__).resolve().parents[3]


def _csv_env(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(',') if item.strip()]


def _parse_env_value(raw: str) -> str:
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding='utf-8').splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('#') or '=' not in stripped:
            continue
        key, value = stripped.split('=', 1)
        os.environ.setdefault(key.strip(), _parse_env_value(value))


def load_default_env_file() -> None:
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    env_file = os.getenv('APP_ENV_FILE', '.env').strip() or '.env'
    path = Path(env_file)
    if not path.is_absolute():
        path = _ROOT_DIR / path
    _load_env_file(path)
    _ENV_LOADED = True


@dataclass
class Settings:
    app_name: str = 'Cognitive Agentic Platform'
    app_version: str = '6.0.0'
    environment: str = field(default_factory=lambda: os.getenv('APP_ENVIRONMENT', 'development'))
    log_level: str = field(default_factory=lambda: os.getenv('APP_LOG_LEVEL', 'INFO'))
    loki_url: str = field(default_factory=lambda: os.getenv('APP_LOKI_URL', 'http://localhost:3100'))
    loki_enabled: bool = field(default_factory=lambda: os.getenv('APP_LOKI_ENABLED', 'false').strip().lower() in {'1', 'true', 'yes', 'on'})
    cors_origins: list[str] = field(default_factory=lambda: _csv_env('APP_CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174'))
    auth_required: bool = field(default_factory=lambda: os.getenv('APP_AUTH_REQUIRED', 'false').strip().lower() in {'1', 'true', 'yes', 'on'})
    auth_secret: str = field(default_factory=lambda: os.getenv('APP_AUTH_SECRET', 'change-me-local-rd-secret'))
    auth_access_token_expire_minutes: int = field(default_factory=lambda: int(os.getenv('APP_AUTH_ACCESS_TOKEN_EXPIRE_MINUTES', '720')))
    auth_bootstrap_email: str = field(default_factory=lambda: os.getenv('APP_AUTH_BOOTSTRAP_EMAIL', 'operator@local'))
    auth_bootstrap_password: str = field(default_factory=lambda: os.getenv('APP_AUTH_BOOTSTRAP_PASSWORD', 'operator-demo-pass'))
    auth_bootstrap_role: str = field(default_factory=lambda: os.getenv('APP_AUTH_BOOTSTRAP_ROLE', 'admin'))
    default_model_id: str = field(default_factory=lambda: os.getenv('APP_DEFAULT_MODEL_ID', 'ollama_qwen3'))
    ollama_base_url: str = field(default_factory=lambda: os.getenv('APP_OLLAMA_BASE_URL', 'http://localhost:11434'))
    llamacpp_base_url: str = field(default_factory=lambda: os.getenv('APP_LLAMACPP_BASE_URL', 'http://localhost:8001/v1'))
    llamacpp_api_key: str = field(default_factory=lambda: os.getenv('APP_LLAMACPP_API_KEY', 'local'))
    vllm_base_url: str = field(default_factory=lambda: os.getenv('APP_VLLM_BASE_URL', 'http://localhost:8002/v1'))
    vllm_api_key: str = field(default_factory=lambda: os.getenv('APP_VLLM_API_KEY', 'local'))
    openai_model_name: str = field(default_factory=lambda: os.getenv('APP_OPENAI_MODEL', ''))
    anthropic_model_name: str = field(default_factory=lambda: os.getenv('APP_ANTHROPIC_MODEL', ''))
    transformers_device: str = field(default_factory=lambda: os.getenv('APP_TRANSFORMERS_DEVICE', 'cpu'))
    transformers_max_new_tokens: int = field(default_factory=lambda: int(os.getenv('APP_TRANSFORMERS_MAX_NEW_TOKENS', '192')))
    training_service_url: str = field(default_factory=lambda: os.getenv('APP_TRAINING_SERVICE_URL', 'http://localhost:15000'))
    idle_training_seconds: int = field(default_factory=lambda: int(os.getenv('APP_IDLE_TRAINING_SECONDS', '900')))
    training_backend: str = field(default_factory=lambda: os.getenv('APP_TRAINING_BACKEND', 'unsloth'))
    mock_delay_ms: int = field(default_factory=lambda: int(os.getenv('APP_MOCK_DELAY_MS', '0')))
    auth_store_dir: Path = field(default_factory=lambda: Path(os.getenv('APP_AUTH_STORE_DIR', '/tmp/cognitive_agentic_platform_v6_auth')))
    platform_db_path: Path = field(default_factory=lambda: Path(os.getenv('APP_PLATFORM_DB_PATH', '/tmp/cognitive_agentic_platform_v6_platform/platform.db')))
    auto_fallback_enabled: bool = field(default_factory=lambda: os.getenv('APP_AUTO_FALLBACK_ENABLED', 'true').strip().lower() in {'1', 'true', 'yes', 'on'})
    fallback_model_ids: list[str] = field(default_factory=lambda: _csv_env('APP_FALLBACK_MODEL_IDS', 'transformers_qwen3_0_6b,mock_static'))
    provider_health_cache_seconds: int = field(default_factory=lambda: int(os.getenv('APP_PROVIDER_HEALTH_CACHE_SECONDS', '5')))


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        load_default_env_file()
        _settings = Settings()
    return _settings


def reset_settings_cache() -> None:
    global _ENV_LOADED, _settings
    _ENV_LOADED = False
    _settings = None
