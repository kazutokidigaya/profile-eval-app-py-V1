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
import streamlit.components.v1 as components  # Import Streamlit
from streamlit.components.v1 import html
import base64

# Load environment variables
load_dotenv()

# Validate and Initialize OpenAI and Supabase clients
openai_api_key = os.getenv('OPENAI_API_KEY')
mongodb_uri = os.getenv('MONGODB_URI')
leadsquared_accesskey = os.getenv('LEADSQUARED_ACCESSKEY')  # Add your LeadSquared Access Key here
leadsquared_secretkey = os.getenv('LEADSQUARED_SECRETKEY')  # Add your LeadSquared Secret Key here
leadsquared_host = os.getenv('LEADSQUARED_HOST')  # Add your LeadSquared Host here

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
        submit_button = st.form_submit_button("Get Started")
        with st.spinner('Generating Response...'): 
            if submit_button:
                if not all([name, email, mobile]):
                    st.warning("Please fill out all fields.")
                    return  # Stop further execution if any field is missing

                current_time = datetime.datetime.now()
                existing_user = user_data_collection.find_one({"email": email})

                if existing_user:
                    remaining_attempts = existing_user.get("attempts", 3)  # Default to 3 if not set

                    if remaining_attempts <= 0:
                        st.info("You have used your max allocated usage.")
                        return  # Exit if no attempts left

                    # Decrement attempts
                    new_attempts = max(remaining_attempts - 1, 0)  # Never goes below 0
                    user_data_collection.update_one(
                        {"email": email},
                        {"$set": {"attempts": new_attempts,
                                "name": name,
                                "mobile": mobile,
                                "updated_at": current_time
                                }}
                    )
                    # st.success("Existing user's information updated. Remaining attempts: " + str(new_attempts))
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
                        "attempts": 3  # Set initial attempts to 3
                    }
                    user_data_collection.insert_one(user_data)
                    st.session_state['user_id'] = user_id
                    st.session_state['registered'] = True
                    # st.success("User registration successful. Proceed to analysis.")
                

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
                        # st.success("Lead captured in CRM successfully!")
                    # else:
                        # st.error("Lead ID not found in response.")
                # else:
                    # st.error(f"Failed to capture lead in CRM. Response: {response.text}")
                    
 
def upload_pdf_to_mongodb(pdf_file, user_id):
    file_bytes = pdf_file.getvalue()
    file_name = pdf_file.name
    created_at = datetime.datetime.now()
    _id = str(uuid4())

    # Check if the PDF already exists
    existing_pdf = db.pdf_uploads.find_one({"file_bytes": file_bytes, "file_name": file_name})
    if existing_pdf:
        # st.info("This file has already been uploaded. Continuing with analysis.")
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
    # st.success("File uploaded successfully")

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

        # if response.status_code == 200:
        #     st.success("Activity posted to CRM successfully!")
        # else:
        #     st.error(f"Failed to post activity to CRM. Response: {response.text}")

    return file_name  # Returning file name for reference



def display_shortened_response(response):
    words = response.split()
    shortened_response = ' '.join(words[:150]) + "..."  # Shorten the response to 150 words
    st.write(shortened_response)
    st.write("If you'd like to know more, download the PDF.")

def create_pdf(responses):
    pdf = FPDF()
    pdf.set_left_margin(10)
    pdf.set_right_margin(10)
    pdf.add_page()

    for response in responses:
        pdf.set_font('Arial', '', 12)
        pdf.multi_cell(0, 10, response)
        pdf.add_page()  # Add a new page for each response

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
    
    with open('styles.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    
    # Render the HTML code using st.markdown
    components.html("""
<html>
  <head>
    <title>My App</title>
  </head>
  
  <body>
    <div class="main-body">
     

      <div class="main-container">
        <!-- section1 -->

        <div class="section1">
          <div class="section1-left">
            <h1 class="section1-header">Evaluate Your Fitment </br>for a Management </br>Program</h1>
            <p class="section1-body-text">
                Use our Profile Evaluation Tool to assess your readiness</br> 
                for management programs. Simply upload your</br> 
                resume or CV, and our tool will analyze your fitment for</br> 
                various management courses</p>
            <button>Upload My Resume</button>
          </div>
          <div class="section1-right">
            <img src="https://lh3.googleusercontent.com/3tEeGNkBJnXg0N9dJu7oumnaFtmUKCcZl-cOKlhAYBtE3VvqmDf0W9HFBHCVBEOoH4Szf9QpOlSrgBRL4q4vOYdll1_GHiVL1eE=w380" alt="" />
          </div>
        </div>

        <!-- section2 -->

        <div class="section2">
          <p>Embarking on a management journey requires insight, preparation, and the right fit. That's where we come </br> 
            in! Our Profile Evaluation Tool is designed to illuminate your path to success in the management realm.</br> </br> 
            Just upload your resume or CV, and let us do the rest. </br> </br> 
            What will you get? A comprehensive analysis tailored to your profile, showcasing how you align with various </br> 
            management programs. It's straightforward, insightful, and completely tailored to you
        </p>
        </div>

        <!-- section3 -->

        <div class="section3">
          <div class="section3-header">
            <h2>How to Use this Tool to Evaluate Your Profile </br> 
                and Plan Your Next Steps</h2>
          </div>

          <!-- card-body -->
          
          <!-- 1 -->
          <div class="section3-card card1">
            <div class="card-image">
              <img src="https://lh3.googleusercontent.com/olj0WNmHgUOjQYpi8WjfHZEG95Ny7MQqZUplro5kSgy8UviHO0cRgROUK2fQDfiCdqvXlqNqJcwx98lWeDe2Xr080tkDK-mnCw=s0" width="70" alt="" />
            </div>
            <div class="card-content">
            
                <h3>Step 1: Fill Out a Brief Form</h3>
                <p>Start your journey by providing some basic information about yourself and your career 
                    aspirations. This will help us tailor the evaluation to your unique profile</p>
            
            </div>
          </div>

        <!-- 2 -->
          <div class="section3-card card2">
            <div class="card-image">
              <img src="https://lh3.googleusercontent.com/ly8yPCJu3jBCYghmMQdiwryUJz0_s6MfkyHBZ__9qHwyXiaAFmtUfK1erZq00bOiO1voJlfygoCdJlL9rnbry_Kh__-I1G6pXjQ=s0" width="70" alt="" />
            </div>
            <div class="card-content">
              
                <h3>Step 2: Upload Your Resume/CV</h3>
                <p>Attach your most recent resume or CV. Our tool uses this information to assess your 
                    academic background, professional experience, and extracurricular activities.</p>
             
            </div>
          </div>

          <!-- 3 -->
          <div class="section3-card card3">
            <div class="card-image">
              <img src="https://lh3.googleusercontent.com/Hgo4hXEglNPL3a3RCxsO8olfECbM0TdRJowG6HE0ltOwT-YZx9jivimyYZfmo2SGI9G608O0NhliqeuOGKQAh-e5Loe3rnj5o50=s0" width="70" alt="" />
            </div>
            <div class="card-content">
                <h3>Step 3: Wait for Our AI to Do Its Magic</h3>
                <p>Sit back and relax while our advanced AI analyzes your details. It cross references your
                    profile with management program criteria to provide a comprehensive evaluation. </p>
             
            </div>
          </div>

          <!-- 4 -->
          <div class="section3-card card4">
            <div class="card-image">
              <img src="https://lh3.googleusercontent.com/_5-f_4KVVazwOzzDFjL47Oiq1P6mhmbGES82m_m1AAITzIC4yq3EMUfVux1EN09Z2IKC_CEL0VZXwRvm_d5aVEwPgbu8KteKyvVE=s0" width="70" alt="" />
            </div>
            <div class="card-content">
                <h3>Step 4: View Your Analysis</h3>
                <p>Receive a detailed report on your fitment for management programs. Understand your 
                    strengths, areas for improvement, and how you compare to typical program candidates </p>
             
            </div>
          </div>

          <!-- 5 -->
          <div class="section3-card card5">
            <div class="card-image">
              <img src="https://lh3.googleusercontent.com/CpXc5hbW4jh9PxeAJP9uAtsWG9LtlAAZGKdzjkFEGabYiFjGeQjRVBdmVxXS9zvbzmVouyO0PkJsxXX5uCpCkL2eHly1HgZjag=s0" width="70" alt="" />
              </div>
              <div class="card-content">
                <h3>Step 5: Schedule a Call with an Expert</h3>
                <p>Take it further by scheduling a consultation with one of our experts. They will help you 
                    interpret your results and discuss your next steps towards management success.</p>
             
            </div>
          </div>

          <div class="bottom-button">
            <button>Upload My Resume</button>
          </div>
        </div>
      </div>
    </div>

    
    <hr>

  
  </body>

  <style>
    @import url("https://fonts.googleapis.com/css2?family=Montserrat:wght@600&display=swap");

* {
  margin: 0;
  padding: 0;
  font-family: "Arial", sans-serif;
}


h1 {
  font-size: 30px;
  margin-bottom: 20px;
  font-weight: 800;
}
h2 {
  font-size: 25px;
}
h3 {
  font-size: 20px;
}
p {
  font-size: 17px;
}

button {
  padding: 10px;
  font-size: 20px;
  margin-top: 20px;
  color: white;
  background-color: #0029e4;
  border: none;
  cursor: pointer;
  transition: background-color 0.3s, color 0.3s;
}

button:hover {
  background-color: #f1f7ff;
  color: #0029e4;
  border: 1px solid #0029e4;
}

hr {
  border: 0;
  height: 2px;
  background-color: gray;
  width: 70%;
  margin: 20px auto;
}

.section1 {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  text-align: center;
  padding: 20px;
}

.section1-left,
.section1-right {
  flex: 1;
  min-width: 300px; /* Responsive consideration */
  margin: 10px;
}
.section1-left {
  text-align: left;
  padding: 0 20px 0 0;
}

.section1-left p {
  margin-bottom: 20px;
  color: gray;
}

.section1-right {
  padding: 0 0 0 20px;
}

.section2 {
  background: #f1f7ff;
  display: flex;
  justify-content: center;
  margin: 20px 0px;
  padding: 20px;
  text-align: center;
}

.section3 {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin: 40px;
  text-align: center;
}

.section3-header {
  margin-bottom: 20px;
}

/* Add to your existing styles */

.section3-card {
  display: flex;
  align-items: center;
  text-align: left;
  padding: 20px;
  width: 830px;
  margin-bottom: 20px; /* Add space between cards */
  border: 1px solid #ddd; /* Optional: adds a border */
  border-radius: 5px; /* Optional: rounds corners */
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1); /* Optional: adds shadow */
}

.card-image img {
  height: auto;
  margin-right: 20px; /* Space between image and text */
}

.card-content {
  flex: 1; /* Takes up remaining space */
}

.card-content h3 {
  margin-top: 0;
  /* Theme color or choose what fits */
}

.card-content p {
  color: #333; /* Adjust for desired text color */
  margin: 5px 0 0 0; /* Adjust spacing as needed */
}

html {
  scroll-behavior: smooth;
}

@media screen and (max-width: 768px) {
  /* Tablet adjustments */
  .section1-right img {
    display: block; /* Show on tablets */
  }

  .section3-card {
    width: 100%; /* Full width on smaller screens */
    flex-direction: column; /* Stack image and text */
  }

  .card-image,
  .card-content {
    width: 100%; /* Full width for children */
  }
}

@media screen and (max-width: 480px) {
  /* Mobile adjustments */
  .section1-right {
    display: none; /* Hide image on mobile */
  }
  .section1 {
    align-items: center;
  }
  .section3-card {
    width: 100%; /* Adjust width for mobile */
  }
}

/* Card uniformity and design */
.section3-card {
  display: flex;
  align-items: center;
  padding: 20px;
  margin-bottom: 20px;
  border: 1px solid #ddd;
  border-radius: 5px;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
  width: 100%; /* Full width by default, adjust as needed */
  max-width: 830px; /* Maximum width */
}

.card-image img {
  width: 70px; /* Adjust as needed */
  height: 70px; /* Adjust as needed */
  object-fit: cover; /* Ensures image covers the area */
  margin-right: 20px; /* Space between image and text */
}

.card-content {
  flex: 1; /* Flex grow to fill space */
}

.stDataFrameResizable {
  max-width: 100% !important;
  max-height: 100% !important;
}

.block-container.st-emotion-cache-1y4p8pa.ea3mdgi4 {
  max-width: none;
}
/* .block-container.st-emotion-cache-1y4p8pa.ea3mdgi4 {
  max-width: 100%;
  padding-top: 3vh;
} */

.st-emotion-cache-1629p8f.e1nzilvr2 {
  text-align: center;
}

.uploadedFile.st-emotion-cache-12xsiil.e1b2p2ww5 {
  display: none;
}


.row-widget.stButton {
  text-align: center;
}

.st-emotion-cache-16y4qhw {
  width: 1194px;
  position: relative;
  display: flex;
  flex: 1 1 0%;
  justify-content: center;
  align-items: center;
  flex-direction: column;
  gap: 1rem;
}
.block-container.st-emotion-cache-1y4p8pa.ea3mdgi4 {
  align-items: center;
  display: flex;
  justify-content: center;
  width: 100%;
  text-align: center;
}

.st-emotion-cache-r421ms.e10yg2by1 {
  width: 70%;
  text-align: center;
}
.st-emotion-cache-6n2dlg{
  display: flex;
  align-items: center !important;
  flex-direction: column;
  gap: 1rem;
}


  </style>

  </html>""", height=500, width=900)

    # Setup the page with styles and header
    hide_streamlit_style()
    st.title("Start By Filling This Form")
    

    # User registration process
    register_user()
     # Initialize session states
    if st.session_state.get('registered', False):
        # File uploader
        pdf_file = st.file_uploader("Upload a PDF file", type="pdf", label_visibility="collapsed")
        user_id = st.session_state.get('user_id')  # Retrieve user_id from session state

        if pdf_file and user_id:
            # Extract text from PDF
            text = extract_text_from_pdf(pdf_file)

            prompts = ["act like an expert mba admissions consultant. evaluate this resume. look at the total number of years of experience and advice the applicant on how mba ready they are. for instance, someone with 0 to 2 years of experience might not have the best chance cracking a top mba program but might be able to get into a b-school in your own country. provide very specific advice based on the user's years of experience.", 
                "act like an mba admissions expert. check the education background, career experience, projects, skills and keywords mentioned in the resume. based on what you find, provide a summary of the applicant's journey so far. follow this up with suggestions on what kind of mba programs would work for them. after this, they need to know about the top 3 possible career paths they can get into post-mba along with some details about the same"]
                # Replace with actual prompts
            prompt_responses = []

                # Generate and display responses with a spinner showing during generation
            with st.spinner('Generating response...'):
                for prompt in prompts:
                    response = get_response_from_openai(text, prompt)
                    prompt_responses.append(response)

                    # Check if responses are available and display a shortened version of the first response
                if prompt_responses:
                    st.subheader("Brief Overview:")
                    display_shortened_response(prompt_responses[0])

                # After responses are generated, create a PDF and offer for download outside the spinner
            if prompt_responses:
                    # Create PDF with all responses
                full_pdf = create_pdf(prompt_responses)

                    # Offer the PDF for download
                st.download_button(label="Download Detailed Analysis", data=full_pdf, file_name="detailed_analysis.pdf", mime='application/pdf')

                # Additional functionality for uploading to MongoDB or other tasks can be added here
                pdf_url = upload_pdf_to_mongodb(pdf_file, user_id)

if __name__ == "__main__":
    main()

    
 