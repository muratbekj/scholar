"use client"
import { useState, useEffect } from "react"
import { Menu, History, Plus, ArrowLeft, RotateCcw, AlertCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Loading } from "@/components/ui/loading"
import Link from "next/link"
import { useQuiz } from "@/lib/hooks/useQuiz"
import { QuizRequest, QuizQuestionResponse } from "@/lib/api"

export default function QuizPage() {
  const [showMenu, setShowMenu] = useState(false)
  const [fileName, setFileName] = useState<string>("")
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [selectedAnswers, setSelectedAnswers] = useState<Record<string, string>>({})
  const [showResults, setShowResults] = useState(false)
  const [quizConfig, setQuizConfig] = useState({
    numQuestions: 10,
    difficulty: 'medium' as 'easy' | 'medium' | 'hard',
    questionTypes: ['multiple_choice', 'true_false'] as ('multiple_choice' | 'true_false' | 'short_answer')[]
  })

  const {
    isGenerating,
    isCreatingSession,
    isSubmitting,
    error,
    quiz,
    questions,
    sessionId,
    result,
    generateQuiz,
    createSession,
    getQuestions,
    submitQuiz,
    resetQuiz,
    clearError
  } = useQuiz()

  useEffect(() => {
    // Get uploaded file info from localStorage
    const fileData = localStorage.getItem("uploadedFile")
    if (fileData) {
      const file = JSON.parse(fileData)
      setFileName(file.name)
      
      // Generate quiz automatically when component mounts
      handleGenerateQuiz(file)
    }
  }, [])

  const handleGenerateQuiz = async (file: any) => {
    try {
      clearError()
      
      // Generate quiz
      const quizRequest: QuizRequest = {
        file_id: file.fileId,
        filename: file.name,
        num_questions: quizConfig.numQuestions,
        difficulty: quizConfig.difficulty,
        question_types: quizConfig.questionTypes,
        include_explanations: true
      }
      
      const generatedQuiz = await generateQuiz(quizRequest)
      
      // Get questions
      await getQuestions(generatedQuiz.quiz_id)
      
      // Create session
      await createSession({
        quiz_id: generatedQuiz.quiz_id,
        file_id: file.fileId,
        filename: file.name
      })
      
    } catch (error) {
      console.error('Failed to generate quiz:', error)
    }
  }

  const handleAnswerSelect = (questionId: string, answer: string) => {
    setSelectedAnswers(prev => ({
      ...prev,
      [questionId]: answer
    }))
  }

  const handleNextQuestion = () => {
    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(currentQuestionIndex + 1)
    } else {
      handleSubmitQuiz()
    }
  }

  const handlePreviousQuestion = () => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(currentQuestionIndex - 1)
    }
  }

  const handleSubmitQuiz = async () => {
    if (!sessionId) return
    
    try {
      await submitQuiz({
        session_id: sessionId,
        answers: selectedAnswers
      })
      setShowResults(true)
    } catch (error) {
      console.error('Failed to submit quiz:', error)
    }
  }

  const restartQuiz = () => {
    setCurrentQuestionIndex(0)
    setSelectedAnswers({})
    setShowResults(false)
    resetQuiz()
    
    // Regenerate quiz
    const fileData = localStorage.getItem("uploadedFile")
    if (fileData) {
      const file = JSON.parse(fileData)
      handleGenerateQuiz(file)
    }
  }

  const handleNewSession = () => {
    localStorage.removeItem("uploadedFile")
    resetQuiz()
  }

  // Show loading state while generating quiz
  if (isGenerating || isCreatingSession || questions.length === 0) {
    return (
      <div className="min-h-screen bg-background">
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
            <h1 className="text-xl font-bold font-montserrat text-foreground">Quiz Mode</h1>
          </div>
        </header>

        <div className="flex items-center justify-center h-64">
          <div className="text-center space-y-4">
            <Loading message={isGenerating ? "Generating quiz..." : isCreatingSession ? "Creating session..." : "Loading questions..."} />
            {error && (
              <div className="flex items-center gap-2 text-destructive">
                <AlertCircle className="h-4 w-4" />
                <p>{error}</p>
              </div>
            )}
          </div>
        </div>
      </div>
    )
  }

  if (showResults && result) {
    return (
      <div className="min-h-screen bg-background">
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
            <h1 className="text-xl font-bold font-montserrat text-foreground">Quiz Results</h1>
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

        <main className="p-8">
          <div className="max-w-2xl mx-auto space-y-8">
            <div className="text-center space-y-4">
              <h2 className="text-3xl font-bold font-montserrat text-foreground">Quiz Complete!</h2>
              <div className="space-y-2">
                <p className="text-6xl font-bold text-accent">{Math.round(result.score)}%</p>
                <p className="text-lg text-muted-foreground">
                  You scored {result.correct_answers} out of {result.total_questions} questions correctly
                </p>
                {result.feedback && (
                  <p className="text-sm text-muted-foreground">{result.feedback}</p>
                )}
              </div>
            </div>

            <Card className="p-6 space-y-4">
              <h3 className="text-lg font-semibold font-montserrat">Review Your Answers</h3>
              <div className="space-y-4">
                {result.question_results.map((questionResult, index) => (
                  <div key={questionResult.question_id} className="space-y-2">
                    <p className="font-medium">
                      {index + 1}. {questionResult.question}
                    </p>
                    <div className="pl-4 space-y-1">
                      <p className={`text-sm ${questionResult.is_correct ? "text-green-600" : "text-red-600"}`}>
                        Your answer: {questionResult.user_answer} {questionResult.is_correct ? "✓" : "✗"}
                      </p>
                      {!questionResult.is_correct && (
                        <p className="text-sm text-green-600">
                          Correct answer: {questionResult.correct_answer}
                        </p>
                      )}
                      {questionResult.explanation && (
                        <p className="text-sm text-muted-foreground italic">{questionResult.explanation}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </Card>

            <div className="flex justify-center">
              <Button onClick={restartQuiz} size="lg" className="bg-accent hover:bg-accent/90">
                <RotateCcw className="h-4 w-4 mr-2" />
                Take Quiz Again
              </Button>
            </div>
          </div>
        </main>
      </div>
    )
  }

  const currentQuestion = questions[currentQuestionIndex]
  const selectedAnswer = selectedAnswers[currentQuestion.id]

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
          <h1 className="text-xl font-bold font-montserrat text-foreground">Quiz Mode</h1>
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

      <main className="p-8">
        <div className="max-w-2xl mx-auto space-y-8">
          {/* Progress Bar */}
          <div className="space-y-2">
            <div className="flex justify-between text-sm text-muted-foreground">
              <span>
                Question {currentQuestionIndex + 1} of {questions.length}
              </span>
              <span>{Math.round(((currentQuestionIndex + 1) / questions.length) * 100)}% Complete</span>
            </div>
            <div className="w-full bg-muted rounded-full h-2">
              <div
                className="bg-accent h-2 rounded-full transition-all duration-300"
                style={{ width: `${((currentQuestionIndex + 1) / questions.length) * 100}%` }}
              />
            </div>
          </div>

          {/* Question Card */}
          <Card className="p-8 space-y-6">
            <h2 className="text-xl font-semibold font-montserrat text-foreground">{currentQuestion.question}</h2>

            <div className="space-y-3">
              {currentQuestion.options?.map((option: string, index: number) => (
                <Button
                  key={index}
                  variant={selectedAnswer === option ? "default" : "outline"}
                  className={`w-full text-left justify-start p-4 h-auto ${
                    selectedAnswer === option ? "bg-accent text-accent-foreground" : ""
                  }`}
                  onClick={() => handleAnswerSelect(currentQuestion.id, option)}
                >
                  <span className="mr-3 font-medium">{String.fromCharCode(65 + index)}.</span>
                  {option}
                </Button>
              ))}
            </div>
          </Card>

          {/* Navigation */}
          <div className="flex justify-between">
            <Button variant="outline" onClick={handlePreviousQuestion} disabled={currentQuestionIndex === 0}>
              Previous
            </Button>

            <Button
              onClick={handleNextQuestion}
              disabled={!selectedAnswer}
              className="bg-accent hover:bg-accent/90"
            >
              {currentQuestionIndex === questions.length - 1 ? "Finish Quiz" : "Next Question"}
            </Button>
          </div>
        </div>
      </main>
    </div>
  )
}
