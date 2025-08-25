# LLM service for generating answers using Ollama models
from langchain_ollama import OllamaLLM
from typing import Dict, Any, Optional, List
import logging
import asyncio

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
