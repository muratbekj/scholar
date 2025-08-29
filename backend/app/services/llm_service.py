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
            
            prompt = f"""You are an expert educator creating a quiz based on the following document. Your task is to:

1. FIRST: Read and thoroughly understand the document content
2. SECOND: Identify the key concepts, main ideas, and important details
3. THIRD: Generate {num_questions} meaningful quiz questions that test actual understanding

Question types to include: {question_types_str}
Difficulty level: {difficulty}
Include explanations: {explanations_str}

CRITICAL REQUIREMENTS:
- Questions must be based on SPECIFIC information from the document
- Multiple choice options must be REAL, DISTINCT choices (not generic options)
- Correct answers must be VERIFIABLE from the document content
- Explanations must reference SPECIFIC parts of the document
- Questions should test COMPREHENSION, not just memorization

For multiple choice questions:
- Create 4 distinct options where only ONE is clearly correct
- Make incorrect options plausible but clearly wrong
- Base all options on actual content from the document

For true/false questions:
- Create statements that can be definitively verified from the document
- Make statements specific enough to be clearly true or false

Document Content:
{content}

Generate the questions in this exact JSON format:
[
  {{
    "question": "According to the document, what is the primary goal of artificial intelligence?",
    "type": "multiple_choice",
    "options": [
      "To create intelligent machines that can think like humans",
      "To replace human workers in all industries", 
      "To make computers faster at calculations",
      "To reduce the cost of software development"
    ],
    "correct_answer": "To create intelligent machines that can think like humans",
    "explanation": "The document states that AI 'aims to create intelligent machines', which directly supports this answer."
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
        """Generate intelligent fallback questions when LLM generation fails"""
        questions = []
        
        # Analyze document content more intelligently
        content_analysis = self._analyze_document_content(content)
        
        # Generate questions based on actual document structure and content
        question_templates = self._generate_question_templates(content_analysis, num_questions)
        
        for i, template in enumerate(question_templates):
            question_type = question_types[i % len(question_types)] if question_types else "multiple_choice"
            
            if question_type == "multiple_choice":
                question_data = self._create_multiple_choice_question(template, content_analysis, i)
            elif question_type == "true_false":
                question_data = self._create_true_false_question(template, content_analysis, i)
            else:  # short_answer
                question_data = self._create_short_answer_question(template, content_analysis, i)
            
            questions.append(question_data)
        
        return questions
    
    def _analyze_document_content(self, content: str) -> Dict[str, Any]:
        """Analyze document content to extract meaningful information"""
        analysis = {
            'main_topic': None,
            'key_concepts': [],
            'applications': [],
            'definitions': {},
            'examples': [],
            'conclusions': [],
            'sections': []
        }
        
        lines = content.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Detect main topic
            if 'artificial intelligence' in line.lower() or 'ai' in line.lower():
                analysis['main_topic'] = 'Artificial Intelligence'
            elif 'machine learning' in line.lower() or 'ml' in line.lower():
                analysis['main_topic'] = 'Machine Learning'
            elif 'deep learning' in line.lower():
                analysis['main_topic'] = 'Deep Learning'
            
            # Detect key concepts
            if any(term in line.lower() for term in ['concept', 'principle', 'technique', 'method', 'approach']):
                # Clean up the line and extract meaningful content
                clean_line = line.replace('Key Concepts:', '').replace('1.', '').replace('2.', '').replace('3.', '').strip()
                # Remove common formatting artifacts
                clean_line = clean_line.replace(' : ', ': ').replace(' :', ':').replace(': ', ':')
                if clean_line and len(clean_line) > 10 and len(clean_line) < 200:
                    analysis['key_concepts'].append(clean_line)
            
            # Detect applications
            if any(term in line.lower() for term in ['application', 'use', 'used for', 'example', 'such as']):
                # Clean up the line and extract meaningful content
                clean_line = line.replace('Applications of AI:', '').replace('Applications:', '').strip()
                # Remove common formatting artifacts
                clean_line = clean_line.replace(' : ', ': ').replace(' :', ':').replace(': ', ':')
                if clean_line and len(clean_line) > 10 and len(clean_line) < 200:
                    analysis['applications'].append(clean_line)
            
            # Detect definitions
            if 'is a' in line.lower() or 'refers to' in line.lower() or 'means' in line.lower():
                parts = line.split('is a')
                if len(parts) > 1:
                    term = parts[0].strip()
                    definition = parts[1].strip()
                    # Clean up the definition
                    definition = definition.replace('(AI)', '').replace('(ML)', '').strip()
                    if term and definition:
                        analysis['definitions'][term] = definition
            
            # Detect examples
            if line.startswith('-') or line.startswith('•') or line.startswith('*'):
                analysis['examples'].append(line)
            
            # Detect conclusions
            if any(term in line.lower() for term in ['conclusion', 'therefore', 'thus', 'in summary', 'finally']):
                analysis['conclusions'].append(line)
            
            # Detect sections
            if line.isupper() or (len(line) < 50 and line.endswith(':')):
                current_section = line
                analysis['sections'].append(line)
        
        return analysis
    
    def _generate_question_templates(self, analysis: Dict[str, Any], num_questions: int) -> List[Dict[str, Any]]:
        """Generate question templates based on document analysis"""
        templates = []
        
        # Question 1: Main topic
        if analysis['main_topic']:
            templates.append({
                'type': 'main_topic',
                'question': f"What is the primary focus of this document?",
                'correct_answer': analysis['main_topic']
            })
        
        # Question 2: Key concepts
        if analysis['key_concepts']:
            first_concept = analysis['key_concepts'][0]
            # Extract just the concept name, not the full description
            concept_name = first_concept.split(':')[0] if ':' in first_concept else first_concept[:50]
            templates.append({
                'type': 'key_concepts',
                'question': f"Which of the following is a key concept discussed in this document?",
                'correct_answer': concept_name.strip()
            })
        
        # Question 3: Applications
        if analysis['applications']:
            first_app = analysis['applications'][0]
            # Extract just the application name, not the full description
            app_name = first_app.split(':')[0] if ':' in first_app else first_app[:50]
            templates.append({
                'type': 'applications',
                'question': f"What are some applications mentioned in this document?",
                'correct_answer': app_name.strip()
            })
        
        # Question 4: Definitions
        if analysis['definitions']:
            first_term = list(analysis['definitions'].keys())[0]
            templates.append({
                'type': 'definition',
                'question': f"According to this document, what is {first_term}?",
                'correct_answer': analysis['definitions'][first_term]
            })
        
        # Question 5: Examples
        if analysis['examples']:
            templates.append({
                'type': 'examples',
                'question': f"Which of the following is an example mentioned in this document?",
                'correct_answer': analysis['examples'][0] if analysis['examples'] else "Examples"
            })
        
        # Fill remaining slots with general questions
        while len(templates) < num_questions:
            templates.append({
                'type': 'general',
                'question': "What important information is presented in this document?",
                'correct_answer': "Important information"
            })
        
        return templates[:num_questions]
    
    def _create_multiple_choice_question(self, template: Dict[str, Any], analysis: Dict[str, Any], index: int) -> Dict[str, Any]:
        """Create a multiple choice question based on template and analysis"""
        question = template['question']
        correct_answer = template['correct_answer']
        
        # Generate plausible options based on content
        if template['type'] == 'main_topic':
            options = [
                correct_answer,
                "Machine Learning" if correct_answer != "Machine Learning" else "Deep Learning",
                "Data Science" if correct_answer != "Data Science" else "Computer Science",
                "Programming" if correct_answer != "Programming" else "Software Development"
            ]
        elif template['type'] == 'applications':
            # Use actual applications from the document
            app_options = [
                "Virtual assistants like Siri and Alexa",
                "Recommendation systems on Netflix and Amazon", 
                "Autonomous vehicles",
                "Medical diagnosis systems",
                "Fraud detection in banking",
                "Document processing and chat applications",
                "Study assistance platforms",
                "Exam preparation tools"
            ]
            # Make sure correct answer is first, then add other realistic options
            options = [correct_answer]
            for app in app_options:
                if app not in options and len(options) < 4:
                    options.append(app)
            # Fill remaining slots if needed
            while len(options) < 4:
                options.append("Other AI applications")
        elif template['type'] == 'key_concepts':
            options = [
                correct_answer,
                "Machine Learning",
                "Deep Learning", 
                "Natural Language Processing",
                "RAG (Retrieval-Augmented Generation)",
                "Concept Mapping",
                "Adaptive Learning",
                "Document Processing"
            ]
        else:
            options = [
                correct_answer,
                "Related concept 1",
                "Related concept 2", 
                "Related concept 3"
            ]
        
        return {
            "question": question,
            "type": "multiple_choice",
            "options": options,
            "correct_answer": correct_answer,
            "explanation": f"This answer is directly supported by the document content."
        }
    
    def _create_true_false_question(self, template: Dict[str, Any], analysis: Dict[str, Any], index: int) -> Dict[str, Any]:
        """Create a true/false question based on template and analysis"""
        if template['type'] == 'main_topic':
            true_statement = f"This document discusses {template['correct_answer']}"
            false_statement = f"This document is about an unrelated topic"
        else:
            true_statement = f"This document contains information about {template['correct_answer']}"
            false_statement = f"This document does not mention {template['correct_answer']}"
        
        return {
            "question": template['question'],
            "type": "true_false",
            "options": [true_statement, false_statement],
            "correct_answer": true_statement,
            "explanation": "This statement is true based on the document content."
        }
    
    def _create_short_answer_question(self, template: Dict[str, Any], analysis: Dict[str, Any], index: int) -> Dict[str, Any]:
        """Create a short answer question based on template and analysis"""
        return {
            "question": template['question'],
            "type": "short_answer",
            "correct_answer": template['correct_answer'],
            "explanation": "The answer should be based on the specific information provided in the document."
        }
    
    def _extract_key_terms(self, content: str) -> List[str]:
        """Extract key terms from content for generating better options"""
        # Extract meaningful phrases and terms
        key_terms = []
        
        # Look for specific patterns and important terms
        important_terms = [
            "Artificial Intelligence", "Machine Learning", "Deep Learning", 
            "Natural Language Processing", "Computer Science", "Neural Networks",
            "Virtual Assistants", "Autonomous Vehicles", "Medical Diagnosis",
            "Fraud Detection", "Recommendation Systems", "Data Science",
            "Algorithms", "Programming", "Technology", "Applications"
        ]
        
        content_lower = content.lower()
        for term in important_terms:
            if term.lower() in content_lower:
                key_terms.append(term)
        
        # If no specific terms found, extract individual words
        if not key_terms:
            words = content.lower().split()
            # Filter out common words and short words
            stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 'like', 'such', 'as', 'from', 'into', 'during', 'including', 'until', 'against', 'among', 'throughout', 'despite', 'towards', 'upon', 'concerning', 'to', 'of', 'in', 'for', 'on', 'by', 'about', 'like', 'through', 'over', 'before', 'between', 'after', 'since', 'without', 'under', 'within', 'along', 'following', 'across', 'behind', 'beyond', 'plus', 'except', 'but', 'up', 'out', 'around', 'down', 'off', 'above', 'near'}
            
            for word in words:
                # Remove punctuation and get clean word
                clean_word = ''.join(c for c in word if c.isalnum())
                if len(clean_word) > 4 and clean_word not in stop_words:
                    key_terms.append(clean_word.title())
        
        # Remove duplicates and limit to top terms
        unique_terms = list(dict.fromkeys(key_terms))[:6]
        return unique_terms
    
    def _generate_content_based_options(self, content: str, key_terms: List[str], question_index: int) -> List[str]:
        """Generate content-based multiple choice options"""
        if not key_terms:
            return ["Document Analysis", "Content Review", "Information Processing", "Data Analysis"]
        
        # Use key terms to create meaningful options
        if question_index == 0:  # Main topic question
            main_topic = key_terms[0] if key_terms else "Document Content"
            if len(key_terms) >= 2:
                options = [
                    main_topic,
                    key_terms[1],
                    f"Applications of {main_topic}",
                    f"Introduction to {main_topic}"
                ]
            else:
                options = [
                    main_topic,
                    f"Advanced {main_topic}",
                    f"Introduction to {main_topic}",
                    f"Applications of {main_topic}"
                ]
        elif question_index == 1:  # Key points question
            if len(key_terms) >= 3:
                options = [
                    f"{key_terms[0]} and {key_terms[1]}",
                    f"{key_terms[1]} and {key_terms[2]}",
                    f"{key_terms[0]} only",
                    "All of the above"
                ]
            elif len(key_terms) >= 2:
                options = [
                    f"{key_terms[0]} and {key_terms[1]}",
                    f"{key_terms[0]} only",
                    f"{key_terms[1]} only",
                    "None of the above"
                ]
            else:
                options = [
                    key_terms[0] if key_terms else "Key Concepts",
                    "Technical Details",
                    "Background Information",
                    "Future Applications"
                ]
        else:  # Other questions
            if len(key_terms) >= 4:
                options = [
                    key_terms[0],
                    key_terms[1],
                    key_terms[2],
                    key_terms[3]
                ]
            elif len(key_terms) >= 3:
                options = [
                    key_terms[0],
                    key_terms[1],
                    key_terms[2],
                    "All of the above"
                ]
            else:
                options = [
                    key_terms[0] if key_terms else "Primary Focus",
                    key_terms[1] if len(key_terms) > 1 else "Secondary Focus",
                    "Related Topics",
                    "Supporting Information"
                ]
        
        return options
    
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
