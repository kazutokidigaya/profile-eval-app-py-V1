import streamlit as st
import os
from PyPDF2 import PdfReader
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def hide_streamlit_style():
    hide_st_style = """
        <style>
        header {visibility: hidden;}
        .viewerBadge_link__qRIco{
            display:none;
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
    hide_streamlit_style()
    st.title("PDF Content-based Analysis App")

    # Upload a PDF file
    pdf_file = st.file_uploader("Upload a PDF file", type="pdf")

    if pdf_file is not None:
        with st.spinner('Extracting text from PDF...'):
            text = extract_text_from_pdf(pdf_file)
            st.success('Text extraction complete!')

        # Custom prompts
        prompts = ["Give a detailed summary of the file.", 
                   "What improvements can be made on it?"]

        # Display responses for each prompt
        for prompt in prompts:
            with st.spinner(f'Fetching response for: "{prompt}"'):
                response = get_response_from_openai(text, prompt)
                st.write(f"**{prompt}**")
                st.write(response)

if __name__ == "__main__":
    main()
