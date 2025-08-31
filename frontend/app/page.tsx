"use client"

import React from "react"
import { useState } from "react"
import { Upload, FileText, Menu, History, Plus, Clock, Trash2, AlertCircle, CheckCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Loading } from "@/components/ui/loading"
import { ProcessingStatus } from "@/components/ui/processing-status"
import { useFileUpload } from "@/lib/hooks/useFileUpload"
import { FileUploadResponse } from "@/lib/api"
import Link from "next/link"

type StudyMode = "upload" | "qa" | "quiz" | "flashcards"

interface StudySession {
  id: string
  fileName: string
  mode: StudyMode
  timestamp: Date
  preview: string
  fileId?: string
  sessionId?: string
}

export default function StudyApp() {
  const [isDragOver, setIsDragOver] = useState(false)
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [showMenu, setShowMenu] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const [uploadResult, setUploadResult] = useState<FileUploadResponse | null>(null)
  const { uploadState, uploadFile, resetUpload } = useFileUpload()
  const [studySessions, setStudySessions] = useState<StudySession[]>([
    {
      id: "1",
      fileName: "Data Structures Guide.pdf",
      mode: "qa",
      timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000), // 2 hours ago
      preview: "Discussed binary trees and sorting algorithms",
    },
    {
      id: "2",
      fileName: "Machine Learning Basics.docx",
      mode: "quiz",
      timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000), // 1 day ago
      preview: "Completed quiz on supervised learning - 85% score",
    },
    {
      id: "3",
      fileName: "JavaScript Fundamentals.txt",
      mode: "flashcards",
      timestamp: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000), // 3 days ago
      preview: "Reviewed 15 flashcards on closures and promises",
    },
  ])
  const [isNavigatingToQA, setIsNavigatingToQA] = useState(false)  // Add navigation state

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)

    const files = Array.from(e.dataTransfer.files)
    const file = files[0]

    if (
      file &&
      (file.type === "application/pdf" ||
        file.type === "application/vnd.openxmlformats-officedocument.wordprocessingml.document" ||
        file.type === "application/vnd.openxmlformats-officedocument.presentationml.presentation" ||
        file.type === "text/plain")
    ) {
      setUploadedFile(file)
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setUploadedFile(file)
    }
  }

  const handleModeSelect = async (mode: StudyMode) => {
    setShowMenu(false)

    if (uploadedFile) {
      try {
        // Upload file to backend with study mode
        const result = await uploadFile(uploadedFile, mode)
        if (result) {
          setUploadResult(result)

          const newSession: StudySession = {
            id: Date.now().toString(),
            fileName: uploadedFile.name,
            mode: mode,
            timestamp: new Date(),
            preview: `Started ${mode === "qa" ? "Q&A session" : mode === "quiz" ? "quiz" : "flashcard review"}`,
            fileId: result.file_id,
          }
          setStudySessions((prev) => [newSession, ...prev])

          // Store file data and upload result in localStorage for the target page
          localStorage.setItem(
            "uploadedFile",
            JSON.stringify({
              name: uploadedFile.name,
              size: uploadedFile.size,
              type: uploadedFile.type,
              fileId: result.file_id,
              uploadResult: result,
            }),
          )

          // Automatically navigate to the appropriate page based on mode
          if (mode === "quiz") {
            window.location.href = "/quiz"
          } else if (mode === "qa") {
            window.location.href = "/qa"
          } else if (mode === "flashcards") {
            window.location.href = "/flashcards"
          }
        }
      } catch (error) {
        console.error("Failed to upload file:", error)
        // Error is already handled by the useFileUpload hook
      }
    }
  }

  const handleNewSession = () => {
    setUploadedFile(null)
    setUploadResult(null)
    setShowMenu(false)
    setShowHistory(false)
    resetUpload()
    // Clear any stored file data
    localStorage.removeItem("uploadedFile")
  }

  const handleLoadSession = (session: StudySession) => {
    setShowHistory(false)
    setShowMenu(false)
    alert(`Loading session: ${session.fileName} (${session.mode})`)
  }

  const handleNavigateToQA = () => {
    setIsNavigatingToQA(true)
    // The navigation will happen automatically via the Link component
  }

  const handleDeleteSession = (sessionId: string) => {
    setStudySessions((prev) => prev.filter((session) => session.id !== sessionId))
  }

  const formatTimeAgo = (date: Date) => {
    const now = new Date()
    const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60))

    if (diffInHours < 1) return "Just now"
    if (diffInHours < 24) return `${diffInHours}h ago`

    const diffInDays = Math.floor(diffInHours / 24)
    if (diffInDays < 7) return `${diffInDays}d ago`

    return date.toLocaleDateString()
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header with hamburger menu */}
      <header className="flex items-center justify-between p-4 border-b border-border">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => setShowMenu(!showMenu)} className="p-2">
            <Menu className="h-5 w-5" />
          </Button>
          <h1 className="text-xl font-bold font-montserrat text-foreground">ScholAr</h1>
        </div>
      </header>

      {/* Hamburger Menu */}
      {showMenu && (
        <div className="absolute top-16 left-4 z-50 bg-card border border-border rounded-lg shadow-lg p-2 min-w-48">
          <Button variant="ghost" className="w-full justify-start gap-2 text-sm" onClick={handleNewSession}>
            <Plus className="h-4 w-4" />
            New Session
          </Button>
          <Button
            variant="ghost"
            className="w-full justify-start gap-2 text-sm"
            onClick={() => {
              setShowHistory(true)
              setShowMenu(false)
            }}
          >
            <History className="h-4 w-4" />
            History
          </Button>
        </div>
      )}

      {/* History Modal */}
      {showHistory && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <Card className="w-full max-w-2xl max-h-[80vh] bg-card">
            <div className="p-6 border-b border-border">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold font-montserrat text-foreground">Study History</h2>
                <Button variant="ghost" size="sm" onClick={() => setShowHistory(false)}>
                  ×
                </Button>
              </div>
            </div>

            <ScrollArea className="max-h-96 p-6">
              {studySessions.length === 0 ? (
                <div className="text-center py-8">
                  <Clock className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <p className="text-muted-foreground">No study sessions yet</p>
                </div>
              ) : (
                <div className="space-y-4 max-h-80 overflow-y-auto pr-2">
                  {studySessions.map((session) => (
                    <Card key={session.id} className="p-4 hover:bg-muted/50 transition-colors">
                      <div className="flex items-start justify-between">
                        <div className="flex-1 cursor-pointer" onClick={() => handleLoadSession(session)}>
                          <div className="flex items-center gap-2 mb-2">
                            <FileText className="h-4 w-4 text-accent" />
                            <h3 className="font-medium text-foreground">{session.fileName}</h3>
                            <span
                              className={`px-2 py-1 rounded-full text-xs font-medium ${
                                session.mode === "qa"
                                  ? "bg-blue-100 text-blue-800"
                                  : session.mode === "quiz"
                                    ? "bg-green-100 text-green-800"
                                    : "bg-purple-100 text-purple-800"
                              }`}
                            >
                              {session.mode === "qa" ? "Q&A" : session.mode === "quiz" ? "Quiz" : "Flashcards"}
                            </span>
                          </div>
                          <p className="text-sm text-muted-foreground mb-2">{session.preview}</p>
                          <p className="text-xs text-muted-foreground">{formatTimeAgo(session.timestamp)}</p>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation()
                            handleDeleteSession(session.id)
                          }}
                          className="text-muted-foreground hover:text-destructive"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </Card>
                  ))}
                </div>
              )}
            </ScrollArea>
          </Card>
        </div>
      )}

      {/* Main Content */}
      <main className="flex-1 p-8">
        <div className="max-w-4xl mx-auto h-full">

          {!uploadedFile && (
            <div className="text-center space-y-8">
              <div className="space-y-4">
                <h2 className="text-3xl font-bold font-montserrat text-foreground">ScholAr</h2>
                <p className="text-muted-foreground text-lg">
                  Upload a document to start studying with AI-powered tools
                </p>
              </div>

              {/* File Upload Area */}
              <Card
                className={`p-12 border-2 border-dashed transition-colors cursor-pointer ${
                  isDragOver ? "border-accent bg-accent/5" : "border-border hover:border-accent/50"
                }`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => document.getElementById("file-input")?.click()}
              >
                <div className="space-y-4">
                  <div className="flex justify-center">
                    <Upload className="h-12 w-12 text-muted-foreground" />
                  </div>
                  <div className="space-y-2">
                    <p className="text-lg font-medium text-foreground">Drop your file here or click to browse</p>
                    <p className="text-sm text-muted-foreground">Supports PDF, DOCX, PPTX, and TXT files</p>
                  </div>
                </div>
              </Card>

              <input
                id="file-input"
                type="file"
                accept=".pdf,.docx,.pptx,.txt"
                onChange={handleFileSelect}
                className="hidden"
              />
            </div>
          )}

          {uploadedFile && !uploadState.isUploading && !uploadState.error && !uploadResult && (
            <div className="space-y-8">
              <div className="text-center space-y-4">
                <div className="flex justify-center">
                  <FileText className="h-16 w-16 text-accent" />
                </div>
                <div>
                  <h2 className="text-2xl font-bold font-montserrat text-center text-foreground mb-2">
                    File Ready for Upload
                  </h2>
                  <p className="text-muted-foreground">
                    {uploadedFile.name} • {(uploadedFile.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>
              </div>

              <div className="space-y-4">
                <h3 className="text-lg font-semibold font-montserrat text-center text-foreground">
                  Choose your study mode:
                </h3>

                <div className="grid gap-4">
                  <Button 
                    size="lg" 
                    variant="outline"
                    className="w-full h-16 text-lg font-medium border-2 bg-transparent hover:bg-accent hover:text-accent-foreground"
                    onClick={() => handleModeSelect("qa")}
                  >
                    Q&A Chat
                    <span className="text-sm font-normal ml-2 opacity-80">Ask questions about your document</span>
                  </Button>

                  <Button
                    size="lg"
                    variant="outline"
                    className="w-full h-16 text-lg font-medium border-2 bg-transparent hover:bg-accent hover:text-accent-foreground"
                    onClick={() => handleModeSelect("quiz")}
                  >
                    Generate Quiz
                    <span className="text-sm font-normal ml-2 opacity-80">Test your knowledge</span>
                  </Button>

                  <Button
                    size="lg"
                    variant="outline"
                    className="w-full h-16 text-lg font-medium border-2 bg-transparent hover:bg-accent hover:text-accent-foreground"
                    onClick={() => handleModeSelect("flashcards")}
                  >
                    Create Flashcards
                    <span className="text-sm font-normal ml-2 opacity-80">Review key concepts</span>
                  </Button>
                </div>
              </div>
            </div>
          )}

          {/* Upload Loading State */}
          {uploadState.isUploading && (
            <div className="space-y-8">
              <div className="text-center space-y-4">
                <Loading 
                  message="Processing your document..." 
                  progress={uploadState.uploadProgress}
                  showProgress={true}
                />
                <ProcessingStatus
                  steps={uploadState.processingSteps}
                  totalTime={uploadState.uploadResult?.rag_processing?.processing_time_seconds}
                  isComplete={false}
                />
              </div>
            </div>
          )}

          {/* Upload Error State */}
          {uploadState.error && (
            <div className="space-y-8">
              <div className="text-center space-y-4">
                <div className="flex justify-center">
                  <AlertCircle className="h-16 w-16 text-destructive" />
                </div>
                <div>
                  <h2 className="text-2xl font-bold font-montserrat text-center text-foreground mb-2">
                    Upload Failed
                  </h2>
                  <p className="text-destructive mb-4">{uploadState.error}</p>
                  <Button onClick={handleNewSession} variant="outline">
                    Try Again
                  </Button>
                </div>
              </div>
            </div>
          )}

          {/* Upload Success State */}
          {uploadResult && (
            <div className="space-y-8">
              <div className="text-center space-y-4">
                <div className="flex justify-center">
                  <CheckCircle className="h-16 w-16 text-green-500" />
                </div>
                <div>
                  <h2 className="text-2xl font-bold font-montserrat text-center text-foreground mb-2">
                    File Processed Successfully
                  </h2>
                  <p className="text-muted-foreground mb-4">
                    {uploadResult.filename} • {(uploadResult.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                  
                  {/* Show processing details */}
                  <ProcessingStatus
                    steps={uploadState.processingSteps}
                    totalTime={uploadResult.rag_processing?.processing_time_seconds}
                    isComplete={true}
                  />
                </div>
              </div>

              <div className="text-center space-y-4">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent mx-auto"></div>
                <p className="text-muted-foreground">Redirecting to study mode...</p>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
