"""Source-kit convenience wrapper; the same demo operation is in the wheel CLI."""

import subprocess
import sys

if __name__ == "__main__":
    subprocess.run([sys.executable, "-m", "crous_queue.cli", "seed-demo"], check=True)
