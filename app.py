import streamlit as st
from supabase import create_client, Client
import os
from PyPDF2 import PdfReader
from openai import OpenAI
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def is_valid_email(email_address):
    email_regex = r"[^@]+@[^@]+\.[^@]+"
    return re.match(email_regex, email_address) is not None

def login_form():
    st.sidebar.title("Login/Signup")
    email = st.sidebar.text_input("Email")
    password = st.sidebar.text_input("Password", type="password")

    col1, col2, col3 = st.sidebar.columns([1, 2, 1])  # Adjust column ratios for centering

    with col2:  # Place buttons in the second (middle) column
        login = st.button("Login")
        signup = st.button("Signup")

    if login:
        if is_valid_email(email):
            response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            handle_response(response)
        else:
            st.sidebar.error("Invalid email format")

    if signup:
        if is_valid_email(email):
            response = supabase.auth.sign_up({
                "email": email,
                "password": password
            })
            handle_response(response)
        else:
            st.sidebar.error("Invalid email format")

def handle_response(response):
    if response.user:
        st.session_state['user'] = response.user
        st.experimental_rerun()
    elif response.error and response.error.message == "Email not confirmed":
        st.sidebar.error("Please confirm your email before logging in.")
    else:
        st.sidebar.error("Authentication failed: " + response.error.message if response.error else "Unknown error")

def logout():
    if st.sidebar.button("Logout"):
        supabase.auth.sign_out()
        st.session_state['user'] = None
        st.experimental_rerun()

def hide_streamlit_style():
    hide_st_style = """
        <style>
        header {visibility: hidden;}
        .viewerBadge_container__r5tak.styles_viewerBadge__CvC9N {
            display: none;
        }
        footer {visibility: hidden;}
        </style>
    """
    st.markdown(hide_st_style, unsafe_allow_html=True)
    
def extract_text_from_pdf(pdf_file):
    pdf_reader = PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() or ''
    return text

def get_response_from_openai(text, prompt):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", 
            messages=[
                {"role": "system", "content": text},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return str(e)

def main():
    if 'user' not in st.session_state:
        st.session_state['user'] = None

    if st.session_state['user']:
        hide_streamlit_style()
        st.title("PDF Analysis App")
        logout()  # Add logout option

        pdf_file = st.file_uploader("Upload a PDF file", type="pdf")
        if pdf_file is not None:
            with st.spinner('Extracting text from PDF...'):
                text = extract_text_from_pdf(pdf_file)
                st.success('Text extraction complete!')

            prompts = ["Give a detailed summary of the file.", "What improvements can be made on it?"]
            for prompt in prompts:
                with st.spinner(f'Fetching response for: "{prompt}"'):
                    response = get_response_from_openai(text, prompt)
                    st.write(f"**{prompt}**")
                    st.write(response)
    else:
        login_form()

if __name__ == "__main__":
    main()
