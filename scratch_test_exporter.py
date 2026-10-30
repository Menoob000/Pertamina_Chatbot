"""Quick end-to-end test: DB text → parse_text_to_rks_data → render_to_docx"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import psycopg
from tools.docx_exporter import parse_text_to_rks_data, render_to_docx

CONN = "dbname=langchain user=langchain password=langchain host=localhost"

with psycopg.connect(CONN) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT title, full_content FROM documents ORDER BY title LIMIT 3;")
        rows = cur.fetchall()

for title, content in rows:
    print(f"\n{'='*60}")
    print(f"TITLE: {title}")
    print(f"Content length: {len(content)} chars")
    rks = parse_text_to_rks_data(content, custom_title=title)
    print(f"Parsed BABs: {len(rks['bab'])}")
    print(f"Cover title: {rks['cover_page']['judul_pekerjaan'][:80]}")
    print(f"Company: {rks['cover_page']['nama_perusahaan']}")
    print(f"Doc No: {rks['metadata']['nomor_dokumen']}")
    for b in rks['bab']:
        print(f"  BAB {b['nomor']}: {b['judul']} ({len(b['sub_bab'])} sub-babs)")

    # Render DOCX for first document
    safe = title.replace("/","_").replace(" ","_").replace(".pdf","")[:40]
    out = render_to_docx(rks, f"Test_{safe}.docx")
    print(f"  DOCX: {out}")
    print(f"  Exists: {os.path.exists(out)}")
