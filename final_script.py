import argparse
import json
from argparse import RawTextHelpFormatter
import requests
import streamlit as st
from typing import Optional
import warnings
import re
import time
import base64
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

try:
    from langflow.load import upload_file
except ImportError:
    warnings.warn("Langflow provides a function to help you upload files to the flow. Please install langflow to use it.")
    upload_file = None

BASE_API_URL = "http://127.0.0.1:7860"
FLOW_ID = "a8e00c6e-9144-42e5-a9a3-684e5b16dfee"
ENDPOINT = "" # You can set a specific endpoint name in the flow settings

DEBUG = False

# You can tweak the flow by adding a tweaks dictionary
# e.g {"OpenAI-XXXXX": {"model_name": "gpt-4"}}
TWEAKS = {
  "Prompt-14xLZ": {},
  "ChatInput-jebY0": {},
  "ChatOutput-032Ec": {},
  "GoogleSerperAPI-SZQPI": {},
  "OpenAIModel-xRa5b": {},
  "TextInput-MSFp7": {},
  "APIRequest-BoQEV": {},
  "TextInput-1TAOl": {},
  "TextInput-N2Jzt": {},
  "Webhook-j4j9M": {},
  "ParseData-EGVyz": {},
  "OpenAIModel-ODnE0": {},
  "Prompt-UAVSH": {},
  "ParseData-HoDVq": {},
  "CombineText-GQeIv": {},
  "TextInput-4q4ln": {},
  "TextInput-JBzJ8": {},
  "Prompt-C4R08": {},
  "TextInput-6xwqT": {},
  "Prompt-6yZjJ": {},
  "OpenAIModel-QDcLd": {},
  "OpenAIModel-2gKLw": {},
  "AnthropicModel-4rsXd": {},
  "AnthropicModel-iTLFl": {},
  "DallEImageGenerator-s2rxy": {},
  "PromptComponent-0rcBo": {}
}

def send_to_webhook(image_urls, whatsapp_number):
    webhook_url = "https://webhook.mumunha.xyz/webhook/99c17b59-3a78-45e4-b018-8974183f2810"
    
    success_count = 0
    total_images = len(image_urls)
    
    for index, image_url in enumerate(image_urls, start=1):
        payload = {
            "image_url": image_url,
            "whatsapp_number": whatsapp_number,
            "image_number": index,
            "total_images": total_images
        }
        
        try:
            response = requests.post(webhook_url, json=payload)
            response.raise_for_status()
            print(f"Image {index}/{total_images} sent successfully to webhook")
            success_count += 1
            
            if index < total_images:  # Don't wait after the last image
                time.sleep(3)  # Wait for 3 seconds before sending the next image
        except requests.exceptions.RequestException as e:
            print(f"Failed to send image {index}/{total_images} to webhook. Error: {str(e)}")
    
    return success_count == total_images

class InstagramPublisher:
    def __init__(self, access_token, account_id):
        self.access_token = access_token
        self.account_id = account_id
        self.api_version = "v20.0"
        self.base_url = f"https://graph.facebook.com/{self.api_version}"

    def create_container(self, image_urls):
        children = []
        for url in image_urls:
            child_id = self._create_media(url)
            children.append(child_id)

        url = f"{self.base_url}/{self.account_id}/media"
        params = {
            "access_token": self.access_token,
            "media_type": "CAROUSEL",
            "children": ",".join(children)
        }
        response = requests.post(url, params=params)
        response.raise_for_status()
        return response.json()['id']

    def _create_media(self, image_url):
        url = f"{self.base_url}/{self.account_id}/media"
        params = {
            "access_token": self.access_token,
            "image_url": image_url,
            "is_carousel_item": "true"
        }
        response = requests.post(url, params=params)
        response.raise_for_status()
        return response.json()['id']

    def publish_container(self, container_id):
        url = f"{self.base_url}/{self.account_id}/media_publish"
        params = {
            "access_token": self.access_token,
            "creation_id": container_id
        }
        response = requests.post(url, params=params)
        response.raise_for_status()
        return response.json()['id']

def run_flow(message: str,
  endpoint: str,
  output_type: str = "chat",
  input_type: str = "chat",
  tweaks: Optional[dict] = None,
  api_key: Optional[str] = None) -> dict:
    """
    Run a flow with a given message and optional tweaks.

    :param message: The message to send to the flow
    :param endpoint: The ID or the endpoint name of the flow
    :param tweaks: Optional tweaks to customize the flow
    :return: The JSON response from the flow
    """
    api_url = f"{BASE_API_URL}/api/v1/run/{endpoint}"

    payload = {
        "input_value": message,
        "output_type": output_type,
        "input_type": input_type,
    }
    headers = None
    if tweaks:
        payload["tweaks"] = tweaks
    if api_key:
        headers = {"x-api-key": api_key}
    response = requests.post(api_url, json=payload, headers=headers)
    return response.json()

def extract_image_urls(text):
    pattern = r"'image_urls': \[(.*?)\]"
    match = re.search(pattern, text)
    if match:
        urls = match.group(1).split(', ')
        return [url.strip("'") for url in urls]
    return []

def extract_remaining_credits(text):
    pattern = r"'remaining_credits': (\d+)"
    match = re.search(pattern, text)
    if match:
        return int(match.group(1))
    return None

def extract_job_id(text):
    pattern = r"'job_id': '(.*?)'"
    match = re.search(pattern, text)
    if match:
        return match.group(1)
    return None

def select_template(selected_index: int, current_selections: list) -> list:
    """
    Select a template and deselect others.
    
    :param selected_index: The index of the template to select (1-based)
    :param current_selections: The current list of selected templates
    :return: Updated list of selected templates
    """
    new_selections = [False] * 4
    new_selections[selected_index - 1] = True
    return new_selections

def get_template_code(template_number):
    template_mapping = {
        1: "006",
        2: "007",
        3: "008",
        4: "009"
    }
    return template_mapping.get(template_number, "")

def is_youtube_link(url):
    youtube_regex = r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
    match = re.match(youtube_regex, url)
    return bool(match)

def main():
    # Remove the title and add the centered logo
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.image("a4u.png", width=250)

    st.subheader("Crie carrosséis para o Instagram com IA")

    message = st.text_input("Qual tema você gostaria de gerar conteúdo? (ou insira um link do YouTube)", "")

    # Add checkboxes for Instagram posting and WhatsApp sending
    post_to_instagram = st.checkbox("Posta automaticamente no Instagram", value=False)
    send_to_whatsapp = st.checkbox("Envia imagens para WhatsApp", value=False)

    # Add input field for WhatsApp number
    whatsapp_number = None
    if send_to_whatsapp:
        whatsapp_number = st.text_input("Informe o número do WhatsApp para receber as imagens:")

    st.subheader("Selecione o template:")
    col1, col2, col3, col4 = st.columns(4)

    if 'template_selections' not in st.session_state:
        st.session_state.template_selections = [False] * 4

    st.markdown("""
    <style>
    .stButton > button {
        color: black;
        background-color: #F0F2F6;
        border-color: #F0F2F6;
        font-weight: bold;
    }
    .stButton > button:hover {
        color: white;
        background-color: #FF4B4B;
        border-color: #FF4B4B;
    }
    .stButton > button:focus {
        color: white;
        background-color: #FF4B4B;
        border-color: #FF4B4B;
    }
    </style>
    """, unsafe_allow_html=True)

    with col1:
        st.image("lang_001.png", width=100)
        if st.button("Template 1", key="btn1"):
            st.session_state.template_selections = select_template(1, st.session_state.template_selections)

    with col2:
        st.image("lang_002.png", width=100)
        if st.button("Template 2", key="btn2"):
            st.session_state.template_selections = select_template(2, st.session_state.template_selections)

    with col3:
        st.image("lang_003.png", width=100)
        if st.button("Template 3", key="btn3"):
            st.session_state.template_selections = select_template(3, st.session_state.template_selections)

    with col4:
        st.image("lang_004.png", width=100)
        if st.button("Template 4", key="btn4"):
            st.session_state.template_selections = select_template(4, st.session_state.template_selections)

    selected_template = next((i+1 for i, t in enumerate(st.session_state.template_selections) if t), None)
    if selected_template:
        st.markdown(f"<p style='color: #FF4B4B; font-weight: bold;'>Selected Template: {selected_template}</p>", unsafe_allow_html=True)

    if st.button("Gerar carrossel"):
        selected_templates = [i+1 for i, t in enumerate(st.session_state.template_selections) if t]
        if not selected_templates:
            st.warning("Por favor, selecione pelo menos um template.")
        else:
            selected_template = selected_templates[0]
            template_code = get_template_code(selected_template)
            
            if is_youtube_link(message):
                # Use the second flow for YouTube links
                YOUTUBE_FLOW_ID = "5a28fdca-3575-4ebc-8601-b4e528097532"
                YOUTUBE_TWEAKS = {
                    "Prompt-ZC1Tg": {},
                    "ChatInput-t4pgZ": {},
                    "ChatOutput-CCawS": {},
                    "TextInput-IVF5F": {},
                    "APIRequest-mVrVY": {},
                    "TextInput-MSkMF": {},
                    "TextInput-K1aKT": {},
                    "Webhook-vGtjV": {},
                    "ParseData-E6rEW": {},
                    "Prompt-77FKY": {},
                    "CombineText-4sShZ": {},
                    "TextInput-Pi0xu": {},
                    "TextInput-caDm3": {},
                    "Prompt-qc7ue": {},
                    "TextInput-wXHXu": {},
                    "Prompt-Q3xaY": {},
                    "OpenAIModel-uWs0Q": {},
                    "OpenAIModel-ppOA5": {},
                    "AnthropicModel-HJxTt": {},
                    "DallEImageGenerator-IlBUC": {},
                    "PromptComponent-2axgY": {},
                    "YouTubeTranscriptExtractor-qsA7O": {},
                    "OpenAIModel-Jnm6L": {}
                }
                YOUTUBE_TWEAKS["TextInput-Pi0xu"] = {"input_value": f'"{template_code}"'}
                
                with st.spinner("Gerando carrossel baseado no vídeo do YouTube..."):
                    response = run_flow(
                        message=message,
                        endpoint=YOUTUBE_FLOW_ID,
                        output_type="chat",
                        input_type="chat",
                        tweaks=YOUTUBE_TWEAKS,
                        api_key=None
                    )
            else:
                # Use the original flow for non-YouTube inputs
                TWEAKS["TextInput-4q4ln"] = {"input_value": f'"{template_code}"'}
                
                with st.spinner("Gerando carrossel..."):
                    response = run_flow(
                        message=message,
                        endpoint=ENDPOINT or FLOW_ID,
                        output_type="chat",
                        input_type="chat",
                        tweaks=TWEAKS,
                        api_key=None
                    )

            if DEBUG:
                st.subheader("Debug Information")
                st.write(f"Selected template: {selected_template}")
                st.write(f"Template code: {template_code}")
                st.write("User input message:", message)
                
                st.write("Content of all components:")
                for component_id, component_data in TWEAKS.items():
                    st.write(f"{component_id}: {component_data}")

                st.write("Full TWEAKS dictionary:")
                st.json(TWEAKS)

            if DEBUG:
                st.subheader("Raw API Request:")
                st.json({
                    "message": message,
                    "endpoint": ENDPOINT or FLOW_ID,
                    "output_type": "chat",
                    "input_type": "chat",
                    "tweaks": TWEAKS
                })

                st.subheader("Raw API Response:")
                st.json(response)

            try:
                outputs = response.get('outputs', [])
                if outputs and isinstance(outputs[0], dict):
                    output = outputs[0]
                    messages = output.get('outputs', [])
                    if messages and isinstance(messages[0], dict):
                        message_data = messages[0].get('results', {}).get('message', {}).get('data', {})
                        message_text = message_data.get('text', '')
                        
                        if DEBUG:
                            st.subheader("Parsed Response Data:")
                            st.json(message_data)
                        
                        image_urls = extract_image_urls(message_text)
                        remaining_credits = extract_remaining_credits(message_text)
                        job_id = extract_job_id(message_text)
                        
                        if image_urls:
                            st.success("Images generated successfully!")
                            
                            for i, img_url in enumerate(image_urls):
                                st.image(img_url, caption=f"Generated Image {i+1}", use_column_width=True)
                            
                            if remaining_credits is not None:
                                st.write(f"Remaining credits: {remaining_credits}")
                            if job_id:
                                st.write(f"Job ID: {job_id}")

                            # Proceed with sending/posting without confirmation
                            if send_to_whatsapp:
                                if whatsapp_number:
                                    with st.spinner("Sending images to webhook..."):
                                        if send_to_webhook(image_urls, whatsapp_number):
                                            st.success(f"All {len(image_urls)} images sent to webhook successfully!")
                                        else:
                                            st.warning("Some images failed to send to the webhook. Check the logs for details.")
                                else:
                                    st.warning("Por favor, informe o número do WhatsApp para enviar as imagens.")
                            else:
                                st.info("Sending images to webhook is disabled.")
                            
                            # Instagram Publishing
                            if post_to_instagram:
                                instagram_access_token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
                                instagram_account_id = os.getenv("INSTAGRAM_ACCOUNT_ID")
                                
                                instagram_publisher = InstagramPublisher(instagram_access_token, instagram_account_id)
                                
                                try:
                                    container_id = instagram_publisher.create_container(image_urls)
                                    st.write(f"Instagram container created with ID: {container_id}")
                                    
                                    time.sleep(10)  # Wait for container to be ready
                                    
                                    media_id = instagram_publisher.publish_container(container_id)
                                    st.success(f"Carousel published successfully on Instagram! Media ID: {media_id}")
                                except Exception as e:
                                    st.error(f"Error publishing to Instagram: {str(e)}")
                            else:
                                st.info("Automatic posting to Instagram is disabled.")
                        else:
                            st.error("Failed to generate images.")
                    else:
                        st.error("Unexpected message format in the response.")
                else:
                    st.error("Unexpected response format.")
            except Exception as e:
                st.error(f"Error parsing response: {str(e)}")

if __name__ == "__main__":
    main()
