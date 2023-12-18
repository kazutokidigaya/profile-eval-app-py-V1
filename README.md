# PDF Content-based Analysis App

This Streamlit application allows users to upload a PDF file and receive a detailed analysis based on the content. The analysis includes a summary of the file and suggested improvements, utilizing OpenAI's GPT-3.5 model.

## Dependencies
- Python 3.7+
- Streamlit
- PyPDF2
- openai
- python-dotenv

## Installation

First, clone the repository to your local machine:

```bash
git clone https://github.com/kazutokidigaya/profile-eval-app-py-V1.git
cd profile-eval-app-py-V1

Install the required Python packages:
pip install streamlit PyPDF2 openai python-dotenv

## Configuration

Create a .env file in the root directory of the project and add your OpenAI API key:
OPENAI_API_KEY='your_api_key_here'

## Running the Application

To run the app, navigate to the project directory and execute:
streamlit run app.py

##Usage
On the application interface, upload a PDF file.
The app will automatically extract the text from the PDF.
It will then provide a detailed summary and suggest improvements based on the content using OpenAI's GPT-3.5 model.
