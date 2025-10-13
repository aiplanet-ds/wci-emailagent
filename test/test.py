import openai
import os

# Set your Azure OpenAI API key and endpoint
# It's recommended to load these from environment variables for security
openai.api_key = "CqpbS6BuNg5LEO4vuVq0RCyRMcVFe545bfGRGfu0J9nSJvAHAvS9JQQJ99BIACYeBjFXJ3w3AAABACOGkJU6" 
openai.api_base = "https://akkodisai.openai.azure.com/" 
openai.api_type = "azure"
openai.api_version = "2024-12-01-preview"

# Set your deployment name
deployment_name = "gpt-4.1" # Replace with your actual deployment name

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