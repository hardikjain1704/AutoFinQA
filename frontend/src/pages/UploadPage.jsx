import FileUploader from '../components/FileUploader'

function UploadPage() {
  return (
    <div className="relative min-h-full bg-bg-primary text-text-primary transition-colors duration-300">
      <div className="absolute inset-0 bg-gradient-to-br from-bg-primary via-bg-secondary to-bg-primary opacity-80" aria-hidden="true" />
      <div className="relative z-10 min-h-screen flex items-center justify-center px-4 py-16">
        <div className="w-full max-w-4xl">
          <div className="mb-8 text-center space-y-4">
            <div className="inline-flex items-center gap-2 bg-bg-secondary/50 border border-border-primary px-4 py-2 rounded-full text-sm font-medium tracking-wide uppercase text-text-secondary">
              <span className="w-2 h-2 rounded-full bg-accent-coral animate-pulse" aria-hidden="true" />
              Upload financial document
            </div>
            <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-text-primary">Kickstart your financial analysis</h1>
            <p className="text-lg md:text-xl text-text-secondary max-w-2xl mx-auto">
              Upload earnings reports, balance sheets, or investment decks. Our AI assistant will break down every insight and answer follow-up questions instantly.
            </p>
          </div>
          <FileUploader />
        </div>
      </div>
      <div className="absolute inset-x-0 top-0 h-40 bg-gradient-to-b from-bg-primary/50 to-transparent" aria-hidden="true" />
      <div className="absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-bg-primary/60 to-transparent" aria-hidden="true" />
    </div>
  )
}

export default UploadPage
