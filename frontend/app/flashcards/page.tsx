"use client"
import { useState, useEffect } from "react"
import { Menu, History, Plus, ArrowLeft, RotateCcw, ChevronLeft, ChevronRight } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import Link from "next/link"
import { useFlashcardGeneration } from "@/lib/hooks/useFlashcardGeneration"
import { Flashcard } from "@/lib/api"

export default function FlashcardsPage() {
  const [showMenu, setShowMenu] = useState(false)
  const [currentFlashcardIndex, setCurrentFlashcardIndex] = useState(0)
  const [isFlipped, setIsFlipped] = useState(false)
  
  const { 
    flashcards, 
    isGenerating, 
    error, 
    generateFlashcards, 
    resetFlashcards, 
    clearError 
  } = useFlashcardGeneration()

  useEffect(() => {
    // Get uploaded file info from localStorage
    const fileData = localStorage.getItem("uploadedFile")
    if (fileData && flashcards.length === 0 && !isGenerating) {
      const file = JSON.parse(fileData)
      
      // Generate flashcards from the uploaded file
      generateFlashcards({
        file_id: file.fileId,
        filename: file.name
      }).catch(console.error)
    }
  }, [flashcards.length, isGenerating, generateFlashcards])

  const handleNextFlashcard = () => {
    if (currentFlashcardIndex < flashcards.length - 1) {
      setCurrentFlashcardIndex(currentFlashcardIndex + 1)
      setIsFlipped(false)
    }
  }

  const handlePreviousFlashcard = () => {
    if (currentFlashcardIndex > 0) {
      setCurrentFlashcardIndex(currentFlashcardIndex - 1)
      setIsFlipped(false)
    }
  }

  const handleFlipCard = () => {
    setIsFlipped(!isFlipped)
  }

  const resetCurrentSession = () => {
    setCurrentFlashcardIndex(0)
    setIsFlipped(false)
  }

  const handleNewSession = () => {
    localStorage.removeItem("uploadedFile")
    resetFlashcards()
  }

  if (isGenerating) {
    return (
      <div className="min-h-screen bg-background flex flex-col">
        <header className="sticky top-0 z-40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 flex items-center justify-between p-4 border-b border-border">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={() => setShowMenu(!showMenu)} className="p-2">
              <Menu className="h-5 w-5" />
            </Button>
            <Link href="/">
              <Button variant="ghost" size="sm" className="p-2">
                <ArrowLeft className="h-5 w-5" />
              </Button>
            </Link>
            <h1 className="text-xl font-bold font-montserrat text-foreground">Flashcards</h1>
          </div>
        </header>

        <div className="flex items-center justify-center h-64">
          <div className="text-center space-y-4">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent mx-auto"></div>
            <p className="text-muted-foreground">Generating flashcards...</p>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background flex flex-col">
        <header className="sticky top-0 z-40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 flex items-center justify-between p-4 border-b border-border">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={() => setShowMenu(!showMenu)} className="p-2">
              <Menu className="h-5 w-5" />
            </Button>
            <Link href="/">
              <Button variant="ghost" size="sm" className="p-2">
                <ArrowLeft className="h-5 w-5" />
              </Button>
            </Link>
            <h1 className="text-xl font-bold font-montserrat text-foreground">Flashcards</h1>
          </div>
        </header>

        <div className="flex items-center justify-center h-64">
          <div className="text-center space-y-4">
            <p className="text-red-500 font-medium">Error generating flashcards</p>
            <p className="text-muted-foreground">{error}</p>
            <Button onClick={clearError} variant="outline">
              Try Again
            </Button>
          </div>
        </div>
      </div>
    )
  }

  if (flashcards.length === 0) {
    return (
      <div className="min-h-screen bg-background flex flex-col">
        <header className="sticky top-0 z-40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 flex items-center justify-between p-4 border-b border-border">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={() => setShowMenu(!showMenu)} className="p-2">
              <Menu className="h-5 w-5" />
            </Button>
            <Link href="/">
              <Button variant="ghost" size="sm" className="p-2">
                <ArrowLeft className="h-5 w-5" />
              </Button>
            </Link>
            <h1 className="text-xl font-bold font-montserrat text-foreground">Flashcards</h1>
          </div>
        </header>

        <div className="flex items-center justify-center h-64">
          <div className="text-center space-y-4">
            <p className="text-muted-foreground">No flashcards available</p>
            <p className="text-sm text-muted-foreground">Upload a document to generate flashcards</p>
          </div>
        </div>
      </div>
    )
  }

  const currentFlashcard = flashcards[currentFlashcardIndex]

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <header className="sticky top-0 z-40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 flex items-center justify-between p-4 border-b border-border">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => setShowMenu(!showMenu)} className="p-2">
            <Menu className="h-5 w-5" />
          </Button>
          <Link href="/">
            <Button variant="ghost" size="sm" className="p-2">
              <ArrowLeft className="h-5 w-5" />
            </Button>
          </Link>
          <h1 className="text-xl font-bold font-montserrat text-foreground">Flashcards</h1>
        </div>
      </header>

      {/* Hamburger Menu */}
      {showMenu && (
        <div className="absolute top-[calc(4rem+1px)] left-4 z-50 bg-card border border-border rounded-lg shadow-lg p-2 min-w-48">
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

      <main className="flex flex-col flex-1 min-h-0 p-12">
        <div className="max-w-6xl mx-auto space-y-12 flex-1 w-full">
          {/* Progress and Controls */}
          <div className="flex items-center justify-between">
            <div className="space-y-2">
              <p className="text-lg text-muted-foreground">
                Card {currentFlashcardIndex + 1} of {flashcards.length}
              </p>
              {currentFlashcard.category && (
                <p className="text-sm text-accent font-medium">{currentFlashcard.category}</p>
              )}
            </div>
            <Button variant="outline" size="lg" onClick={resetCurrentSession}>
              <RotateCcw className="h-5 w-5 mr-2" />
              Reset Session
            </Button>
          </div>

          {/* Progress Bar */}
          <div className="w-full space-y-3">
            <div className="flex items-center justify-between text-sm text-muted-foreground">
              <span>Progress</span>
              <span>{Math.round(((currentFlashcardIndex + 1) / flashcards.length) * 100)}%</span>
            </div>
            <div className="w-full bg-muted rounded-full h-4 overflow-hidden shadow-inner">
              <div
                className="bg-gradient-to-r from-blue-500 via-blue-600 to-blue-700 h-4 rounded-full transition-all duration-700 ease-out shadow-sm relative overflow-hidden"
                style={{ width: `${((currentFlashcardIndex + 1) / flashcards.length) * 100}%` }}
              >
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-[shimmer_2s_ease-in-out_infinite]" />
              </div>
            </div>
          </div>

          {/* Flashcard Container */}
          <div className="flex-1 flex items-center justify-center min-h-[600px]">
            <div className="relative w-full max-w-4xl h-[500px]">
              <Card
                className={`absolute inset-0 cursor-pointer transition-all duration-500 transform-gpu shadow-xl hover:shadow-2xl ${
                  isFlipped ? "rotate-y-180" : ""
                }`}
                onClick={handleFlipCard}
                style={{
                  transformStyle: "preserve-3d",
                  backfaceVisibility: "hidden",
                }}
              >
                {/* Front of card */}
                <div
                  className={`absolute inset-0 p-16 flex flex-col items-center justify-center text-center space-y-8 ${
                    isFlipped ? "opacity-0" : "opacity-100"
                  }`}
                  style={{
                    backfaceVisibility: "hidden",
                  }}
                >
                  <div className="space-y-6 max-w-2xl">
                    <p className="text-lg text-muted-foreground uppercase tracking-wide font-medium">Question</p>
                    <h2 className="text-3xl font-semibold font-montserrat text-foreground leading-relaxed">
                      {currentFlashcard.front}
                    </h2>
                  </div>
                  <p className="text-base text-muted-foreground mt-12">Click to reveal answer</p>
                </div>

                {/* Back of card */}
                <div
                  className={`absolute inset-0 p-16 flex flex-col items-center justify-center text-center space-y-8 ${
                    isFlipped ? "opacity-100" : "opacity-0"
                  }`}
                  style={{
                    backfaceVisibility: "hidden",
                    transform: "rotateY(180deg)",
                  }}
                >
                  <div className="space-y-6 max-w-3xl">
                    <p className="text-lg text-accent uppercase tracking-wide font-medium">Answer</p>
                    <p className="text-2xl text-foreground leading-relaxed">{currentFlashcard.back}</p>
                  </div>
                  <p className="text-base text-muted-foreground mt-12">Click to see question</p>
                </div>
              </Card>
            </div>
          </div>

          {/* Study Stats */}
          <Card className="p-8">
            <div className="flex items-center justify-between text-lg">
              <div className="text-center">
                <p className="text-2xl font-bold text-foreground">{flashcards.length}</p>
                <p className="text-muted-foreground">Total Cards</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-foreground">{currentFlashcardIndex + 1}</p>
                <p className="text-muted-foreground">Current</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-foreground">{flashcards.length - currentFlashcardIndex - 1}</p>
                <p className="text-muted-foreground">Remaining</p>
              </div>
            </div>
          </Card>
        </div>
      </main>

      {/* Sticky Navigation */}
      <div className="sticky bottom-0 z-40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 border-t border-border">
        <div className="p-12 pt-6">
          <div className="max-w-6xl mx-auto">
            <div className="flex items-center justify-between">
              <Button
                variant="outline"
                size="lg"
                onClick={handlePreviousFlashcard}
                disabled={currentFlashcardIndex === 0}
                className="flex items-center gap-3 bg-transparent px-8 py-3"
              >
                <ChevronLeft className="h-5 w-5" />
                Previous
              </Button>

              <div className="flex items-center gap-4">
                <Button
                  variant={isFlipped ? "outline" : "default"}
                  size="lg"
                  onClick={handleFlipCard}
                  className="bg-accent hover:bg-accent/90 px-8 py-3 text-lg"
                >
                  {isFlipped ? "Show Question" : "Show Answer"}
                </Button>
              </div>

              <Button
                variant="outline"
                size="lg"
                onClick={handleNextFlashcard}
                disabled={currentFlashcardIndex === flashcards.length - 1}
                className="flex items-center gap-3 bg-transparent px-8 py-3"
              >
                Next
                <ChevronRight className="h-5 w-5" />
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
