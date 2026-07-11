from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from packvote.backend.core.config import settings


def get_llm():
    """Central LLM factory — returns the chat model based on settings.llm_provider."""
    if settings.llm_provider == "openai":
        return ChatOpenAI(model=settings.llm_model)
    elif settings.llm_provider == "anthropic":
        return ChatAnthropic(model=settings.llm_model)
    elif settings.llm_provider == "google":
        return ChatGoogleGenerativeAI(model=settings.llm_model, google_api_key=settings.google_api_key)
    raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")


def get_embeddings():
    """Central embeddings factory — returns the embedding model based on settings.embedding_provider."""
    if settings.embedding_provider == "openai":
        return OpenAIEmbeddings(model=settings.embedding_model)
    elif settings.embedding_provider == "google":
        return GoogleGenerativeAIEmbeddings(model=settings.embedding_model, google_api_key=settings.google_api_key)
    raise ValueError(f"Unknown Embedding provider: {settings.embedding_provider}")
