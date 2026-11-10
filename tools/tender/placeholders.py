"""Visible markers for procurement facts absent from a tender draft."""

NOMOR_TENDER = "[Nomor tender belum diisi]"
TANGGAL_DOKUMEN = "[Tanggal dokumen belum diisi]"
METODE_PEMENUHAN = "[Metode pemenuhan belum diisi]"
JENIS_KONTRAK = "[Jenis kontrak belum diisi]"
HPS_PRIME_COST = "[HPS Prime Cost belum diisi]"
HPS_TOTAL = "[Total HPS belum diisi]"
RISIKO_CSMS = "[Risiko CSMS belum diisi]"


def text_or_placeholder(value, placeholder: str) -> str:
    return str(value).strip() if value is not None and str(value).strip() else placeholder


def amount_or_placeholder(value, placeholder: str, formatter) -> str:
    """Zero in the form denotes missing data, not an approved Rp0 amount."""
    return formatter(value) if value is not None and float(value) > 0 else placeholder
