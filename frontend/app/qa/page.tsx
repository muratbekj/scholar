"use client"

import React, { useState, useEffect, useRef } from "react"
import { Menu, History, Plus, ArrowLeft, AlertCircle, Bot, FileText } from "lucide-react"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Loading } from "@/components/ui/loading"
import { Message } from "@/components/chat/Message"
import { ChatInput } from "@/components/chat/ChatInput"
import { SessionHistory } from "@/components/chat/SessionHistory"
import { useQASession } from "@/lib/hooks/useQASession"
import { useSessionHistory } from "@/lib/hooks/useSessionHistory"
import { useToast } from "@/components/ui/toast"
import { QAMessage } from "@/lib/api"
import Link from "next/link"

export default function QAPage() {
  const [showMenu, setShowMenu] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const [fileName, setFileName] = useState<string>("")
  const [fileId, setFileId] = useState<string>("")
  const [isInitializing, setIsInitializing] = useState(true)  // Add initial loading state
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const sessionCreatedRef = useRef(false)

  const { sessionState, createSession, loadSession, askQuestion, deleteSession, clearError, resetSession } = useQASession()
  const { historyState, removeSessionFromList, addSessionToList } = useSessionHistory()
  const { addToast, clearToasts } = useToast()

  useEffect(() => {
    // Get uploaded file info from localStorage
    const fileData = localStorage.getItem("uploadedFile")
    if (fileData) {
      const file = JSON.parse(fileData)
      setFileName(file.name)
      setFileId(file.fileId)

      // Create QA session if we have file data and haven't created one yet
      if (file.fileId && file.name && !sessionCreatedRef.current) {
        sessionCreatedRef.current = true
        // Remove toast - we'll use the full-screen loading instead

        createSession(file.fileId, file.name)
          .then((session) => {
            if (session) {
              addSessionToList(session)
              addToast({
                type: 'success',
                title: 'Session created!',
                message: 'You can now ask questions about your document'
              });
            }
          })
          .catch((error) => {
            console.error("Failed to create session:", error)
            sessionCreatedRef.current = false // Reset on error
            addToast({
              type: 'error',
              title: 'Session creation failed',
              message: error instanceof Error ? error.message : 'Unknown error'
            });
          })
          .finally(() => {
            setIsInitializing(false)  // Hide initial loading state
          })
      } else {
        setIsInitializing(false)  // Hide initial loading state if no file data
      }
    } else {
      setIsInitializing(false)  // Hide initial loading state if no file data
    }
  }, [createSession, addSessionToList])

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollAreaRef.current && sessionState.session?.messages) {
      // Use requestAnimationFrame to ensure DOM is updated
      requestAnimationFrame(() => {
        if (scrollAreaRef.current) {
          scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight
        }
      })
    }
  }, [sessionState.session?.messages?.length]) // Use length instead of the array reference

  const handleSendMessage = async (message: string) => {
    try {
      addToast({
        type: 'loading',
        title: 'Generating answer...',
        message: 'This may take 3-8 seconds depending on question complexity'
      });
      
      await askQuestion(message)
      
      // Clear all toasts (including loading) and show success
      clearToasts();
      addToast({
        type: 'success',
        title: 'Answer generated',
        message: 'AI has provided a response to your question'
      });
    } catch (error) {
      console.error("Failed to send message:", error)
      
      // Clear all toasts (including loading) and show error
      clearToasts();
      addToast({
        type: 'error',
        title: 'Failed to get answer',
        message: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  }

  const handleLoadSession = async (sessionId: string) => {
    try {
      addToast({
        type: 'loading',
        title: 'Loading session...',
        message: 'Retrieving your previous conversation'
      });

      await loadSession(sessionId)
      setShowHistory(false)
      
      addToast({
        type: 'success',
        title: 'Session loaded',
        message: 'Your previous conversation has been restored'
      });
    } catch (error) {
      console.error("Failed to load session:", error)
      addToast({
        type: 'error',
        title: 'Failed to load session',
        message: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  }

  const handleDeleteSession = async (sessionId: string) => {
    try {
      await deleteSession(sessionId)
      removeSessionFromList(sessionId)
      setShowHistory(false)
      
      addToast({
        type: 'success',
        title: 'Session deleted',
        message: 'The session has been permanently removed'
      });
    } catch (error) {
      console.error("Failed to delete session:", error)
      addToast({
        type: 'error',
        title: 'Failed to delete session',
        message: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  }

  const handleNewSession = () => {
    resetSession()
    sessionCreatedRef.current = false
    localStorage.removeItem("uploadedFile")
  }

  const handleClearError = () => {
    clearError()
  }

  // Show initial loading state
  if (isInitializing) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loading message="Setting up your Q&A session..." />
      </div>
    )
  }

  // Show loading state while creating session
  if (sessionState.isCreating) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loading message="Setting up your document for questions..." />
      </div>
    )
  }

  // Show error state
  if (sessionState.error && !sessionState.session) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center space-y-4">
          <AlertCircle className="h-16 w-16 text-destructive mx-auto" />
          <h2 className="text-2xl font-bold text-foreground">Session Error</h2>
          <p className="text-destructive max-w-md">{sessionState.error}</p>
          <div className="space-x-2">
            <Button onClick={handleClearError} variant="outline">
              Try Again
            </Button>
            <Link href="/">
              <Button onClick={handleNewSession}>
                New Session
              </Button>
            </Link>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="flex items-center justify-between p-4 border-b border-border">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => setShowMenu(!showMenu)} className="p-2">
            <Menu className="h-5 w-5" />
          </Button>
          <Link href="/">
            <Button variant="ghost" size="sm" className="p-2">
              <ArrowLeft className="h-5 w-5" />
            </Button>
          </Link>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold font-montserrat text-foreground">Q&A Chat</h1>
            {fileName && (
              <div className="flex items-center gap-1 text-sm text-muted-foreground">
                <FileText className="h-3 w-3" />
                <span>{fileName}</span>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Hamburger Menu */}
      {showMenu && (
        <div className="absolute top-16 left-4 z-50 bg-card border border-border rounded-lg shadow-lg p-2 min-w-48">
          <Link href="/" onClick={handleNewSession}>
            <Button variant="ghost" className="w-full justify-start gap-2 text-sm">
              <Plus className="h-4 w-4" />
              New Session
            </Button>
          </Link>
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

      {/* Error Banner */}
      {sessionState.error && (
        <div className="bg-destructive/10 border border-destructive/20 p-3 mx-4 mt-4 rounded-lg">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-destructive" />
              <p className="text-sm text-destructive">{sessionState.error}</p>
            </div>
            <Button variant="ghost" size="sm" onClick={handleClearError}>
              ×
            </Button>
          </div>
        </div>
      )}

      {/* Main Content */}
      <main className="flex flex-col h-[calc(100vh-5rem)]">
        {/* Chat Messages */}
        <ScrollArea className="flex-1 p-4" ref={scrollAreaRef}>
          <div className="max-w-4xl mx-auto space-y-4">
            {sessionState.session?.messages && sessionState.session.messages.length > 0 ? (
              sessionState.session.messages.map((message) => (
                <Message 
                  key={message.id}
                  message={message} 
                  isUser={message.type === "user"} 
                />
              ))
            ) : (
              <div className="text-center py-8">
                <Bot className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-medium text-foreground mb-2">
                  Welcome to Q&A Chat!
                </h3>
                <p className="text-muted-foreground">
                  Ask me any questions about your document and I'll help you understand it better.
                </p>
              </div>
            )}
          </div>
        </ScrollArea>

        {/* Chat Input */}
        <ChatInput
          onSendMessage={handleSendMessage}
          isLoading={sessionState.isAsking}
          disabled={!sessionState.session}
          placeholder="Ask a question about your document..."
        />
      </main>

      {/* Session History Modal */}
      {showHistory && (
        <SessionHistory
          sessions={historyState.sessions}
          isLoading={historyState.isLoading}
          onLoadSession={handleLoadSession}
          onDeleteSession={handleDeleteSession}
          onClose={() => setShowHistory(false)}
        />
      )}
    </div>
  )
}
