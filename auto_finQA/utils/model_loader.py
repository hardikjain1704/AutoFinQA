# model_loader.py

import os
import sys
from dotenv import load_dotenv
from utils.config_loader import load_config
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from logger import GLOBAL_LOGGER as log
from exception.custom_exception import AutoFinQAException
import asyncio

class ApiKeyManager:
    def __init__(self):
        load_dotenv()
        self.api_keys = {
            "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY"),
            "GROQ_API_KEY": os.getenv("GROQ_API_KEY"),
        }

        for key, val in self.api_keys.items():
            if val:
                log.info(f"{key} loaded from environment")
            else:
                log.warning(f"{key} is missing from environment")

    def get(self, key: str):
        return self.api_keys.get(key)

class ModelLoader:
    """
    Loads embedding models and LLMs based on config and environment.
    """
    def __init__(self):
        self.api_key_mgr = ApiKeyManager()
        self.config = load_config()
        log.info("YAML config loaded", config_keys=list(self.config.keys()))

    def load_embeddings(self):
        """
        Load and return embedding model from Google Generative AI.
        """
        try:
            model_name = self.config["embedding_model"]["model_name"]
            log.info("Loading embedding model", model=model_name)

            try:
                asyncio.get_running_loop()
            except RuntimeError:
                asyncio.set_event_loop(asyncio.new_event_loop())

            return GoogleGenerativeAIEmbeddings(
                model=model_name,
                google_api_key=self.api_key_mgr.get("GOOGLE_API_KEY")
            )
        except Exception as e:
            log.error("Error loading embedding model", error=str(e))
            raise AutoFinQAException("Failed to load embedding model", e)

    def load_llm(self, mode: str = "smart"):
        """
        Load and return the configured LLM model.
        Args:
            mode (str): "smart" for high-intelligence (70B), "fast" for high-speed/limits (8B).
        """
        llm_block = self.config["llm"]
        # provider_key = os.getenv("LLM_PROVIDER", "google")
        provider_key = os.getenv("LLM_PROVIDER", "groq")

        if provider_key not in llm_block:
            log.error("LLM provider not found in config", provider=provider_key)
            raise ValueError(f"LLM provider '{provider_key}' not found in config")

        llm_config = llm_block[provider_key]
        provider = llm_config.get("provider")
        
        if mode == "fast" and "fast_model_name" in llm_config:
            model_name = llm_config["fast_model_name"]
            log.info(f"Loading FAST LLM: {model_name}")
        else:
            model_name = llm_config.get("model_name")
            log.info(f"Loading SMART LLM: {model_name}")

        temperature = llm_config.get("temperature", 0.2)
        max_tokens = llm_config.get("max_output_tokens", 2048)
        
        try:
            if provider == "google":
                return ChatGoogleGenerativeAI(
                    model=model_name,
                    google_api_key=self.api_key_mgr.get("GOOGLE_API_KEY"),
                    temperature=temperature,
                    max_output_tokens=max_tokens
                )

            elif provider == "groq":
                return ChatGroq(
                    model=model_name,
                    api_key=self.api_key_mgr.get("GROQ_API_KEY"), #type: ignore
                    temperature=temperature,
                )

            # elif provider == "openai":
            #     return ChatOpenAI(
            #         model=model_name,
            #         api_key=self.api_key_mgr.get("OPENAI_API_KEY"),
            #         temperature=temperature
            #     )

            else:
                log.error("Unsupported LLM provider", provider=provider)
                raise ValueError(f"Unsupported LLM provider: {provider}")
        except Exception as e:
            log.error(f"Failed to load LLM from provider: {provider}", error=str(e))
            raise AutoFinQAException(f"Failed to load LLM: {model_name}", e)

if __name__ == "__main__":
    loader = ModelLoader()

    # Test Embedding
    embeddings = loader.load_embeddings()
    print(f"Embedding Model Loaded: {embeddings}")
    result = embeddings.embed_query("Hello, how are you?")
    print(f"Embedding Result: {result}")

    # Test LLM
    llm = loader.load_llm(mode="fast")
    print(f"LLM Loaded: {llm}")
    result = llm.invoke("Hello, how are you?")
    print(f"LLM Result: {result.content}")