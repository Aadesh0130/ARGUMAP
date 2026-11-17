#!/usr/bin/env python3
"""ARGUMAP NLP Preprocessing CLI Utility.

Reads a raw or normalized debate transcript text file, executes deterministic
speaker extraction, sentence boundary detection, and conservative proposition
segmentation, and serializes the structured result to JSON.

Guarantees:
- component_label remains strictly null/None (no fake classifications).
- Full character offset verification.
- Deterministic IDs and ordering.
"""

import argparse
import json
import sys
from pathlib import Path

# Ensure backend is on sys.path for app.nlp import
PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.nlp import preprocess_transcript


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="ARGUMAP Transcript Preprocessing CLI: Converts raw transcripts into structured argument units."
    )
    parser.add_argument(
        "input_file",
        type=Path,
        help="Path to raw plain text transcript (.txt).",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Optional path to write preprocessed JSON output. Defaults to stdout if omitted.",
    )
    parser.add_argument(
        "--document-id",
        type=str,
        default=None,
        help="Optional unique document identifier. Defaults to deterministic hash.",
    )
    parser.add_argument(
        "--source-corpus",
        type=str,
        default="custom",
        help="Corpus identifier (e.g. qt30, us2016, custom).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.input_file.exists():
        print(f"Error: Input transcript file not found at '{args.input_file}'.", file=sys.stderr)
        return 1

    try:
        with open(args.input_file, "r", encoding="utf-8") as f:
            transcript_text = f.read()
    except Exception as e:
        print(f"Error reading transcript: {e}", file=sys.stderr)
        return 1

    result = preprocess_transcript(
        transcript_text=transcript_text,
        document_id=args.document_id,
        source_corpus=args.source_corpus,
    )

    output_dict = result.model_dump()

    # Format JSON
    json_output = json.dumps(output_dict, indent=2, ensure_ascii=False)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(json_output)
            print(f"Successfully processed transcript -> {args.output}")
            print(f"Speakers: {len(result.speakers)} | Turns: {len(result.turns)} | Units: {len(result.units)}")
            if result.validation.warnings:
                for w in result.validation.warnings:
                    print(f"[Warning] {w}")
        except Exception as e:
            print(f"Error writing output file: {e}", file=sys.stderr)
            return 1
    else:
        print(json_output)

    return 0 if result.validation.is_valid else 1


if __name__ == "__main__":
    sys.exit(main())
