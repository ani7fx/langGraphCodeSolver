import os
from langchain_openai import AzureChatOpenAI
from config import AZURE_OPENAI_DEPLOYMENT, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_KEY, AZURE_OPENAI_VERSION

os.environ["AZURE_OPENAI_API_KEY"] = AZURE_OPENAI_KEY
os.environ["AZURE_OPENAI_ENDPOINT"] = AZURE_OPENAI_ENDPOINT
os.environ["AZURE_OPENAI_API_VERSION"] = AZURE_OPENAI_VERSION
os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"] = AZURE_OPENAI_DEPLOYMENT

model = AzureChatOpenAI(
    openai_api_version=os.environ["AZURE_OPENAI_API_VERSION"],
    azure_deployment=os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"],
    temperature = 0
)