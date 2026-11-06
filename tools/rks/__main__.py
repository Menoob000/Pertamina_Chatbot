"""Usage: python -m tools.rks 'buatkan rks overhaul tangki 041T314'."""
import argparse
import json

from .service import create_document

parser = argparse.ArgumentParser(description="Buat RKS tertata beserta preview dari sumber knowledge base.")
parser.add_argument("query")
parser.add_argument("--source-id", default="")
parser.add_argument("--no-preview", action="store_true")
args = parser.parse_args()
print(json.dumps(create_document(args.query, args.source_id, render_preview=not args.no_preview),
                 ensure_ascii=True, indent=2))
