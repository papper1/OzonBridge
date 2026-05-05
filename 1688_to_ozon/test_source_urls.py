import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from main import detect_input_mode, run_pipeline
from main import detect_source


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python test_source_urls.py <product_or_source_url> [max_links]")
        raise SystemExit(1)

    source_value = sys.argv[1].strip()
    max_links = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    detected_source = detect_source(source_value, "")
    print(f"Detected source: {detected_source}")
    output_path = run_pipeline(
        keyword=source_value,
        max_links=max_links,
        source_mode=detect_input_mode(source_value),
    )
    print(output_path or "No export generated")


if __name__ == "__main__":
    main()
