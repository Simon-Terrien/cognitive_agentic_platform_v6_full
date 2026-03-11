from pathlib import Path

from app.core import config


def test_settings_can_load_from_app_env_file(monkeypatch, tmp_path: Path):
    env_file = tmp_path / 'preset.env'
    env_file.write_text(
        '\n'.join(
            [
                'APP_DEFAULT_MODEL_ID=mock_static',
                'APP_TRANSFORMERS_MAX_NEW_TOKENS=64',
                'APP_MOCK_DELAY_MS=7',
            ]
        ),
        encoding='utf-8',
    )

    monkeypatch.delenv('APP_DEFAULT_MODEL_ID', raising=False)
    monkeypatch.delenv('APP_TRANSFORMERS_MAX_NEW_TOKENS', raising=False)
    monkeypatch.delenv('APP_MOCK_DELAY_MS', raising=False)
    monkeypatch.setenv('APP_ENV_FILE', str(env_file))
    config.reset_settings_cache()

    settings = config.get_settings()

    assert settings.default_model_id == 'mock_static'
    assert settings.transformers_max_new_tokens == 64
    assert settings.mock_delay_ms == 7

    config.reset_settings_cache()
