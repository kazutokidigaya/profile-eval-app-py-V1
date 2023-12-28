import streamlit as st
import os
import requests 
import datetime
from PyPDF2 import PdfReader
from openai import OpenAI
from dotenv import load_dotenv
import io
from fpdf import FPDF
from pymongo import MongoClient
from uuid import uuid4
import datetime
import time

# Load environment variables
load_dotenv()

# Validate and Initialize OpenAI and Supabase clients
openai_api_key = os.getenv('OPENAI_API_KEY')
mongodb_uri = os.getenv('MONGODB_URI')
leadsquared_accesskey = os.getenv('LEADSQUARED_ACCESSKEY')  # Add your LeadSquared Access Key here
leadsquared_secretkey = os.getenv('LEADSQUARED_SECRETKEY')  # Add your LeadSquared Secret Key here
leadsquared_host = os.getenv('LEADSQUARED_HOST')  # Add your LeadSquared Host here


with open('styles.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

openai_client = OpenAI(api_key=openai_api_key)
mongo_client = MongoClient(mongodb_uri)
db = mongo_client['users']  # Database name
user_data_collection = db['user-data']  # Collection name

def hide_streamlit_style():
    hide_st_style = """
        <style>
        header {visibility: hidden;}
        .viewerBadge_container__r5tak.styles_viewerBadge__CvC9N {
            display: none !important;
        }
        .viewerBadge_link__qRIco {
            display: none !important;
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



def register_user():
    if 'registered' not in st.session_state:
        st.session_state['registered'] = False

    with st.form("User Registration"):
        name = st.text_input("Name")
        email = st.text_input("Email")
        mobile = st.text_input("Mobile Number")
        submit_button = st.form_submit_button("Register")

        if submit_button:
            if not all([name, email, mobile]):
                st.warning("Please fill out all fields.")
                return  # Stop further execution if any field is missing

            current_time = datetime.datetime.now()
            existing_user = user_data_collection.find_one({"email": email})

            # Check if the user has attempts left or if it's a new user
            if existing_user:
                if existing_user.get("attempts", 1) <= 0:
                    st.info("You have used your max allocated usage.")
                    return  # Stop further execution

                # Decrement attempts
                new_attempts = existing_user.get("attempts", 1) - 1
                user_data_collection.update_one(
                    {"email": email},
                    {"$set": {"attempts": new_attempts,
                              "name": name,
                              "mobile": mobile,
                              "updated_at": current_time
                              }}
                )
                
                st.success("Existing user's information updated.")
                st.session_state['registered'] = True
                st.session_state['user_id'] = existing_user["_id"]



            else:  # New user registration
                user_id = str(uuid4())
                user_data = {
                    "_id": user_id,
                    "name": name,
                    "email": email,
                    "mobile": mobile,
                    "created_at": datetime.datetime.now(),
                    "updated_at": datetime.datetime.now(),
                    "attempts": 2  # Set initial attempts to 3
                }
                user_data_collection.insert_one(user_data)
                st.session_state['user_id'] = user_id

            st.session_state['registered'] = True
            st.success("User registration successful. Proceed to analysis.")

            # Attempt to capture lead in CRM
            url = f"{leadsquared_host}/LeadManagement.svc/Lead.Capture?accessKey={leadsquared_accesskey}&secretKey={leadsquared_secretkey}"
            headers = {"Content-Type": "application/json"}
            payload = [
                {"Attribute": "FirstName", "Value": name},
                {"Attribute": "EmailAddress", "Value": email},
                {"Attribute": "Phone", "Value": mobile},
                {"Attribute": "campaign", "Value": 'profile_evaluation_app'},
                {"Attribute": "medium", "Value": 'profile_evaluation_app'},
            ]
            response = requests.post(url, json=payload, headers=headers)

            if response.status_code == 200:
                lead_id = response.json().get('Message', {}).get('RelatedId')
                if lead_id:
                    st.session_state['lead_id'] = lead_id
                    st.success("Lead captured in CRM successfully!")
                else:
                    st.error("Lead ID not found in response.")
            else:
                st.error(f"Failed to capture lead in CRM. Response: {response.text}")
                  
   

 
def upload_pdf_to_mongodb(pdf_file, user_id):
    file_bytes = pdf_file.getvalue()
    file_name = pdf_file.name
    created_at = datetime.datetime.now()
    _id = str(uuid4())

    # Check if the PDF already exists
    existing_pdf = db.pdf_uploads.find_one({"file_bytes": file_bytes, "file_name": file_name})
    if existing_pdf:
        st.info("This file has already been uploaded. Continuing with analysis.")
        return file_name  # Return the existing file name for reference

    # If the file doesn't exist, proceed with uploading
    pdf_data = {
        "_id": _id,
        "user_id": user_id,
        "file_name": file_name,
        "file_bytes": file_bytes,
        "created_at": created_at
    }
    with st.spinner('Uploading PDF to MongoDB...'):
        db.pdf_uploads.insert_one(pdf_data)
    st.success("File uploaded successfully")

    # Retrieve the lead_id from the session state
    lead_id = st.session_state.get('lead_id')  # Use lead_id from session state
    
    # If lead_id exists, post activity to LeadSquared CRM
    if lead_id:
    # Construct API endpoint and headers
        url = f"{leadsquared_host}/ProspectActivity.svc/Create?accessKey={leadsquared_accesskey}&secretKey={leadsquared_secretkey}"
        headers = {"Content-Type": "application/json"}

        # Getting the current time in the required format
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # Constructing the activity payload
       
        payload = {
            "RelatedProspectId": lead_id,
            "ActivityEvent": 228,  # Adjust as per your CRM's custom activity event code
            "ActivityNote": f"Uploaded PDF: {file_name}",
            "Fields": [
                {
                    "SchemaName": "PDF Name",  # This is a custom field example, adjust as needed
                    "Value": file_name,
                },
                # ... include any other necessary fields ...
            ]
        }



        # Post the activity
        response = requests.post(url, json=payload, headers=headers)

        if response.status_code == 200:
            st.success("Activity posted to CRM successfully!")
        else:
            st.error(f"Failed to post activity to CRM. Response: {response.text}")

    return file_name  # Returning file name for reference



def create_pdf(prompt_responses):
    pdf = FPDF()
    pdf.set_left_margin(10)
    pdf.set_right_margin(10)
    pdf.add_page()

    for prompt, response in prompt_responses:
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'Prompt:', 0, 1, 'L')
        pdf.set_font('Arial', '', 12)
        pdf.multi_cell(0, 10, prompt)
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'Response:', 0, 1, 'L')
        pdf.set_font('Arial', '', 12)
        pdf.multi_cell(0, 10, response)
        pdf.add_page()

    pdf_file = io.BytesIO()
    pdf.output(pdf_file)
    pdf_file.seek(0)
    return pdf_file.getvalue()

def get_response_from_openai(text, prompt):
    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo", 
            messages=[{"role": "system", "content": text}, {"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return str(e)
    
def main():
    hide_streamlit_style()
    st.title("PDF Analysis App")

    register_user()
    if st.session_state.get('registered', False):
        pdf_file = st.file_uploader("Upload a PDF file", type="pdf")
        user_id = st.session_state.get('user_id')  # Retrieve user_id from session state

        if pdf_file is not None and user_id is not None:
            text = extract_text_from_pdf(pdf_file)
            st.success('Text extracted from PDF!')

            prompt_responses = []
            prompts = ["act like an expert mba admissions consultant. evaluate this resume. look at the total number of years of experience and advice the applicant on how mba ready they are. for instance, someone with 0 to 2 years of experience might not have the best chance cracking a top mba program but might be able to get into a b-school in your own country. provide very specific advice based on the user's years of experience.", 
                       "act like an mba admissions expert. check the education background, career experience, projects, skills and keywords mentioned in the resume. based on what you find, provide a summary of the applicant's journey so far. follow this up with suggestions on what kind of mba programs would work for them. after this, they need to know about the top 3 possible career paths they can get into post-mba along with some details about the same"]
           
            with st.spinner('Generating Response...'):    
                for prompt in prompts:
                    response = get_response_from_openai(text, prompt)
                    prompt_responses.append((prompt, response))

            pdf = create_pdf(prompt_responses)
            st.download_button(label="Download Responses PDF", data=pdf, file_name="prompt_responses.pdf", mime='application/pdf')

            pdf_url = upload_pdf_to_mongodb(pdf_file, user_id)
            if pdf_url:
                st.write("PDF uploaded successfully. URL:", pdf_url)
                
            for prompt, response in prompt_responses:
                st.write(f"**{prompt}**")
                st.write(response)

if __name__ == "__main__":
    main()
    
 