import React from 'react'
import { CircleHelp, Download, FileCheck2, FileText, X } from 'lucide-react'
import { api } from './api.js'

export default function ConversionDialog({ document, mode, result, converting, onClose, onConvert }) {
  const downloadUrl = result ? api.downloadUrl(result.download_url) : null
  return <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}>
    <div className="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title">
      <button className="modal-close icon-button" aria-label="Tutup dialog" onClick={onClose}><X size={19} /></button>
      <div className="modal-icon"><FileCheck2 size={25} /></div>
      <h2 id="modal-title">Konversi PDF ke DOCX</h2>
      <p>{mode === 'live' ? 'Konversi PDF sumber melalui layanan backend.' : 'Alur ini siap digunakan setelah backend terhubung.'}</p>
      <label>File sumber<div className="modal-source"><FileText size={18} /> {document?.filename || 'Belum ada dokumen'}</div></label>
      <label>Nama file keluaran<input value={result?.filename || document?.filename?.replace(/\.pdf$/i, '.docx') || ''} readOnly /></label>
      {mode !== 'live' && <div className="modal-note"><CircleHelp size={17} /> Mode demo belum menghasilkan file. Hubungkan backend untuk konversi asli.</div>}
      {mode === 'live' && !document?.canConvert && <div className="modal-note"><CircleHelp size={17} /> PDF sumber tidak ditemukan di folder data.</div>}
      <div className="modal-actions">
        <button className="outline-button" onClick={onClose}>Tutup</button>
        {downloadUrl ? <a className="primary-button" href={downloadUrl}><Download size={16} /> Unduh DOCX</a> : <button className="primary-button" onClick={onConvert} disabled={mode !== 'live' || !document?.canConvert || converting}><Download size={16} /> {converting ? 'Mengonversi...' : 'Konversi ke DOCX'}</button>}
      </div>
    </div>
  </div>
}
