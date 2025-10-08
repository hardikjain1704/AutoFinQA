import FileUploader from '../components/FileUploader'

function UploadPage() {
  return (
    <div className="relative min-h-full">
      <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-blue-900 to-blue-600" aria-hidden="true" />
      <div className="relative z-10 min-h-screen flex items-center justify-center px-4 py-16">
        <div className="w-full max-w-4xl">
          <div className="mb-8 text-center text-white space-y-4">
            <div className="inline-flex items-center gap-2 bg-white/10 px-4 py-2 rounded-full text-sm font-medium tracking-wide uppercase">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" aria-hidden="true" />
              Upload financial document
            </div>
            <h1 className="text-4xl md:text-5xl font-bold tracking-tight">Kickstart your financial analysis</h1>
            <p className="text-lg md:text-xl text-blue-100 max-w-2xl mx-auto">
              Upload earnings reports, balance sheets, or investment decks. Our AI assistant will break down every insight and answer follow-up questions instantly.
            </p>
          </div>
          <FileUploader />
        </div>
      </div>
      <div className="absolute inset-x-0 top-0 h-40 bg-gradient-to-b from-black/50 to-transparent" aria-hidden="true" />
      <div className="absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-slate-950/60 to-transparent" aria-hidden="true" />
    </div>
  )
}

export default UploadPage
