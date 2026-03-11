from app.providers.mock import MockProvider


def test_mock_provider_generate_and_stream():
    provider = MockProvider()

    generated = provider.generate('mock-static', 'Goal: say hello\nStep: summarize\nNotes: tool=reasoning')
    streamed = ''.join(provider.stream('mock-static', 'Goal: say hello\nStep: summarize\nNotes: tool=reasoning')).strip()

    assert generated.provider == 'mock'
    assert 'Completed summarize' in generated.text
    assert streamed.startswith('[mock:mock-static]')
