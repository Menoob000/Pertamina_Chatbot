import React from 'react'
import {
  ArrowDownToLine, ArrowRight, BookOpenText, Check, Download, FileCheck2,
  FileClock, FileSearch, FileText, Layers3,
} from 'lucide-react'

export default function DocumentPanel({ document, tab, setTab, mode, onConvert, onSearch }) {
  return <section className="viewer-panel" aria-label="Pratinjau dokumen">
    <div className="viewer-heading">
      <div>
        <div className="viewer-heading-icon"><FileText size={19} /></div>
        <div><strong>Pratinjau dokumen</strong><small>Telusuri isi dan detail dokumen</small></div>
      </div>
      <span className="viewer-badge">{mode === 'live' ? 'DOKUMEN ASLI' : 'LIVE PREVIEW'}</span>
    </div>
    {!document ? <div className="viewer-empty">
      <div className="viewer-empty-icon"><FileSearch size={32} /></div>
      <div className="empty-dots"><span /><span /><span /></div>
      <h3>Belum ada dokumen dibuka</h3>
      <p>Minta asisten mencari dokumen RKS. Hasilnya akan muncul di panel ini agar mudah ditinjau.</p>
      <button onClick={onSearch}>Coba cari dokumen <ArrowRight size={16} /></button>
      <div className="viewer-empty-foot"><BookOpenText size={16} /> Preview · Daftar bab · Konversi</div>
    </div> : <>
      <div className="document-info">
        <div className="document-symbol"><FileText size={22} /></div>
        <div><span>DOKUMEN TERBUKA</span><h3>{document.title}</h3><p>{document.filename}</p></div>
      </div>
      <div className="document-tags">
        <span><FileCheck2 size={13} /> {document.number}</span>
        <span className="risk-tag">CSMS: {document.category}</span>
        <span>{document.chapters.length} Bab</span>
      </div>
      <div className="doc-tabs" role="tablist" aria-label="Tampilan dokumen">
        <button role="tab" aria-selected={tab === 'preview'} className={tab === 'preview' ? 'active' : ''} onClick={() => setTab('preview')}><BookOpenText size={16} /> Isi dokumen</button>
        <button role="tab" aria-selected={tab === 'outline'} className={tab === 'outline' ? 'active' : ''} onClick={() => setTab('outline')}><Layers3 size={16} /> Daftar bab</button>
        <button role="tab" aria-selected={tab === 'convert'} className={tab === 'convert' ? 'active' : ''} onClick={() => setTab('convert')}><Download size={16} /> Konversi</button>
      </div>
      <div className="document-body">
        {tab === 'preview' && <div className="paper">
          <div className="paper-header"><div className="paper-brand"><div className="mini-mark"><i /><i /><i /></div> PERTAMINA</div><span>{document.id ? 'DOKUMEN RKS' : 'CONTOH DOKUMEN'}</span></div>
          <div className="paper-rule" />
          <p className="paper-overline">RENCANA KERJA DAN SYARAT-SYARAT</p>
          <h2>{document.title}</h2>
          <div className="paper-meta"><span>Nomor dokumen</span><strong>{document.number}</strong><span>Kategori risiko</span><strong>{document.category}</strong></div>
          <hr />
          {document.content ? <div className="paper-source-text">{document.content}</div> : <>
            <h4>BAB 01 — PENDAHULUAN</h4>
            <p>Dokumen contoh ini memperlihatkan bagaimana isi RKS akan ditampilkan setelah data dari backend tersedia. Bagian ini bukan isi dokumen resmi.</p>
            <h4>1.1 Latar Belakang</h4>
            <p>Pekerjaan overhaul tangki memerlukan persyaratan teknis, administrasi, dan keselamatan yang terdokumentasi secara jelas untuk mendukung proses pengadaan.</p>
          </>}
          {document.pdfUrl && <a className="source-pdf-link" href={document.pdfUrl} target="_blank" rel="noreferrer">Buka PDF sumber <ArrowRight size={14} /></a>}
        </div>}
        {tab === 'outline' && <div className="outline-list">
          <div className="outline-intro">STRUKTUR DOKUMEN <span>{document.chapters.length} BAB</span></div>
          {document.chapters.length ? document.chapters.map((chapter, index) => <div className="outline-chapter" key={`${chapter.no}-${index}`}>
            <div className="outline-number">{chapter.no}</div>
            <div><strong>BAB {chapter.no} — {chapter.title}</strong>{chapter.sections.map((section, sectionIndex) => <p key={`${section}-${sectionIndex}`}>{section}</p>)}</div>
          </div>) : <p className="outline-empty">Daftar bab belum teridentifikasi dari isi dokumen.</p>}
        </div>}
        {tab === 'convert' && <div className="convert-card">
          <div className="convert-icon"><ArrowDownToLine size={24} /></div>
          <h3>PDF ke Word, lebih mudah</h3>
          <p>{mode === 'live' ? 'Konversi PDF sumber menjadi DOCX melalui backend.' : 'Mode demo menunjukkan alur konversi. Proses sebenarnya tersedia setelah backend terhubung.'}</p>
          <div className="convert-file"><FileText size={21} /><div><strong>{document.filename}</strong><small>Dokumen sumber · PDF</small></div><Check size={17} /></div>
          <button className="primary-button" onClick={onConvert} disabled={mode === 'live' && !document.canConvert}><FileCheck2 size={17} /> {document.canConvert === false ? 'PDF sumber tidak tersedia' : 'Lihat alur konversi'}</button>
        </div>}
      </div>
      <div className="viewer-footer"><FileClock size={15} /> {mode === 'live' && document.id ? 'Konten dari backend' : 'Konten demo untuk pratinjau antarmuka'}</div>
    </>}
  </section>
}
