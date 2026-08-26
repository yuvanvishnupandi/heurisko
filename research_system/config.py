"""Configuration for the Heurisko Web Research Agent. Manages API keys and initializes API clients."""

import os
import requests
from typing import Dict, Any, Optional
import logging
from dotenv import load_dotenv
from tavily import TavilyClient
from google.genai import types
from google.ai import generativelanguage as glm 

try:
    import google.generativeai as genai
    from langchain_google_genai import ChatGoogleGenerativeAI
    from firecrawl import FirecrawlApp
except ImportError as e:
    genai = None
    ChatGoogleGenerativeAI = None
    FirecrawlApp = None
    logging.warning(f"ImportError: {e}. Some functionalities might be limited.")
    # logging.warning("google.generativeai or langchain_google_genai not installed. Gemini functionality will be limited.")

load_dotenv()

AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY_O3_mini")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT_O3_mini")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION_O3_mini")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME_O3_mini")

AZURE_OPENAI_API_KEY_ALT = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT_ALT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_VERSION_ALT = os.getenv("AZURE_OPENAI_API_VERSION")
AZURE_OPENAI_DEPLOYMENT_ALT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

NEWS_API_KEY = os.getenv("NEWS_API_KEY")

WIKIDATA_API_ENDPOINT = "https://www.wikidata.org/w/api.php"

HIGH_CONFIDENCE_THRESHOLD = float(os.getenv("HIGH_CONFIDENCE_THRESHOLD", "0.8"))
MEDIUM_CONFIDENCE_THRESHOLD = float(os.getenv("MEDIUM_CONFIDENCE_THRESHOLD", "0.5"))
LOW_CONFIDENCE_THRESHOLD = float(os.getenv("LOW_CONFIDENCE_THRESHOLD", "0.3"))

FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")

if GEMINI_API_KEY and genai: # Check if genai was imported successfully
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception as e:
        logging.warning(f"Failed to configure google.genai: {e}")
else:
    logging.warning("GEMINI_API_KEY not set or google.generativeai not installed. Cannot configure Gemini client.")

def get_primary_llm(streaming: bool = False):
    """Get the primary LLM client with multi-provider fallback.
    
    Tries to instantiate Gemini, OpenAI, Groq, Mistral, and OpenRouter in that order.
    Uses LangChain's native with_fallbacks() to ensure robust execution.
    """
    primary_llm = None
    fallbacks = []

    # 1. Gemini
    if GEMINI_API_KEY and ChatGoogleGenerativeAI is not None:
        try:
            gemini_llm = ChatGoogleGenerativeAI(
                model=GEMINI_MODEL,
                google_api_key=GEMINI_API_KEY,
                streaming=streaming,
            )
            if primary_llm is None:
                primary_llm = gemini_llm
            else:
                fallbacks.append(gemini_llm)
        except Exception as e:
            logging.error(f"Failed to initialize Gemini: {e}")

    # 2. OpenAI
    if OPENAI_API_KEY:
        try:
            from langchain_openai import ChatOpenAI
            openai_llm = ChatOpenAI(
                model="gpt-4o-mini",
                openai_api_key=OPENAI_API_KEY,
                streaming=streaming,
            )
            if primary_llm is None:
                primary_llm = openai_llm
            else:
                fallbacks.append(openai_llm)
        except Exception as e:
            logging.error(f"Failed to initialize OpenAI: {e}")

    # 3. Groq
    if GROQ_API_KEY:
        try:
            from langchain_openai import ChatOpenAI
            groq_llm = ChatOpenAI(
                base_url="https://api.groq.com/openai/v1",
                model="llama3-70b-8192",
                openai_api_key=GROQ_API_KEY,
                streaming=streaming,
            )
            if primary_llm is None:
                primary_llm = groq_llm
            else:
                fallbacks.append(groq_llm)
        except Exception as e:
            logging.error(f"Failed to initialize Groq: {e}")

    # 4. Mistral
    if MISTRAL_API_KEY:
        try:
            from langchain_openai import ChatOpenAI
            mistral_llm = ChatOpenAI(
                base_url="https://api.mistral.ai/v1",
                model="mistral-large-latest",
                openai_api_key=MISTRAL_API_KEY,
                streaming=streaming,
            )
            if primary_llm is None:
                primary_llm = mistral_llm
            else:
                fallbacks.append(mistral_llm)
        except Exception as e:
            logging.error(f"Failed to initialize Mistral: {e}")
            
    # 5. OpenRouter
    if OPENROUTER_API_KEY:
        try:
            from langchain_openai import ChatOpenAI
            openrouter_llm = ChatOpenAI(
                base_url="https://openrouter.ai/api/v1",
                model="anthropic/claude-3-haiku",
                openai_api_key=OPENROUTER_API_KEY,
                streaming=streaming,
            )
            if primary_llm is None:
                primary_llm = openrouter_llm
            else:
                fallbacks.append(openrouter_llm)
        except Exception as e:
            logging.error(f"Failed to initialize OpenRouter: {e}")

    if primary_llm is None:
        raise ValueError(
            "No primary LLM configured. Please set at least one valid API key (Gemini, OpenAI, Groq, Mistral, or OpenRouter) in the .env file."
        )

    if fallbacks:
        return primary_llm.with_fallbacks(fallbacks)
    return primary_llm


def get_tavily_client():
    """Get the Tavily search client."""
    if not TAVILY_API_KEY:
        raise ValueError("TAVILY_API_KEY not set. Cannot create Tavily client.")
    return TavilyClient(api_key=TAVILY_API_KEY)

def get_duckduckgo_client():
    """Get the DuckDuckGo search client."""
    from duckduckgo_search import DDGS
    return DDGS()

def get_news_api_client():
    """Get the NewsAPI client."""
    if not NEWS_API_KEY:
        raise ValueError("NEWS_API_KEY not set. Cannot create NewsAPI client.")
    
    from newsapi import NewsApiClient
    return NewsApiClient(api_key=NEWS_API_KEY)

def get_wikidata_client():
    """Get a function to query the Wikidata API."""
    
    def query_wikidata(search_term: str, language: str = "en", limit: int = 5):
        """Query the Wikidata API for entities."""
        params = {
            'action': 'wbsearchentities',
            'format': 'json',
            'language': language,
            'search': search_term,
            'limit': limit
        }
        
        response = requests.get(WIKIDATA_API_ENDPOINT, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Wikidata API request failed with status code {response.status_code}")
    
    return query_wikidata

def get_entity_details(entity_id: str, language: str = "en"):
    """Get detailed information about a Wikidata entity."""
    params = {
        'action': 'wbgetentities',
        'format': 'json',
        'ids': entity_id,
        'languages': language
    }
    
    response = requests.get(WIKIDATA_API_ENDPOINT, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Wikidata API request failed with status code {response.status_code}")


def get_azure_openai_parser_llm():
    """Get the Azure OpenAI LLM client using alternate credentials for parsing tasks."""
    if AZURE_OPENAI_API_KEY_ALT and AZURE_OPENAI_ENDPOINT_ALT:
        from langchain_openai import AzureChatOpenAI
        logging.info(f"Initializing Azure OpenAI parser LLM with endpoint: {AZURE_OPENAI_ENDPOINT_ALT} and deployment: {AZURE_OPENAI_DEPLOYMENT_ALT}")
        return AzureChatOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT_ALT,
            openai_api_version=AZURE_OPENAI_API_VERSION_ALT,
            deployment_name=AZURE_OPENAI_DEPLOYMENT_ALT,
            openai_api_key=AZURE_OPENAI_API_KEY_ALT,
            temperature=0.1, 
            max_retries=3, 
        )
    else:
        logging.error("Alternate Azure OpenAI credentials (API Key, Endpoint, Version, Deployment) not fully set. Cannot create parser LLM client.")
        raise ValueError("Alternate Azure OpenAI credentials not set.") 

def get_gemini_llm(streaming: bool = False):
    """Get the Google Gemini LLM client."""
    if not GEMINI_API_KEY:
        logging.error("GEMINI_API_KEY not set. Cannot create Gemini LLM client.")
        raise ValueError("GEMINI_API_KEY not set.")
    if not GEMINI_MODEL:
        logging.error("GEMINI_MODEL environment variable not set. Cannot create Gemini LLM client.")
        raise ValueError("GEMINI_MODEL not set.")
    
    model_name = GEMINI_MODEL 

    if ChatGoogleGenerativeAI is None:
         logging.error("langchain_google_genai not installed. Cannot create Gemini LLM client.")
         raise ImportError("langchain_google_genai package not found.")

    try:
        # Assuming the genai.configure() call earlier handles API key globally
        # If not, you might need to pass api_key=GEMINI_API_KEY here.
        # The 'google_api_key' parameter is often used in ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=GEMINI_API_KEY, # Explicitly pass key
            convert_system_message_to_human=True, # Often helpful for Gemini
            streaming=streaming,
            # Add temperature or other generation parameters if needed
            # temperature=0.7
        )
    except Exception as e:
        logging.error(f"Failed to create Gemini LLM client: {e}")
        raise ValueError(f"Failed to initialize Gemini LLM: {e}")

import base64
import os
from google import genai
from google.genai import types


def generate():
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )

    model = "gemini-2.5-flash-preview-04-17"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text="""INSERT_INPUT_HERE"""),
            ],
        ),
    ]
    tools = [
        types.Tool(google_search=types.GoogleSearch())
    ]
    generate_content_config = types.GenerateContentConfig(
        tools=tools,
        response_mime_type="text/plain",
    )

    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        print(chunk.text, end="")

if __name__ == "__main__":
    generate()

def perform_gemini_google_search(claim: str) -> Dict[str, Any]:
    """
    Performs a search using the Gemini model (specified by GEMINI_MODEL env var)
    with Google Search tool enabled.

    Args:
        claim: The claim or query to search for.

    Returns:
        A dictionary containing the 'text' response and 'source_urls' list
        extracted from grounding metadata, or an error string.
    """
    if not genai:
        logging.error("google.generativeai is not installed or configured.")
        return {"error": "Gemini library not available.", "text": "", "source_urls": []}
    if not GEMINI_API_KEY:
        logging.error("GEMINI_API_KEY not set.")
        return {"error": "GEMINI_API_KEY not configured.", "text": "", "source_urls": []}
    if not GEMINI_MODEL:
        logging.error("GEMINI_MODEL environment variable not set.")
        return {"error": "GEMINI_MODEL not configured.", "text": "", "source_urls": []}

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # Construct the prompt with explicit instructions
        prompt_text = f"""Please research the following query using the Google Search tool: '{claim}'

Provide a comprehensive answer based *only* on the search results. 
Critically, ensure you list the URLs of all web sources consulted to generate your answer."""

        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=prompt_text)
                ],
            ),
        ]
        
        tools = [
            types.Tool(google_search=types.GoogleSearch())
        ]
        
        generate_content_config = types.GenerateContentConfig(
            tools=tools,
            temperature=0.1,
            response_mime_type="text/plain",
        )
        
        logging.info(f"Sending request to Gemini model '{GEMINI_MODEL}' with Google Search enabled.")
        
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=generate_content_config,
        )
        
        search_response_text = ""
        source_urls = []

        # Extract text response
        if response.candidates and response.candidates[0].content.parts:
            search_response_text = response.candidates[0].content.parts[0].text
            logging.info(f"Received text response from Gemini: {search_response_text[:100]}...")
        else:
            logging.warning("Gemini response did not contain expected content parts.")
            # Return error early if no text part
            return {"error": "No valid response text content from Gemini.", "text": "", "source_urls": []} 

        # Extract source URLs from grounding metadata
        if response.candidates[0].grounding_metadata and response.candidates[0].grounding_metadata.grounding_chunks:
            for chunk in response.candidates[0].grounding_metadata.grounding_chunks:
                if hasattr(chunk, 'web') and hasattr(chunk.web, 'uri') and chunk.web.uri:
                    source_urls.append(chunk.web.uri)
            # Remove potential duplicates
            source_urls = list(dict.fromkeys(source_urls))
            logging.info(f"Extracted {len(source_urls)} unique source URLs from grounding metadata chunks.")
        else:
             logging.info("No grounding metadata chunks found or grounding failed.")

        # Return text and URLs separately
        return {"text": search_response_text, "source_urls": source_urls}

    except Exception as e:
        logging.error(f"Error during Gemini search for '{claim}': {e}")
        # Ensure consistent error return format
        return {"error": f"Error: {e}", "text": "", "source_urls": []}

def get_firecrawl_client():
    """Get the Firecrawl client."""
    if not FIRECRAWL_API_KEY:
        raise ValueError("FIRECRAWL_API_KEY not set. Cannot create Firecrawl client.")
    if FirecrawlApp is None:
         raise ImportError("firecrawl-py package not found or failed to import.")
    return FirecrawlApp(api_key=FIRECRAWL_API_KEY)