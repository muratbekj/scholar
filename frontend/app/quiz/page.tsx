"use client"
import { useState, useEffect, useCallback, useRef } from "react"
import { Menu, History, Plus, ArrowLeft, RotateCcw, AlertCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Loading } from "@/components/ui/loading"
import { Textarea } from "@/components/ui/textarea"
import Link from "next/link"
import { useQuiz } from "@/lib/hooks/useQuiz"
import { QuizRequest, QuizMode } from "@/lib/api"

export default function QuizPage() {
  const [showMenu, setShowMenu] = useState(false)
  const [fileName, setFileName] = useState<string>("")
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [selectedAnswers, setSelectedAnswers] = useState<Record<string, string>>({})
  const [showResults, setShowResults] = useState(false)
  const [quizConfig, setQuizConfig] = useState({
    numQuestions: 10,
    difficulty: 'medium' as 'easy' | 'medium' | 'hard',
    questionTypes: ['multiple_choice', 'true_false'] as ('multiple_choice' | 'true_false' | 'short_answer')[],
    mode: 'standard' as QuizMode,
  })

  const {
    isGenerating,
    isCreatingSession,
    isSubmitting,
    error,
    questions,
    sessionId,
    result,
    generateQuiz,
    createSession,
    getQuestions,
    submitQuiz,
    resetQuiz,
    clearError,
  } = useQuiz()

  const quizConfigRef = useRef(quizConfig)
  quizConfigRef.current = quizConfig

  const fetchQuizForFile = useCallback(
    async (file: { fileId: string; name: string }) => {
      try {
        clearError()
        const cfg = quizConfigRef.current
        const isStandard = cfg.mode === "standard"
        const quizRequest: QuizRequest = {
          file_id: file.fileId,
          filename: file.name,
          num_questions: cfg.numQuestions,
          difficulty: cfg.difficulty,
          question_types: isStandard ? cfg.questionTypes : ["short_answer"],
          include_explanations: true,
          mode: cfg.mode,
        }

        const generatedQuiz = await generateQuiz(quizRequest)

        await getQuestions(generatedQuiz.quiz_id)

        await createSession({
          quiz_id: generatedQuiz.quiz_id,
          file_id: file.fileId,
          filename: file.name,
        })
      } catch (err) {
        console.error("Failed to generate quiz:", err)
      }
    },
    [clearError, generateQuiz, getQuestions, createSession]
  )

  useEffect(() => {
    const fileData = localStorage.getItem("uploadedFile")
    if (fileData) {
      const file = JSON.parse(fileData)
      setFileName(file.name)
      fetchQuizForFile({ fileId: file.fileId, name: file.name })
    }
  }, [fetchQuizForFile])

  const regenerateQuiz = async () => {
    const fileData = localStorage.getItem("uploadedFile")
    if (!fileData) return
    setCurrentQuestionIndex(0)
    setSelectedAnswers({})
    setShowResults(false)
    resetQuiz()
    clearError()
    const file = JSON.parse(fileData)
    await fetchQuizForFile({ fileId: file.fileId, name: file.name })
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
    const fileData = localStorage.getItem("uploadedFile")
    if (fileData) {
      const file = JSON.parse(fileData)
      void fetchQuizForFile({ fileId: file.fileId, name: file.name })
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
            <Loading
              message={
                isGenerating
                  ? "Generating quiz..."
                  : isCreatingSession
                    ? "Creating session..."
                    : "Loading questions..."
              }
            />
            {error && (
              <div className="flex flex-col items-center gap-3 text-destructive max-w-md">
                <div className="flex items-center gap-2">
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  <p className="text-sm text-center">{error}</p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    const fileData = localStorage.getItem("uploadedFile")
                    if (fileData) {
                      const file = JSON.parse(fileData)
                      void fetchQuizForFile({ fileId: file.fileId, name: file.name })
                    }
                  }}
                >
                  Retry
                </Button>
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
                    <div className="pl-4 space-y-2">
                      <p
                        className={`text-sm ${questionResult.is_correct ? "text-green-600 dark:text-green-500" : "text-red-600 dark:text-red-500"}`}
                      >
                        Your answer: {questionResult.user_answer}{" "}
                        {questionResult.is_correct ? "✓" : "✗"}
                      </p>
                      {questionResult.review_note ? (
                        <p className="text-sm text-foreground border-l-2 border-accent pl-2">
                          {questionResult.review_note}
                        </p>
                      ) : null}
                      {questionResult.human_agency_bonus_applied ? (
                        <p className="text-xs font-medium text-emerald-700 dark:text-emerald-400">
                          Human agency boost: page-specific citation recognized.
                        </p>
                      ) : null}
                      {questionResult.review_details?.length ? (
                        <ul className="text-xs text-muted-foreground list-disc list-inside space-y-0.5">
                          {questionResult.review_details.map((line, i) => (
                            <li key={i}>{line}</li>
                          ))}
                        </ul>
                      ) : null}
                      {!questionResult.is_correct &&
                        questionResult.mode !== "ai_oversight" &&
                        questionResult.mode !== "reasoning_gap" && (
                          <p className="text-sm text-green-600 dark:text-green-500">
                            Correct answer: {questionResult.correct_answer}
                          </p>
                        )}
                      {questionResult.explanation ? (
                        <p className="text-sm text-muted-foreground italic">{questionResult.explanation}</p>
                      ) : null}
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
  const needsTextAnswer =
    currentQuestion.question_type === "short_answer" ||
    currentQuestion.mode === "reasoning_gap" ||
    currentQuestion.mode === "ai_oversight"
  const canProceed = needsTextAnswer ? !!selectedAnswer?.trim() : !!selectedAnswer

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
          <div className="flex flex-col sm:flex-row sm:items-center gap-2">
            <h1 className="text-xl font-bold font-montserrat text-foreground">Quiz Mode</h1>
            {fileName ? (
              <span className="text-xs text-muted-foreground truncate max-w-[10rem] sm:max-w-xs">
                {fileName}
              </span>
            ) : null}
          </div>
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

      <main className="flex flex-col flex-1 min-h-0 p-8 pb-0">
        <div className="max-w-2xl mx-auto space-y-8 flex-1">
          <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3 rounded-lg border border-border bg-muted/20 p-3">
            <div className="space-y-1">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                Quiz type
              </label>
              <select
                value={quizConfig.mode}
                onChange={(e) =>
                  setQuizConfig((c) => ({ ...c, mode: e.target.value as QuizMode }))
                }
                className="w-full sm:w-auto rounded-md border border-border bg-background px-2 py-1.5 text-sm"
              >
                <option value="standard">Standard (MC / T-F)</option>
                <option value="reasoning_gap">Reasoning gaps</option>
                <option value="ai_oversight">AI oversight (you audit the model)</option>
              </select>
            </div>
            <Button variant="secondary" size="sm" onClick={() => void regenerateQuiz()}>
              New quiz with this type
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            <strong>AI oversight</strong> trains critical review: spot weak claims vs the excerpt.{" "}
            <strong>Reasoning gaps</strong> ask you to supply missing bridges from the text.
          </p>

          {/* Progress Bar */}
          <div className="space-y-2">
            <div className="flex justify-between text-sm text-muted-foreground">
              <span>
                Question {currentQuestionIndex + 1} of {questions.length}
              </span>
              <span>{Math.round(((currentQuestionIndex + 1) / questions.length) * 100)}% Complete</span>
            </div>
            <div className="w-full bg-muted rounded-full h-3 overflow-hidden shadow-inner">
              <div
                className="bg-gradient-to-r from-green-500 via-green-600 to-green-700 h-3 rounded-full transition-all duration-500 ease-out shadow-sm relative overflow-hidden"
                style={{ width: `${((currentQuestionIndex + 1) / questions.length) * 100}%` }}
              >
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-[shimmer_2s_ease-in-out_infinite]" />
              </div>
            </div>
          </div>

          {/* Question Card */}
          <Card className="p-8 space-y-6">
            <h2 className="text-xl font-semibold font-montserrat text-foreground">{currentQuestion.question}</h2>

            {needsTextAnswer ? (
              <div className="space-y-4">
                {currentQuestion.mode === "ai_oversight" && currentQuestion.prior_ai_answer ? (
                  <div className="rounded-md border border-amber-500/35 bg-amber-500/5 p-3 text-sm space-y-1">
                    <p className="text-xs font-semibold text-amber-900 dark:text-amber-200 uppercase">
                      Prior AI answer — your job is to critique it
                    </p>
                    <p className="whitespace-pre-wrap text-foreground/90">{currentQuestion.prior_ai_answer}</p>
                  </div>
                ) : null}

                {currentQuestion.gap_prompt ? (
                  <p className="text-base font-medium leading-relaxed">{currentQuestion.gap_prompt}</p>
                ) : null}

                {currentQuestion.gap_steps && currentQuestion.gap_steps.length > 0 ? (
                  <ol className="list-decimal list-inside text-sm text-muted-foreground space-y-2">
                    {currentQuestion.gap_steps.map((s) => (
                      <li key={s.order}>{s.prompt}</li>
                    ))}
                  </ol>
                ) : null}

                {currentQuestion.review_guidance ? (
                  <p className="text-xs text-muted-foreground">{currentQuestion.review_guidance}</p>
                ) : null}

                {currentQuestion.grading_rubric && currentQuestion.grading_rubric.length > 0 ? (
                  <div className="text-xs text-muted-foreground space-y-1">
                    <span className="font-medium text-foreground">Rubric:</span>
                    <ul className="list-disc list-inside">
                      {currentQuestion.grading_rubric.map((r, i) => (
                        <li key={i}>{r}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}

                {currentQuestion.evidence_refs?.[0]?.excerpt ? (
                  <div className="text-xs border-l-2 border-border pl-3 py-1 text-muted-foreground bg-muted/30 rounded-r">
                    <span className="font-medium text-foreground">Evidence: </span>
                    {currentQuestion.evidence_refs[0].excerpt}
                  </div>
                ) : null}

                <Textarea
                  value={selectedAnswer || ""}
                  onChange={(e) => handleAnswerSelect(currentQuestion.id, e.target.value)}
                  placeholder={
                    currentQuestion.mode === "ai_oversight"
                      ? "Describe the flaw and tie it to the excerpt (quote or paraphrase)…"
                      : "Fill the missing reasoning in your own words…"
                  }
                  className="min-h-[120px]"
                  aria-label="Quiz short answer"
                />
              </div>
            ) : (
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
            )}
          </Card>
        </div>
      </main>

      {/* Sticky Navigation */}
      <div className="sticky bottom-0 z-40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 border-t border-border">
        <div className="p-8 pt-4">
          <div className="max-w-2xl mx-auto">
            <div className="flex justify-between">
              <Button variant="outline" onClick={handlePreviousQuestion} disabled={currentQuestionIndex === 0}>
                Previous
              </Button>

              <Button
                onClick={handleNextQuestion}
                disabled={!canProceed || isSubmitting}
                className="bg-accent hover:bg-accent/90"
              >
                {currentQuestionIndex === questions.length - 1 ? "Finish Quiz" : "Next Question"}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
