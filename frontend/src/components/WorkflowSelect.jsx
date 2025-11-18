import { useLocation, useNavigate } from 'react-router-dom'
import { ArrowLeftIcon, BeakerIcon, CheckCircleIcon, SparklesIcon } from '@heroicons/react/24/outline'

function WorkflowSelect() {
    const navigate = useNavigate()
    const location = useLocation()
    const uploadedData = location.state

    const chooseWorkflow = (workflow) => {
        navigate('/chat', {
            state: {
                ...uploadedData,
                workflow,
            },
        })
    }

    const handleBack = () => navigate('/')

    // Gentle fallback if someone opens this page directly
    if (!uploadedData) {
        return (
            <div className="relative min-h-screen">
                <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-blue-900 to-blue-600" aria-hidden="true" />
                <div className="relative z-10 mx-auto max-w-2xl px-6 py-20 text-white">
                    <button onClick={handleBack} className="inline-flex items-center gap-2 text-sm text-blue-100 hover:text-white">
                        <ArrowLeftIcon className="w-4 h-4" /> Back to upload
                    </button>
                    <div className="mt-6 rounded-3xl border border-white/20 bg-white/10 p-8 backdrop-blur">
                        <h1 className="text-2xl font-semibold">No upload found</h1>
                        <p className="mt-2 text-blue-100/90">Please upload a document first to choose a workflow.</p>
                        <div className="mt-6">
                            <button onClick={handleBack} className="rounded-xl bg-white text-slate-900 font-semibold px-5 py-3 hover:bg-blue-50">Go to Upload</button>
                        </div>
                    </div>
                </div>
            </div>
        )
    }

    return (
        <div className="relative min-h-screen">
            <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-blue-900 to-blue-600" aria-hidden="true" />
            <div className="relative z-10 mx-auto max-w-5xl px-6 py-14 text-white">
                <div className="flex items-center justify-between">
                    <button onClick={handleBack} className="inline-flex items-center gap-2 text-sm text-blue-100 hover:text-white">
                        <ArrowLeftIcon className="w-4 h-4" /> Back
                    </button>
                    <div className="text-xs text-blue-100/80">Uploaded file ready</div>
                </div>

                <div className="mt-6 text-center">
                    <div className="inline-flex items-center gap-2 bg-white/10 px-4 py-2 rounded-full text-sm font-medium tracking-wide uppercase">
                        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" aria-hidden="true" />
                        Select a workflow
                    </div>
                    <h1 className="mt-4 text-4xl md:text-5xl font-bold tracking-tight">How should I analyze your document?</h1>
                    <p className="mt-3 text-lg text-blue-100 max-w-2xl mx-auto">
                        Pick the depth of reasoning you need. You can always return and try the other approach.
                    </p>
                </div>

                <div className="mt-10 grid gap-6 md:grid-cols-2">
                    {/* Simple RAG */}
                    <button
                        onClick={() => chooseWorkflow('simple')}
                        className="group text-left rounded-3xl p-6 bg-white/10 border border-white/20 hover:border-blue-200/60 hover:bg-white/15 transition shadow-xl hover:shadow-2xl backdrop-blur"
                    >
                        <div className="flex items-center gap-4">
                            <span className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-500/20 text-blue-100 ring-2 ring-blue-300/40">
                                <SparklesIcon className="w-6 h-6" />
                            </span>
                            <div>
                                <h2 className="text-xl font-semibold">Workflow 1 — Simple RAG</h2>
                                <p className="text-blue-100/90 text-sm">Fast, focused retrieval and answer generation. Great for straightforward Q&A.</p>
                            </div>
                        </div>
                        <ul className="mt-5 space-y-2 text-sm text-blue-100/90">
                            <li className="flex items-start gap-2"><CheckCircleIcon className="w-4 h-4 mt-0.5 text-emerald-300" /> Lower latency</li>
                            <li className="flex items-start gap-2"><CheckCircleIcon className="w-4 h-4 mt-0.5 text-emerald-300" /> Context-aware follow-ups</li>
                            <li className="flex items-start gap-2"><CheckCircleIcon className="w-4 h-4 mt-0.5 text-emerald-300" /> Endpoint: <span className="ml-1 font-mono">/ask</span></li>
                        </ul>
                    </button>

                    {/* Agentic RAG */}
                    <button
                        onClick={() => chooseWorkflow('agent')}
                        className="group text-left rounded-3xl p-6 bg-white/10 border border-white/20 hover:border-emerald-200/60 hover:bg-white/15 transition shadow-xl hover:shadow-2xl backdrop-blur"
                    >
                        <div className="flex items-center gap-4">
                            <span className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-500/20 text-emerald-100 ring-2 ring-emerald-300/40">
                                <BeakerIcon className="w-6 h-6" />
                            </span>
                            <div>
                                <h2 className="text-xl font-semibold">Workflow 2 — Agentic RAG</h2>
                                <p className="text-blue-100/90 text-sm">Tool-using agent for deeper reasoning, calculations, and multi-step analysis.</p>
                            </div>
                        </div>
                        <ul className="mt-5 space-y-2 text-sm text-blue-100/90">
                            <li className="flex items-start gap-2"><CheckCircleIcon className="w-4 h-4 mt-0.5 text-emerald-300" /> Rich chain-of-thought orchestration</li>
                            <li className="flex items-start gap-2"><CheckCircleIcon className="w-4 h-4 mt-0.5 text-emerald-300" /> Uses retriever and calculator tools</li>
                            <li className="flex items-start gap-2"><CheckCircleIcon className="w-4 h-4 mt-0.5 text-emerald-300" /> Endpoint: <span className="ml-1 font-mono">/ask-agent</span></li>
                        </ul>
                    </button>
                </div>

                <div className="mt-10 text-center text-blue-100/80 text-sm">
                    You can switch workflows by going back after trying one.
                </div>
            </div>
            <div className="absolute inset-x-0 top-0 h-40 bg-gradient-to-b from-black/50 to-transparent" aria-hidden="true" />
            <div className="absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-slate-950/60 to-transparent" aria-hidden="true" />
        </div>
    )
}

export default WorkflowSelect