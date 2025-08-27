# LLM service for generating answers using Ollama models
from langchain_ollama import OllamaLLM
from typing import Dict, Any, Optional, List
import logging
import asyncio
import json

logger = logging.getLogger(__name__)

class LLMService:
    """Service for generating answers using Ollama LLM models"""
    
    def __init__(self, model_name: str = "gpt-oss:20b", 
                 temperature: float = 0.7,
                 max_tokens: int = 2048):
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.llm = OllamaLLM(
            model=model_name,
            temperature=temperature
        )
        logger.info(f"Initialized LLM service with model: {model_name}")
    
    async def generate_answer(self, 
                            question: str, 
                            context: str,
                            system_prompt: Optional[str] = None) -> str:
        """Generate an answer using the LLM with RAG context"""
        try:
            # Default system prompt for QA
            if not system_prompt:
                system_prompt = """You are a helpful AI assistant that answers questions based on the provided document context. 
                
Guidelines:
1. Answer the question using ONLY the information provided in the context
2. If the context doesn't contain enough information to answer the question, say so clearly
3. Be concise but comprehensive
4. Cite specific parts of the context when relevant
5. If the question is not related to the document content, politely redirect to the document topic

Context: {context}

Question: {question}

Answer:"""

            # Format the prompt
            prompt = system_prompt.format(
                context=context,
                question=question
            )
            
            # Generate response
            response = await self._generate_response(prompt)
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating LLM answer: {str(e)}")
            return f"I apologize, but I encountered an error while generating an answer: {str(e)}"
    
    async def generate_summary(self, content: str, max_length: int = 500) -> str:
        """Generate a summary of the provided content"""
        try:
            prompt = f"""Please provide a concise summary of the following content in {max_length} words or less:

{content}

Summary:"""
            
            response = await self._generate_response(prompt)
            return response
            
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return f"Error generating summary: {str(e)}"
    
    async def generate_questions(self, content: str, num_questions: int = 5) -> List[str]:
        """Generate questions based on the content"""
        try:
            prompt = f"""Based on the following content, generate {num_questions} relevant questions that could be asked about this material:

{content}

Questions:
1."""
            
            response = await self._generate_response(prompt)
            
            # Parse the response to extract questions
            questions = []
            lines = response.split('\n')
            for line in lines:
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('Q:')):
                    # Remove numbering and clean up
                    question = line.split('.', 1)[-1].strip()
                    if question.startswith('Q:'):
                        question = question[2:].strip()
                    if question:
                        questions.append(question)
            
            return questions[:num_questions]
            
        except Exception as e:
            logger.error(f"Error generating questions: {str(e)}")
            return [f"Error generating questions: {str(e)}"]
    
    async def generate_quiz_questions(self, 
                                    content: str, 
                                    num_questions: int, 
                                    difficulty: str,
                                    question_types: List[str],
                                    include_explanations: bool = True) -> List[Dict[str, Any]]:
        """Generate structured quiz questions with answers and explanations"""
        try:
            # Create a structured prompt for quiz generation
            question_types_str = ", ".join(question_types)
            explanations_str = "with explanations" if include_explanations else "without explanations"
            
            prompt = f"""Based on the following content, generate {num_questions} quiz questions at {difficulty} difficulty level.
            
Question types to include: {question_types_str}
Include explanations: {explanations_str}

For each question, provide:
1. A clear, well-formatted question
2. For multiple choice: 4 options (A, B, C, D) with one correct answer
3. For true/false: just "True" or "False" as options
4. The correct answer
5. A brief explanation of why the answer is correct

Content:
{content}

Generate the questions in this exact JSON format:
[
  {{
    "question": "What is the main topic discussed in this document?",
    "type": "multiple_choice",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct_answer": "Option A",
    "explanation": "This is correct because..."
  }}
]

Questions:"""
            
            response = await self._generate_response(prompt)
            
            # Parse JSON response
            try:
                # Extract JSON from response (handle potential text before/after JSON)
                start_idx = response.find('[')
                end_idx = response.rfind(']') + 1
                if start_idx != -1 and end_idx != -1:
                    json_str = response[start_idx:end_idx]
                    questions_data = json.loads(json_str)
                else:
                    raise ValueError("No valid JSON found in response")
                
                # Validate and clean up questions
                validated_questions = []
                for q in questions_data[:num_questions]:
                    if self._validate_question_format(q):
                        validated_questions.append(q)
                
                return validated_questions
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Error parsing quiz questions JSON: {str(e)}")
                # Fallback: generate simple questions
                return self._generate_fallback_questions(content, num_questions, question_types)
            
        except Exception as e:
            logger.error(f"Error generating quiz questions: {str(e)}")
            return self._generate_fallback_questions(content, num_questions, question_types)
    
    def _validate_question_format(self, question: Dict[str, Any]) -> bool:
        """Validate that a question has the required format"""
        required_fields = ["question", "type", "correct_answer"]
        
        for field in required_fields:
            if field not in question or not question[field]:
                return False
        
        # Validate question type
        valid_types = ["multiple_choice", "true_false", "short_answer"]
        if question["type"] not in valid_types:
            return False
        
        # Validate multiple choice questions have options
        if question["type"] == "multiple_choice":
            if "options" not in question or not question["options"] or len(question["options"]) < 2:
                return False
        
        return True
    
    def _generate_fallback_questions(self, content: str, num_questions: int, question_types: List[str]) -> List[Dict[str, Any]]:
        """Generate simple fallback questions when LLM generation fails"""
        questions = []
        
        # Simple questions based on content
        simple_questions = [
            "What is the main topic of this document?",
            "What are the key points discussed?",
            "What is the purpose of this material?",
            "What are the main conclusions?",
            "What important information is presented?"
        ]
        
        for i in range(min(num_questions, len(simple_questions))):
            question_type = question_types[i % len(question_types)] if question_types else "multiple_choice"
            
            if question_type == "multiple_choice":
                questions.append({
                    "question": simple_questions[i],
                    "type": "multiple_choice",
                    "options": ["Option A", "Option B", "Option C", "Option D"],
                    "correct_answer": "Option A",
                    "explanation": "This is the correct answer based on the document content."
                })
            elif question_type == "true_false":
                questions.append({
                    "question": simple_questions[i],
                    "type": "true_false",
                    "options": ["True", "False"],
                    "correct_answer": "True",
                    "explanation": "This statement is true based on the document content."
                })
            else:  # short_answer
                questions.append({
                    "question": simple_questions[i],
                    "type": "short_answer",
                    "correct_answer": "Answer based on document content",
                    "explanation": "The answer should be based on the information provided in the document."
                })
        
        return questions
    
    async def _generate_response(self, prompt: str) -> str:
        """Generate a response using the LLM"""
        try:
            # Use asyncio to run the synchronous LLM call
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: self.llm.invoke(prompt)
            )
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error in LLM response generation: {str(e)}")
            raise
    
    async def validate_model(self) -> Dict[str, Any]:
        """Validate that the LLM model is working correctly"""
        try:
            test_prompt = "Hello, can you respond with 'Model is working'?"
            response = await self._generate_response(test_prompt)
            
            return {
                "status": "healthy",
                "model_name": self.model_name,
                "response": response,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }
            
        except Exception as e:
            return {
                "status": "error",
                "model_name": self.model_name,
                "error": str(e)
            }

# Initialize global LLM service
llm_service = LLMService()
