import React, { useEffect, useRef, useState } from 'react'
import {
  Activity, ArrowDownToLine, ArrowRight, BookOpenText, Check, ChevronDown,
  ChevronLeft, ChevronRight, CircleHelp, Clock3, Copy, Download, FileCheck2,
  FileClock, FileSearch, FileText, FolderOpen, History, Layers3, Menu,
  MessageCircle, MoreHorizontal, PanelRightClose, PanelRightOpen, Plus,
  Search, Send, Settings2, ShieldCheck, Sparkles, Trash2, X,
} from 'lucide-react'

const STORAGE_KEY = 'pertamina-react-template-v1'
const INITIAL_THREAD = { id: 'welcome', title: 'Percakapan baru', messages: [], tools: [], document: null, createdAt: Date.now() }

const demoDocument = {
  title: 'RKS Pekerjaan Overhaul Tangki 041T314',
  filename: 'RKS-041T314-PEKERJAAN OVERHAUL TANGKI.pdf',
  number: 'RKS/PN/041T314/2026',
  category: 'HIGH',
  chapters: [
    { no: '01', title: 'Pendahuluan', sections: ['Latar belakang', 'Maksud dan tujuan', 'Lokasi pekerjaan'] },
    { no: '02', title: 'Ruang Lingkup Pekerjaan', sections: ['Persiapan pekerjaan', 'Pekerjaan mekanikal', 'Inspeksi dan pengujian'] },
    { no: '03', title: 'Persyaratan Teknis', sections: ['Standar material', 'Metode pelaksanaan', 'Pengendalian mutu'] },
    { no: '04', title: 'Keselamatan Kerja', sections: ['Persyaratan CSMS', 'Izin kerja', 'Pengendalian risiko'] },
  ],
}

const quickActions = [
  { icon: FolderOpen, color: 'blue', title: 'Cari dokumen RKS', description: 'Temukan template RKS yang relevan', prompt: 'Tolong ambilkan dokumen full RKS untuk overhaul tangki' },
  { icon: ShieldCheck, color: 'green', title: 'Periksa CSMS', description: 'Tanya persyaratan keselamatan', prompt: 'Apa saja persyaratan aspek CSMS untuk kategori High?' },
  { icon: FileCheck2, color: 'orange', title: 'Konversi dokumen', description: 'Ubah PDF menjadi file Word', prompt: 'Convert dokumen PDF RKS terakhir ke docx format' },
]

function createThread() {
  return { id: crypto.randomUUID(), title: 'Percakapan baru', messages: [], tools: [], document: null, createdAt: Date.now() }
}

function createDemoResponse(prompt, hasDocument) {
  const value = prompt.toLowerCase()
  if (/convert|konversi|docx|word/.test(value)) {
    return hasDocument
      ? { text: 'Dokumen sudah siap ditinjau. Alur konversi PDF ke DOCX tersedia di panel dokumen; proses sebenarnya akan aktif setelah endpoint backend dihubungkan.', tool: 'convert_pdf_to_docx', document: demoDocument }
      : { text: 'Untuk mengonversi PDF, ambil dokumen RKS terlebih dahulu. Setelah dokumen tampil di panel kanan, buka tab Konversi untuk melihat alurnya.', tool: null, document: null }
  }
  if (/csms|keselamatan|risiko/.test(value)) {
    return { text: 'Untuk pekerjaan berkategori risiko HIGH, dokumen RKS biasanya memuat persyaratan CSMS, izin kerja, identifikasi bahaya, dan langkah pengendalian risiko. Ini hanya contoh tampilan jawaban. Persyaratan yang berlaku perlu diambil dari dokumen sumber melalui backend.', tool: 'fetch_relevant_documents', document: demoDocument }
  }
  if (/rks|dokumen|tangki|pdf/.test(value)) {
    return { text: 'Saya menemukan contoh dokumen RKS Pekerjaan Overhaul Tangki 041T314. Ringkasan dan susunan bab dapat dilihat pada panel dokumen di sebelah kanan. Dokumen ini adalah data demo untuk pratinjau antarmuka.', tool: 'fetch_full_documents', document: demoDocument }
  }
  return { text: 'Ini adalah respons demo dari template React. Saat API backend terhubung, pesan Anda akan diproses oleh agent Pertamina dan hasilnya akan tampil di sini.', tool: null, document: null }
}

function loadState() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY))
    if (Array.isArray(saved?.threads) && saved.threads.length) {
      return { threads: saved.threads, activeId: saved.threads.some((t) => t.id === saved.activeId) ? saved.activeId : saved.threads[0].id }
    }
  } catch { /* Invalid local demo data: start fresh. */ }
  return { threads: [INITIAL_THREAD], activeId: INITIAL_THREAD.id }
}

function Brand() {
  return <div className="brand"><div className="brand-mark" aria-hidden="true"><i /><i /><i /></div><div><strong>PERTAMINA</strong><span>PATRA NIAGA</span></div></div>
}

function App() {
  const [session, setSession] = useState(loadState)
  const [prompt, setPrompt] = useState('')
  const [search, setSearch] = useState('')
  const [viewerOpen, setViewerOpen] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [docTab, setDocTab] = useState('preview')
  const [convertOpen, setConvertOpen] = useState(false)
  const [notice, setNotice] = useState('')
  const [menuOpen, setMenuOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const bottomRef = useRef(null)
  const active = session.threads.find((thread) => thread.id === session.activeId) || session.threads[0]
  const filteredThreads = session.threads.filter((thread) => thread.title.toLowerCase().includes(search.toLowerCase()))

  useEffect(() => { localStorage.setItem(STORAGE_KEY, JSON.stringify(session)) }, [session])
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [active?.messages.length, busy])
  useEffect(() => { if (notice) { const timer = setTimeout(() => setNotice(''), 4000); return () => clearTimeout(timer) } }, [notice])
  useEffect(() => {
    function closeOnEscape(event) {
      if (event.key !== 'Escape') return
      if (convertOpen) setConvertOpen(false)
      else if (viewerOpen) setViewerOpen(false)
    }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [convertOpen, viewerOpen])

  function updateThread(id, updater) {
    setSession((previous) => ({ ...previous, threads: previous.threads.map((thread) => thread.id === id ? updater(thread) : thread) }))
  }

  function startNewChat() {
    const thread = createThread()
    setSession((previous) => ({ threads: [thread, ...previous.threads], activeId: thread.id }))
    setPrompt('')
    setDocTab('preview')
    setSidebarOpen(false)
  }

  function submitMessage(value = prompt) {
    const text = value.trim()
    if (!text || busy) return
    const threadId = active.id
    const hadDocument = Boolean(active.document)
    setPrompt('')
    setBusy(true)
    updateThread(threadId, (thread) => ({ ...thread,
      title: thread.messages.length ? thread.title : text.slice(0, 27) + (text.length > 27 ? '…' : ''),
      messages: [...thread.messages, { id: crypto.randomUUID(), role: 'user', text, at: Date.now() }],
    }))
    setTimeout(() => {
      const answer = createDemoResponse(text, hadDocument)
      updateThread(threadId, (thread) => ({ ...thread,
        document: answer.document || thread.document,
        messages: [...thread.messages, { id: crypto.randomUUID(), role: 'assistant', text: answer.text, at: Date.now(), tool: answer.tool }],
        tools: answer.tool ? [{ name: answer.tool, at: Date.now(), status: 'Demo' }, ...thread.tools] : thread.tools,
      }))
      setBusy(false)
    }, 650)
  }

  function deleteThread() {
    setSession((previous) => {
      const remaining = previous.threads.filter((thread) => thread.id !== previous.activeId)
      if (remaining.length) return { threads: remaining, activeId: remaining[0].id }
      const fresh = createThread()
      return { threads: [fresh], activeId: fresh.id }
    })
    setMenuOpen(false)
    setSidebarOpen(false)
  }

  function renameThread() {
    const title = window.prompt('Nama percakapan', active.title)?.trim()
    if (title) updateThread(active.id, (thread) => ({ ...thread, title }))
    setMenuOpen(false)
  }

  function copyResponse(text) {
    navigator.clipboard?.writeText(text).then(() => setNotice('Jawaban disalin ke clipboard')).catch(() => setNotice('Clipboard tidak tersedia di browser ini'))
  }

  return <div className="app-shell">
    {sidebarOpen && <button className="mobile-backdrop" aria-label="Tutup menu" onClick={() => setSidebarOpen(false)} />}
    <aside className={`sidebar ${sidebarOpen ? 'sidebar-open' : ''}`}>
      <div className="sidebar-top"><Brand /><button className="sidebar-close icon-button" aria-label="Tutup menu" onClick={() => setSidebarOpen(false)}><X size={18} /></button></div>
      <div className="workspace-label">WORKSPACE <ChevronDown size={13} /></div>
      <div className="workspace-card"><div className="workspace-avatar">P</div><div><strong>Procurement Hub</strong><small>Document intelligence</small></div><ChevronDown size={15} /></div>
      <button className="new-chat" onClick={startNewChat}><Plus size={18} /> Percakapan baru <span>+</span></button>
      <div className="sidebar-section"><span>MENU UTAMA</span></div>
      <button className="nav-item selected"><MessageCircle size={18} /> Asisten AI <span className="nav-dot" /></button>
      <button className="nav-item" onClick={() => { setViewerOpen(true); setSidebarOpen(false); setNotice('Cari dokumen melalui kolom chat untuk menampilkan contoh RKS') }}><FolderOpen size={18} /> Dokumen RKS <ChevronRight size={15} /></button>
      <button className="nav-item" onClick={() => { setViewerOpen(true); setDocTab('convert'); setSidebarOpen(false) }}><Layers3 size={18} /> Konversi PDF <ChevronRight size={15} /></button>
      <div className="history-heading"><span>RIWAYAT PERCAKAPAN</span><History size={15} /></div>
      <label className="history-search"><Search size={15} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Cari percakapan..." aria-label="Cari percakapan" /></label>
      <div className="history-list">{filteredThreads.length ? filteredThreads.map((thread) => <button key={thread.id} className={`history-item ${thread.id === active.id ? 'active' : ''}`} onClick={() => { setSession((previous) => ({ ...previous, activeId: thread.id })); setSidebarOpen(false); setDocTab('preview') }}><MessageCircle size={16} /><span>{thread.title}</span>{thread.id === active.id && <span className="history-active-dot" />}</button>) : <p className="history-empty">Tidak ada percakapan</p>}</div>
      <div className="sidebar-bottom"><div className="demo-status"><span className="pulse-dot" /> MODE PRATINJAU <small>Data demo lokal</small></div><div className="profile"><div className="profile-avatar">PN</div><div><strong>Tim Pengadaan</strong><small>Pertamina Patra Niaga</small></div><Settings2 size={17} /></div></div>
    </aside>

    <div className="main-area">
      <header className="topbar"><div className="topbar-left"><button className="mobile-menu icon-button" aria-label="Buka menu" onClick={() => setSidebarOpen(true)}><Menu size={20} /></button><div className="breadcrumb">Workspace <ChevronRight size={15} /> <span>Asisten AI</span></div></div><div className="topbar-right"><span className="preview-pill"><span /> Preview template</span><button className="help-button" onClick={() => setNotice('Template ini belum terhubung ke API backend. Semua respons menggunakan data demo.')}><CircleHelp size={18} /> <span>Bantuan</span></button></div></header>
      <div className="content-top"><div><div className="eyebrow"><span /> INTELLIGENT DOCUMENT WORKSPACE</div><h1>Asisten Dokumen <span>Pertamina</span></h1><p>Temukan informasi pengadaan, tinjau dokumen RKS, dan siapkan konversi dalam satu ruang kerja.</p></div><div className="content-actions"><button className="outline-button" onClick={() => setViewerOpen(!viewerOpen)}>{viewerOpen ? <PanelRightClose size={17} /> : <PanelRightOpen size={17} />}{viewerOpen ? 'Sembunyikan viewer' : 'Tampilkan viewer'}</button><button className="primary-button" onClick={() => { setViewerOpen(true); setDocTab('convert'); if (active.document) setConvertOpen(true); else setNotice('Ambil contoh dokumen RKS dahulu melalui chat') }}><FileCheck2 size={17} /> Konversi PDF</button></div></div>

      <div className={`work-grid ${viewerOpen ? '' : 'full-chat'}`}>
        <section className="chat-panel" aria-label="Percakapan"><div className="panel-heading"><div className="panel-heading-icon"><MessageCircle size={19} /></div><div><strong>{active.title}</strong><small>Asisten pengadaan berbasis dokumen</small></div><div className="panel-menu"><button className="icon-button more-button" aria-label="Opsi percakapan" onClick={() => setMenuOpen(!menuOpen)}><MoreHorizontal size={20} /></button>{menuOpen && <div className="dropdown"><button onClick={renameThread}><FileText size={15} /> Ubah nama</button><button onClick={deleteThread}><Trash2 size={15} /> Hapus percakapan</button></div>}</div></div>
          <div className="chat-scroll">{active.messages.length === 0 ? <div className="empty-chat"><div className="assistant-orbit"><div className="orbit-inner"><Sparkles size={27} /></div></div><div className="welcome-kicker">SELAMAT DATANG</div><h2>Halo, ada yang bisa<br /><em>saya bantu?</em></h2><p>Tanyakan seputar dokumen RKS, persyaratan CSMS, atau alur konversi PDF ke Word.</p><div className="quick-actions">{quickActions.map(({ icon: Icon, color, title, description, prompt: suggestion }) => <button key={title} className="quick-card" onClick={() => submitMessage(suggestion)}><span className={`quick-icon ${color}`}><Icon size={20} /></span><strong>{title}</strong><small>{description}</small><ArrowRight className="quick-arrow" size={17} /></button>)}</div><div className="sample-label">ATAU COBA TANYAKAN</div><button className="suggestion" onClick={() => submitMessage('Apa isi utama RKS overhaul tangki?')}>“Apa isi utama RKS overhaul tangki?” <ArrowRight size={15} /></button></div> : <div className="messages">{active.messages.map((message) => <div key={message.id} className={`message-row ${message.role}`}><div className="message-avatar">{message.role === 'assistant' ? <Sparkles size={17} /> : 'PN'}</div><div className="message-body"><div className="message-meta"><strong>{message.role === 'assistant' ? 'Asisten Pertamina' : 'Anda'}</strong><time>{new Date(message.at).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' })}</time></div>{message.tool && <div className="tool-chip"><Activity size={13} /> {message.tool} <span>DEMO</span></div>}<p>{message.text}</p>{message.role === 'assistant' && <button className="copy-button" onClick={() => copyResponse(message.text)}><Copy size={14} /> Salin jawaban</button>}</div></div>)}{busy && <div className="message-row assistant"><div className="message-avatar"><Sparkles size={17} /></div><div className="thinking"><span /><span /><span /></div></div>}<div ref={bottomRef} /></div>}</div>
          <form className="composer-wrap" onSubmit={(event) => { event.preventDefault(); submitMessage() }}><div className="composer"><textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); submitMessage() } }} placeholder="Tanyakan tentang dokumen RKS atau proses pengadaan..." rows={2} aria-label="Pesan untuk asisten" /><div className="composer-bottom"><span><Sparkles size={14} /> Asisten dokumen pengadaan</span><button type="submit" disabled={!prompt.trim() || busy} aria-label="Kirim pesan"><Send size={18} /></button></div></div><p>Respons pada template ini adalah simulasi. Verifikasi informasi dengan dokumen resmi.</p></form>
        </section>

        {viewerOpen && <>
          <button className="viewer-backdrop" type="button" aria-label="Tutup pratinjau dokumen" onClick={() => setViewerOpen(false)} />
          <button className="viewer-close-button" type="button" aria-label="Tutup pratinjau dokumen" title="Tutup pratinjau" onClick={() => setViewerOpen(false)}><X size={19} /></button>
        </>}
        {viewerOpen && <section className="viewer-panel" aria-label="Pratinjau dokumen"><div className="viewer-heading"><div><div className="viewer-heading-icon"><FileText size={19} /></div><div><strong>Pratinjau dokumen</strong><small>Telusuri isi dan detail dokumen</small></div></div><span className="viewer-badge">LIVE PREVIEW</span></div>{active.document ? <><div className="document-info"><div className="document-symbol"><FileText size={22} /></div><div><span>DOKUMEN TERBUKA</span><h3>{active.document.title}</h3><p>{active.document.filename}</p></div></div><div className="document-tags"><span><FileCheck2 size={13} /> {active.document.number}</span><span className="risk-tag">CSMS: {active.document.category}</span><span>{active.document.chapters.length} Bab</span></div><div className="doc-tabs" role="tablist" aria-label="Tampilan dokumen"><button role="tab" aria-selected={docTab === 'preview'} className={docTab === 'preview' ? 'active' : ''} onClick={() => setDocTab('preview')}><BookOpenText size={16} /> Isi dokumen</button><button role="tab" aria-selected={docTab === 'outline'} className={docTab === 'outline' ? 'active' : ''} onClick={() => setDocTab('outline')}><Layers3 size={16} /> Daftar bab</button><button role="tab" aria-selected={docTab === 'convert'} className={docTab === 'convert' ? 'active' : ''} onClick={() => setDocTab('convert')}><Download size={16} /> Konversi</button></div><div className="document-body">{docTab === 'preview' && <div className="paper"><div className="paper-header"><div className="paper-brand"><div className="mini-mark"><i /><i /><i /></div> PERTAMINA</div><span>CONTOH DOKUMEN</span></div><div className="paper-rule" /><p className="paper-overline">RENCANA KERJA DAN SYARAT-SYARAT</p><h2>{active.document.title}</h2><div className="paper-meta"><span>Nomor dokumen</span><strong>{active.document.number}</strong><span>Kategori risiko</span><strong>{active.document.category}</strong></div><hr /><h4>BAB 01 — PENDAHULUAN</h4><p>Dokumen contoh ini memperlihatkan bagaimana isi RKS akan ditampilkan setelah data dari backend tersedia. Bagian ini bukan isi dokumen resmi.</p><h4>1.1 Latar Belakang</h4><p>Pekerjaan overhaul tangki memerlukan persyaratan teknis, administrasi, dan keselamatan yang terdokumentasi secara jelas untuk mendukung proses pengadaan.</p><h4>1.2 Maksud dan Tujuan</h4><p>Menetapkan ruang lingkup dan standar pelaksanaan pekerjaan sesuai dokumen sumber yang akan disediakan melalui layanan backend.</p></div>}{docTab === 'outline' && <div className="outline-list"><div className="outline-intro">STRUKTUR DOKUMEN <span>{active.document.chapters.length} BAB</span></div>{active.document.chapters.map((chapter) => <div className="outline-chapter" key={chapter.no}><div className="outline-number">{chapter.no}</div><div><strong>BAB {chapter.no} — {chapter.title}</strong>{chapter.sections.map((section, index) => <p key={section}>{Number(chapter.no)}.{index + 1} {section}</p>)}</div></div>)}</div>}{docTab === 'convert' && <div className="convert-card"><div className="convert-icon"><ArrowDownToLine size={24} /></div><h3>PDF ke Word, lebih mudah</h3><p>Alur konversi mempertahankan struktur dokumen asli. Fungsi unduhan akan tersedia setelah API backend terhubung.</p><div className="convert-file"><FileText size={21} /><div><strong>{active.document.filename}</strong><small>Dokumen sumber · PDF</small></div><Check size={17} /></div><button className="primary-button" onClick={() => setConvertOpen(true)}><FileCheck2 size={17} /> Lihat alur konversi</button></div>}</div><div className="viewer-footer"><FileClock size={15} /> Konten demo untuk pratinjau antarmuka</div></> : <div className="viewer-empty"><div className="viewer-empty-icon"><FileSearch size={32} /></div><div className="empty-dots"><span /><span /><span /></div><h3>Belum ada dokumen dibuka</h3><p>Minta asisten mencari dokumen RKS. Hasilnya akan muncul di panel ini agar mudah ditinjau.</p><button onClick={() => submitMessage('Tolong ambilkan dokumen full RKS untuk overhaul tangki')}>Coba cari dokumen <ArrowRight size={16} /></button><div className="viewer-empty-foot"><BookOpenText size={16} /> Preview · Daftar bab · Konversi</div></div>}</section>}
      </div>
      <footer className="page-footer"><span>© 2026 Pertamina Patra Niaga · Template antarmuka</span><span>Built for a smarter procurement workflow <span className="footer-star">✦</span></span></footer>
    </div>

    {convertOpen && <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setConvertOpen(false) }}><div className="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title"><button className="modal-close icon-button" aria-label="Tutup dialog" onClick={() => setConvertOpen(false)}><X size={19} /></button><div className="modal-icon"><FileCheck2 size={25} /></div><h2 id="modal-title">Konversi PDF ke DOCX</h2><p>Alur ini siap dihubungkan ke layanan konversi pada backend.</p><label>File sumber<div className="modal-source"><FileText size={18} /> {active.document?.filename || 'Belum ada dokumen'}</div></label><label>Nama file keluaran<input value={active.document?.filename?.replace(/\.pdf$/i, '.docx') || ''} readOnly /></label><div className="modal-note"><CircleHelp size={17} /> Mode pratinjau belum menghasilkan file. Tombol unduh akan tersedia setelah API konversi aktif.</div><div className="modal-actions"><button className="outline-button" onClick={() => setConvertOpen(false)}>Tutup</button><button className="primary-button" disabled><Download size={16} /> Konversi & unduh</button></div></div></div>}
    {notice && <div className="toast" role="status"><Check size={16} /> {notice}<button aria-label="Tutup pesan" onClick={() => setNotice('')}><X size={14} /></button></div>}
  </div>
}

export default App
