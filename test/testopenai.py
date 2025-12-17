import os
from dotenv import load_dotenv
from openai import AzureOpenAI

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
        print(completion.choices[0].message.content)
except Exception as e:
    print(f"An error occurred: {e}")