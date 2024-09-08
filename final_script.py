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

# try:
#     from langflow.load import upload_file
# except ImportError:
#     warnings.warn("Langflow provides a function to help you upload files to the flow. Please install langflow to use it.")
#     upload_file = None

BASE_API_URL = "https://langflow.mumunha.xyz"
FLOW_ID = "4a78c140-6113-4838-a788-7ba455dc5b9d"
ENDPOINT = "" # You can set a specific endpoint name in the flow settings
API_KEY = "sk-bM3yWoPbvDnF130Gpt02iKvX5Db8GFqh4HwL8-Ap2uw"

# You can tweak the flow by adding a tweaks dictionary
# e.g {"OpenAI-XXXXX": {"model_name": "gpt-4"}}
TWEAKS = {
  "Prompt-nKzlt": {},
  "ChatInput-KrBpp": {},
  "ChatOutput-VqSw5": {},
  "TextInput-z4dax": {},
  "APIRequest-yObcM": {},
  "TextInput-r54jz": {},
  "TextInput-VtIAR": {},
  "Webhook-mVKLT": {},
  "ParseData-M8Ch8": {},
  "Prompt-LkpPg": {},
  "CombineText-sVCXM": {},
  "TextInput-g8HvQ": {},
  "TextInput-AhCrB": {},
  "Prompt-132Cy": {},
  "TextInput-EWbsm": {},
  "Prompt-xw5Nj": {},
  "OpenAIModel-h4hdc": {},
  "OpenAIModel-kFb5t": {},
  "AnthropicModel-mQEJ7": {},
  "AnthropicModel-YRf1M": {},
  "DallEImageGenerator-0FVRz": {},
  "PromptComponent-kNA2P": {},
  "CreateData-sY3kD": {}
}

DEBUG = False

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
                YOUTUBE_FLOW_ID = "ff9c59d9-02ed-48e4-a7e0-84272be3c88f"
                YOUTUBE_TWEAKS = {
                    "Prompt-zQDhv": {},
                    "ChatInput-uvUaF": {},
                    "ChatOutput-pUlDG": {},
                    "TextInput-hdMfm": {},
                    "APIRequest-irgHK": {},
                    "TextInput-9tlWp": {},
                    "TextInput-epC21": {},
                    "Webhook-95gLz": {},
                    "ParseData-BgD4V": {},
                    "Prompt-nyamU": {},
                    "CombineText-fy34I": {},
                    "TextInput-GTJmO": {},
                    "TextInput-rPfX5": {},
                    "Prompt-xudpi": {},
                    "TextInput-tGdfT": {},
                    "Prompt-DIoAj": {},
                    "OpenAIModel-eFKGL": {},
                    "OpenAIModel-5hIDP": {},
                    "AnthropicModel-gNWrn": {},
                    "DallEImageGenerator-9kNK9": {},
                    "PromptComponent-dnwIT": {},
                    "YouTubeTranscriptExtractor-yinDa": {},
                    "OpenAIModel-WCdt3": {},
                    "CreateData-jbPxB": {}
                }
                YOUTUBE_TWEAKS["TextInput-GTJmO"] = {"input_value": f'"{template_code}"'}
                
                with st.spinner("Gerando carrossel baseado no vídeo do YouTube..."):
                    response = run_flow(
                        message=message,
                        endpoint=YOUTUBE_FLOW_ID,
                        output_type="chat",
                        input_type="chat",
                        tweaks=YOUTUBE_TWEAKS,
                        api_key=API_KEY
                    )
            else:
                # Use the original flow for non-YouTube inputs
                TWEAKS["TextInput-g8HvQ"] = {"input_value": f'"{template_code}"'}
                
                with st.spinner("Gerando carrossel..."):
                    response = run_flow(
                        message=message,
                        endpoint=ENDPOINT or FLOW_ID,
                        output_type="chat",
                        input_type="chat",
                        tweaks=TWEAKS,
                        api_key=API_KEY
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
