"use client"
import { useState, useEffect } from "react"
import { Menu, History, Plus, Send, ArrowLeft, User, Bot } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import Link from "next/link"

interface Message {
  id: string
  type: "user" | "assistant"
  content: string
  timestamp: Date
}

export default function QAPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [inputMessage, setInputMessage] = useState("")
  const [showMenu, setShowMenu] = useState(false)
  const [fileName, setFileName] = useState<string>("")

  useEffect(() => {
    // Get uploaded file info from localStorage
    const fileData = localStorage.getItem("uploadedFile")
    if (fileData) {
      const file = JSON.parse(fileData)
      setFileName(file.name)

      // Initialize with welcome message
      setMessages([
        {
          id: "1",
          type: "assistant",
          content: `Hi! I've analyzed your document "${file.name}". Ask me any questions about its content and I'll help you understand it better.`,
          timestamp: new Date(),
        },
      ])
    }
  }, [])

  const handleSendMessage = () => {
    if (!inputMessage.trim()) return

    const userMessage: Message = {
      id: Date.now().toString(),
      type: "user",
      content: inputMessage,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInputMessage("")

    setTimeout(() => {
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: "assistant",
        content: `I understand you're asking about "${inputMessage}". Based on your document, here's what I can tell you... (This would be connected to your FastAPI backend for real AI responses)`,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, assistantMessage])
    }, 1000)
  }

  const handleNewSession = () => {
    localStorage.removeItem("uploadedFile")
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
          <h1 className="text-xl font-bold font-montserrat text-foreground">Q&A Chat</h1>
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
          <Button variant="ghost" className="w-full justify-start gap-2 text-sm">
            <History className="h-4 w-4" />
            History
          </Button>
        </div>
      )}

      {/* Main Content */}
      <main className="flex flex-col h-[calc(100vh-5rem)]">
        {/* Chat Messages */}
        <ScrollArea className="flex-1 p-4">
          <div className="max-w-4xl mx-auto space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex gap-3 ${message.type === "user" ? "justify-end" : "justify-start"}`}
              >
                {message.type === "assistant" && (
                  <div className="flex-shrink-0 w-8 h-8 bg-accent rounded-full flex items-center justify-center">
                    <Bot className="h-4 w-4 text-accent-foreground" />
                  </div>
                )}
                <div
                  className={`max-w-[70%] p-4 rounded-lg ${
                    message.type === "user"
                      ? "bg-accent text-accent-foreground"
                      : "bg-card text-card-foreground border border-border"
                  }`}
                >
                  <p className="text-sm leading-relaxed">{message.content}</p>
                  <p className="text-xs opacity-60 mt-2">
                    {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </p>
                </div>
                {message.type === "user" && (
                  <div className="flex-shrink-0 w-8 h-8 bg-muted rounded-full flex items-center justify-center">
                    <User className="h-4 w-4 text-muted-foreground" />
                  </div>
                )}
              </div>
            ))}
          </div>
        </ScrollArea>

        {/* Input Area */}
        <div className="border-t border-border p-4">
          <div className="max-w-4xl mx-auto flex gap-2">
            <Input
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder="Ask a question about your document..."
              className="flex-1"
              onKeyPress={(e) => e.key === "Enter" && handleSendMessage()}
            />
            <Button onClick={handleSendMessage} size="sm" className="px-4">
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </main>
    </div>
  )
}
