import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Load environment variables  from .env file
load_dotenv()

# Initialize the AI model
# model_name="gpt-4o" is recommended, but "gpt-3.5-turbo" is faster and cheaper
model = ChatOpenAI(model_name="gpt-4o", temperature=0)
output_parser = StrOutputParser()

def summarize_email(content: str) -> str:
    """Generates a concise summary of the email content."""
    print("AI: Summarizing...")
    
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", "You are an expert assistant. Summarize the following email content in 30 words or less. Focus on the main point and any call to action."),
        ("user", "{email_content}")
    ])
    
    # Create the processing chain
    chain = prompt_template | model | output_parser
    
    try:
        summary = chain.invoke({"email_content": content})
        return summary
    except Exception as e:
        print(f"Error during summarization: {e}")
        return "[Summary failed]"

def classify_email(content: str, categories: list) -> str:
    """Classifies the email into one of the user-defined categories."""
    print("AI: Classifying...")
    
    # Convert list of categories into a comma-separated string
    category_string = ", ".join(categories)
    
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", f"You are a classification assistant. Classify the following email into ONE of these categories: [{category_string}]. Only output the category name and nothing else."),
        ("user", "{email_content}")
    ])
    
    chain = prompt_template | model | output_parser
    
    try:
        # We strip() to remove any leading/trailing whitespace
        category = chain.invoke({"email_content": content}).strip()
        
        # Final check to ensure the model didn't invent a category
        if category in categories:
            return category
        else:
            print(f"Warning: AI returned non-standard category '{category}'. Defaulting to 'Personal'.")
            return "Personal" # Fallback category
            
    except Exception as e:
        print(f"Error during classification: {e}")
        return "[Classification failed]"

def draft_reply(content: str) -> str:
    """
    Drafts a professional, human-like reply AND adds the user's signature.
    """
    print("AI: Drafting full reply with signature...")
    
    # --- UPDATED PROMPT ---
    # We are removing the 50-word limit and asking for a
    # more complete, human-sounding email.
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", (
            "You are a professional and helpful assistant. "
            "Draft a complete, polite, and human-like reply to the following email. "
            "If it's a question, answer it. If it's a task, acknowledge it. "
            "Write a full email, but **do not include a sign-off or closing** "
            "(e.g., 'Regards', 'Thanks'). Just write the body of the reply."
        )),
        ("user", "{email_content}")
    ])
    
    chain = prompt_template | model | output_parser
    
    try:
        # 1. Get the AI-generated reply body
        reply_body = chain.invoke({"email_content": content})
        
        # 2. Get the signature from the .env file
        # Fallback to "Your Name" if not set
        USER_NAME = os.getenv("USER_NAME", "Your Name")
        SIGNATURE = f"\n\nThanking you,\n{USER_NAME}"
        
        # 3. Combine them
        return reply_body + SIGNATURE
        
    except Exception as e:
        print(f"Error during reply drafting: {e}")
        return "[Drafting failed]"
    
def get_priority_score(category: str) -> int:
    """Assigns a numeric priority based on the category."""
    print(f"AI: Assigning priority for '{category}'...")
    priority_map = {
        "Urgent": 3,
        "Work": 2,
        "Finance": 2,
        "Personal": 1,
        "Newsletter": 0
    }
    # Return the score or a default of 1 (Personal) if not found
    return priority_map.get(category, 1)