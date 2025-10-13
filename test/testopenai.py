import os
from openai import AzureOpenAI
client = AzureOpenAI(    api_version="2024-12-01-preview",    azure_endpoint="https://akkodisai.openai.azure.com/",    api_key="CqpbS6BuNg5LEO4vuVq0RCyRMcVFe545bfGRGfu0J9nSJvAHAvS9JQQJ99BIACYeBjFXJ3w3AAABACOGkJU6")
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