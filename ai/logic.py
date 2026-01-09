import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from core.config import settings

os.environ["OPENAI_API_KEY"] = settings.openai_api_key

RAG_PROMPT_TEMPLATE = """
CONTEXT:
Risk Score: {risk_score}/10
Heart Rate: {heart_rate} bpm
Audio Transcript: "{transcript}"

TASK:
Based *only* on the CONTEXT provided, analyze the user's situation.
Is this user in a crisis?
Respond with a single word: ALERT or MONITOR.
"""

def create_crisis_chain():
    """
    Creates and returns a LangChain (LCEL) chain for crisis analysis.
    This chain is designed to take a dictionary of context as input.
    """
    # 1. The LLM model
    llm = ChatOpenAI(model_name="gpt-3.5-turbo")
    # 2. The Prompt Template
    prompt = PromptTemplate.from_template(RAG_PROMPT_TEMPLATE)
    # 3. The Output Parser
    output_parser = StrOutputParser()
    # 4. The RAG Chain
    rag_chain = (
        {"risk_score": RunnablePassthrough(), "heart_rate": RunnablePassthrough(), "transcript": RunnablePassthrough()}
        | prompt
        | llm
        | output_parser
    )
    
    return rag_chain