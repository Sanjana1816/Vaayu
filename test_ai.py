import os
from core.config import settings
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

os.environ["OPENAI_API_KEY"] = settings.openai_api_key

def test_ai_connection():
    print("--- Testing OpenAI Connection (Modern LCEL Method) ---")
    # 1. Instantiate the LLM 
    llm = ChatOpenAI(model_name="gpt-3.5-turbo")
    # 2. Create a prompt template 
    prompt = PromptTemplate(
        input_variables=["topic"],
        template="In one short sentence, what is the main purpose of {topic}?",
    )   
    # 3. Define an output parser
    output_parser = StrOutputParser()
    # 4. Create the chain using LCEL (LangChain Expression Language)
    chain = prompt | llm | output_parser
    # 5. Run the chain with a specific input.
    print("Sending request to AI...")
    topic_input = "a personal safety application"
    response = chain.invoke({"topic": topic_input})
    print("AI responded successfully!")
    print(f"\nQuestion: {prompt.template.format(topic=topic_input)}")
    print(f"Response: {response}")

if __name__ == "__main__":
    test_ai_connection()