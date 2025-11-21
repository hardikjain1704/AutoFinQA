import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowUpTrayIcon, DocumentTextIcon, CheckCircleIcon } from '@heroicons/react/24/outline'
import { documentService } from '../services/documentService'

const ACCEPTED_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.presentationml.presentation',
  'text/plain'
]

function FileUploader() {
  const inputRef = useRef(null)
  const navigate = useNavigate()
  const [selectedFile, setSelectedFile] = useState(null)
  const [isDragging, setIsDragging] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  const resetStatus = () => {
    setErrorMessage('')
    setSuccessMessage('')
  }

  const validateFile = (file) => {
    if (!file) {
      setErrorMessage('Please select a file to upload.')
      return false
    }

    // Accept up to 25MB
    const twentyFiveMB = 25 * 1024 * 1024
    if (file.size > twentyFiveMB) {
      setErrorMessage('File size must be less than 25MB.')
      return false
    }

    if (!ACCEPTED_TYPES.includes(file.type)) {
      setErrorMessage('Unsupported file type. Please upload PDF, DOCX, PPTX, or TXT files.')
      return false
    }

    return true
  }

  const handleFileSelection = (file) => {
    resetStatus()
    if (validateFile(file)) {
      setSelectedFile(file)
    } else {
      setSelectedFile(null)
    }
  }

  const handleBrowseClick = () => {
    inputRef.current?.click()
  }

  const handleInputChange = (event) => {
    const file = event.target.files?.[0]
    if (file) {
      handleFileSelection(file)
    }
  }

  const handleDragOver = (event) => {
    event.preventDefault()
    event.stopPropagation()
    setIsDragging(true)
  }

  const handleDragLeave = (event) => {
    event.preventDefault()
    event.stopPropagation()
    setIsDragging(false)
  }

  const handleDrop = (event) => {
    event.preventDefault()
    event.stopPropagation()
    setIsDragging(false)
    const file = event.dataTransfer.files?.[0]
    if (file) {
      handleFileSelection(file)
    }
  }

  const handleSubmit = async () => {
    if (!selectedFile) {
      setErrorMessage('Please choose a document before uploading.')
      return
    }

    resetStatus()
    setIsUploading(true)

    try {
      const response = await documentService.uploadDocument(selectedFile)
      const successText = response?.message || 'Upload complete! Redirecting you to workflow selection...'
      setSuccessMessage(successText)

      setTimeout(() => {
        navigate('/workflow', {
          state: {
            uploadedFileName: response?.filename || selectedFile.name,
            uploadResponse: response
          }
        })
      }, 600)
    } catch (error) {
      const detail = error?.response?.data?.detail
      setErrorMessage(detail || error.message || 'Something went wrong while uploading the document.')
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <div className="bg-bg-secondary/30 backdrop-blur-sm border border-text-secondary/10 rounded-3xl shadow-2xl overflow-hidden transition-colors duration-300">
      <div className="grid gap-10 md:grid-cols-[1.2fr,0.8fr] p-8 md:p-12">
        <div
          className={`group relative flex flex-col items-center justify-center text-center border-2 border-dashed rounded-2xl transition-all duration-300 cursor-pointer ${isDragging
            ? 'border-accent-coral/90 bg-accent-coral/10 shadow-lg shadow-accent-coral/30'
            : 'border-text-secondary/20 hover:border-accent-pink/80 hover:bg-bg-secondary/50'
            }`}
          onClick={handleBrowseClick}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-bg-secondary/20 via-bg-secondary/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" aria-hidden="true" />
          <div className="relative z-10 flex flex-col items-center space-y-6 px-6 py-12">
            <span className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-accent-pink/20 text-accent-pink ring-2 ring-accent-pink/40">
              <ArrowUpTrayIcon className="w-8 h-8" />
            </span>
            <div className="space-y-2">
              <h2 className="text-2xl font-semibold text-text-primary tracking-tight">Drop your file anywhere</h2>
              <p className="text-text-secondary text-sm md:text-base max-w-md mx-auto">
                We support quarterly reports, balance sheets, investor presentations, and more.
              </p>
            </div>
            <div className="flex items-center gap-2 text-sm text-text-secondary/80">
              <DocumentTextIcon className="w-5 h-5" />
              <span>PDF, DOCX, PPTX, TXT · Max 25MB</span>
            </div>
            <button
              type="button"
              className="inline-flex items-center justify-center rounded-full bg-bg-primary text-accent-coral font-semibold px-6 py-2 shadow-lg shadow-text-secondary/10 hover:shadow-xl hover:shadow-text-secondary/20 transition border border-text-secondary/10"
            >
              Browse files
            </button>
          </div>
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPTED_TYPES.join(',')}
            onChange={handleInputChange}
            className="hidden"
          />
        </div>

        <div className="text-text-primary/90 space-y-6">
          <div className="bg-bg-secondary/50 border border-text-secondary/10 rounded-2xl p-6">
            <h3 className="text-lg font-semibold mb-4 text-text-primary">Analysis we'll unlock</h3>
            <ul className="space-y-3 text-sm text-text-secondary">
              <li className="flex items-start gap-3">
                <CheckCircleIcon className="w-5 h-5 mt-0.5 text-accent-coral" />
                Instant summaries and KPI extraction
              </li>
              <li className="flex items-start gap-3">
                <CheckCircleIcon className="w-5 h-5 mt-0.5 text-accent-coral" />
                Deep dive insights with follow-up conversations
              </li>
              <li className="flex items-start gap-3">
                <CheckCircleIcon className="w-5 h-5 mt-0.5 text-accent-coral" />
                Smart comparisons across uploaded reports
              </li>
            </ul>
          </div>

          <div className="space-y-4">
            {selectedFile ? (
              <div className="flex items-center justify-between bg-bg-secondary/50 border border-text-secondary/10 rounded-2xl px-4 py-3 text-sm">
                <div>
                  <p className="font-semibold text-text-primary tracking-wide">{selectedFile.name}</p>
                  <p className="text-text-secondary/80">
                    {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB · {selectedFile.type || 'Unknown type'}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    resetStatus()
                    setSelectedFile(null)
                    inputRef.current && (inputRef.current.value = '')
                  }}
                  className="text-sm font-medium text-accent-pink hover:text-accent-pink/80 transition"
                >
                  Clear
                </button>
              </div>
            ) : (
              <div className="rounded-2xl border border-dashed border-text-secondary/30 text-text-secondary/70 px-4 py-8 text-center">
                <p className="font-medium">No document selected yet</p>
                <p className="text-sm">Drag and drop your file or tap browse to choose one from your device.</p>
              </div>
            )}

            {errorMessage && (
              <div className="rounded-2xl border border-accent-coral/60 bg-accent-coral/20 px-4 py-3 text-sm text-text-primary">
                {errorMessage}
              </div>
            )}

            {successMessage && (
              <div className="rounded-2xl border border-accent-pink/60 bg-accent-pink/20 px-4 py-3 text-sm text-text-primary">
                {successMessage}
              </div>
            )}

            <button
              type="button"
              onClick={handleSubmit}
              disabled={isUploading}
              className="w-full inline-flex items-center justify-center gap-2 rounded-2xl bg-accent-coral text-bg-primary font-semibold px-6 py-4 shadow-lg shadow-accent-coral/30 hover:bg-accent-coral/90 transition disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {isUploading ? 'Uploading…' : 'Analyze Document'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default FileUploader
