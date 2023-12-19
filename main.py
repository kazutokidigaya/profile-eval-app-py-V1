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

def get_response_from_openai(text, query):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", 
            messages=[
                {"role": "system", "content": text},
                {"role": "user", "content": query}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return str(e)

def main():
    hide_streamlit_style()
    st.title("PDF User-based Q&A App")

    # Upload a PDF file
    pdf_file = st.file_uploader("Upload a PDF file", type="pdf")

    if pdf_file is not None:
        with st.spinner('Extracting text from PDF...'):
            text = extract_text_from_pdf(pdf_file)
            st.success('Text extraction complete!')

            # Initialize a list in session state to store queries
            if 'queries' not in st.session_state:
                st.session_state.queries = []
                st.session_state.responses = []

            # Display existing queries and responses
            for i, query in enumerate(st.session_state.queries):
                st.text_input(f"Question {i+1}", key=f"query_{i}", value=query)
                st.write(st.session_state.responses[i])

            # Add a new query input
            new_query = st.text_input("Have a query 🤔", key=f"query_{len(st.session_state.queries)}")
            
            if new_query:
                with st.spinner('Solution..... 😊 '):
                    response = get_response_from_openai(text, new_query)
                    # Append the new query and response to the session state
                    st.session_state.queries.append(new_query)
                    st.session_state.responses.append(response)
                    st.experimental_rerun()

if __name__ == "__main__":
    main()
