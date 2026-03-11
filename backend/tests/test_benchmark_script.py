import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_benchmark_script_runs_mock_preset():
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / 'scripts' / 'run_benchmark.py'),
            '--env-file',
            '.env.mock.minimal',
            '--suite',
            'speed',
            '--json',
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload
    assert payload[0]['preset'] == 'mock.minimal'
    assert payload[0]['provider'] == 'mock'
