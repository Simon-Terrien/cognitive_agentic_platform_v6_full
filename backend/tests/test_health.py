from app.api.routes import health


def test_health():
    payload = health.health()
    assert payload['ok'] is True
