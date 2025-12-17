import os
import logging
from dotenv import load_dotenv
from openai import AzureOpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

client = AzureOpenAI(
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
    azure_endpoint=os.getenv("AZURE_OPENAI_API_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY")
)
try:
        completion = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "user", "content": "What is Azure OpenAI?"},
            ],
            max_tokens=100
        )
        logger.info(completion.choices[0].message.content)
except Exception as e:
    logger.error(f"An error occurred: {e}")