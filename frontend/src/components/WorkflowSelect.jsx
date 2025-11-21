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
            <div className="relative min-h-screen bg-bg-primary text-text-primary transition-colors duration-300">
                <div className="absolute inset-0 bg-gradient-to-br from-bg-primary via-bg-secondary to-bg-primary opacity-80" aria-hidden="true" />
                <div className="relative z-10 mx-auto max-w-2xl px-6 py-20">
                    <button onClick={handleBack} className="inline-flex items-center gap-2 text-sm text-text-secondary hover:text-text-primary transition-colors">
                        <ArrowLeftIcon className="w-4 h-4" /> Back to upload
                    </button>
                    <div className="mt-6 rounded-3xl border border-border-primary dark:border-text-secondary/10 bg-bg-secondary/60 dark:bg-transparent p-8 backdrop-blur">
                        <h1 className="text-2xl font-semibold text-text-primary">No upload found</h1>
                        <p className="mt-2 text-text-secondary">Please upload a document first to choose a workflow.</p>
                        <div className="mt-6">
                            <button onClick={handleBack} className="rounded-xl bg-bg-primary text-text-primary border border-border-primary font-semibold px-5 py-3 hover:bg-bg-secondary transition-colors">Go to Upload</button>
                        </div>
                    </div>
                </div>
            </div>
        )
    }

    return (
        <div className="relative min-h-screen bg-bg-primary text-text-primary transition-colors duration-300">
            <div className="absolute inset-0 bg-gradient-to-br from-bg-primary via-bg-secondary to-bg-primary opacity-80" aria-hidden="true" />
            <div className="relative z-10 mx-auto max-w-5xl px-6 py-14">
                <div className="flex items-center justify-between">
                    <button onClick={handleBack} className="inline-flex items-center gap-2 text-sm text-text-secondary hover:text-text-primary transition-colors">
                        <ArrowLeftIcon className="w-4 h-4" /> Back
                    </button>
                    <div className="text-xs text-text-secondary/80">Uploaded file ready</div>
                </div>

                <div className="mt-6 text-center">
                    <div className="inline-flex items-center gap-2 bg-bg-secondary/50 border border-border-primary px-4 py-2 rounded-full text-sm font-medium tracking-wide uppercase text-text-secondary">
                        <span className="w-2 h-2 rounded-full bg-accent-coral animate-pulse" aria-hidden="true" />
                        Select a workflow
                    </div>
                    <h1 className="mt-4 text-4xl md:text-5xl font-bold tracking-tight text-text-primary">How should I analyze your document?</h1>
                    <p className="mt-3 text-lg text-text-secondary max-w-2xl mx-auto">
                        Pick the depth of reasoning you need. You can always return and try the other approach.
                    </p>
                </div>

                <div className="mt-10 grid gap-6 md:grid-cols-2">
                    {/* Simple RAG */}
                    <button
                        onClick={() => chooseWorkflow('simple')}
                        className="group text-left rounded-3xl p-6 bg-white dark:bg-transparent border-2 border-border-primary dark:border-text-secondary/10 hover:border-accent-pink dark:hover:border-text-secondary/30 hover:bg-gray-50 dark:hover:bg-bg-secondary/10 transition shadow-sm hover:shadow-md dark:shadow-xl dark:hover:shadow-2xl backdrop-blur"
                    >
                        <div className="flex items-center gap-4">
                            <span className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-accent-pink/20 text-accent-pink ring-2 ring-accent-pink/40">
                                <SparklesIcon className="w-6 h-6" />
                            </span>
                            <div>
                                <h2 className="text-xl font-semibold text-text-primary">Workflow 1 — Simple RAG</h2>
                                <p className="text-text-secondary text-sm">Fast, focused retrieval and answer generation. Great for straightforward Q&A.</p>
                            </div>
                        </div>
                        <ul className="mt-5 space-y-2 text-sm text-text-secondary">
                            <li className="flex items-start gap-2"><CheckCircleIcon className="w-4 h-4 mt-0.5 text-accent-coral" /> Lower latency</li>
                            <li className="flex items-start gap-2"><CheckCircleIcon className="w-4 h-4 mt-0.5 text-accent-coral" /> Context-aware follow-ups</li>

                        </ul>
                    </button>

                    {/* Agentic RAG */}
                    <button
                        onClick={() => chooseWorkflow('agent')}
                        className="group text-left rounded-3xl p-6 bg-white dark:bg-transparent border-2 border-border-primary dark:border-text-secondary/10 hover:border-accent-coral dark:hover:border-text-secondary/30 hover:bg-gray-50 dark:hover:bg-bg-secondary/10 transition shadow-sm hover:shadow-md dark:shadow-xl dark:hover:shadow-2xl backdrop-blur"
                    >
                        <div className="flex items-center gap-4">
                            <span className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-accent-coral/20 text-accent-coral ring-2 ring-ring-primary">
                                <BeakerIcon className="w-6 h-6" />
                            </span>
                            <div>
                                <h2 className="text-xl font-semibold text-text-primary">Workflow 2 — Agentic RAG</h2>
                                <p className="text-text-secondary text-sm">Tool-using agent for deeper reasoning, calculations, and multi-step analysis.</p>
                            </div>
                        </div>
                        <ul className="mt-5 space-y-2 text-sm text-text-secondary">
                            <li className="flex items-start gap-2"><CheckCircleIcon className="w-4 h-4 mt-0.5 text-accent-coral" /> Rich chain-of-thought orchestration</li>
                            <li className="flex items-start gap-2"><CheckCircleIcon className="w-4 h-4 mt-0.5 text-accent-coral" /> Uses retriever and calculator tools</li>

                        </ul>
                    </button>
                </div>

                <div className="mt-10 text-center text-text-secondary/80 text-sm">
                    You can switch workflows by going back after trying one.
                </div>
            </div>
            <div className="absolute inset-x-0 top-0 h-40 bg-gradient-to-b from-bg-primary/50 to-transparent" aria-hidden="true" />
            <div className="absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-bg-primary/60 to-transparent" aria-hidden="true" />
        </div>
    )
}

export default WorkflowSelect