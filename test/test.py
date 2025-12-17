import openai
import os
from dotenv import load_dotenv

load_dotenv()

# Load Azure OpenAI configuration from environment variables
openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")
openai.api_base = os.getenv("AZURE_OPENAI_API_ENDPOINT")
openai.api_type = "azure"
openai.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")

# Set your deployment name
deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1")

try:
    response = client.chat.completions.create(
        engine=deployment_name,
        prompt="Hello, how are you?",
        max_tokens=20
    )
    print("API key and endpoint are valid!")
    print(response.choices[0].text)
except openai.error.AuthenticationError as e:
    print(f"Authentication Error: Your API key or endpoint might be invalid. Details: {e}")
except openai.error.APIError as e:
    print(f"API Error: An issue occurred with the API call. Details: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")