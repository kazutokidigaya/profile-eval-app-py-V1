import streamlit as st
from pymongo import MongoClient
import pandas as pd
import io
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Retrieve MongoDB URI from environment variable
mongodb_uri = os.getenv('MONGODB_URI')

# MongoDB connection setup using the URI from .env file
client = MongoClient(mongodb_uri)
db = client['users']  # The main database

# Collections
user_data_collection = db['user-data']
pdf_uploads_collection = db['pdf_uploads']


with open('styles.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    
# Admin Panel
def main():
    st.title("Admin Panel")

    # Authentication or Access Control (Implement as necessary)

    # Option to select what to view
    admin_choice = st.sidebar.selectbox("Choose an option", ["View Users", "View PDF Uploads"])

    if admin_choice == "View Users":
        view_users()

    elif admin_choice == "View PDF Uploads":
        view_pdf_uploads()


def view_users():
    st.subheader("Registered Users")
    # Fetching all user data
    users = list(user_data_collection.find())
    # Convert to a DataFrame for display purposes
    df = pd.DataFrame(users)
    st.write(df)
    
    
def view_pdf_uploads():
    st.subheader("PDF Uploads")
    # Fetching all PDF data
    pdf_uploads = list(pdf_uploads_collection.find())
    # Convert to a DataFrame for display purposes
    df = pd.DataFrame(pdf_uploads)
    # Handle Binary Data for PDF appropriately if needed before displaying
    df['file_bytes'] = '[Binary Data]'  # Simplifying for display
    st.write(df)

    # Prepare options for the selectbox
    pdf_options = [f"{pdf['_id']} - {pdf['file_name']}" for pdf in pdf_uploads]

    # Optional: Code to download a specific PDF
    selected_option = st.selectbox("Select a PDF to download:", pdf_options)

    if selected_option:
        # Parse the selected option to extract the _id
        selected_id = selected_option.split(" - ")[0]  # Assuming _id is before the first ' - '
        download_pdf(selected_id)



def download_pdf(_id):
    pdf_document = pdf_uploads_collection.find_one({"_id": _id})
    if pdf_document:
        # Extracting the binary data of the file
        file_bytes = pdf_document['file_bytes']
        file_name = pdf_document['file_name']
        st.download_button(
            label=f"Download {file_name}",
            data=io.BytesIO(file_bytes),
            file_name=file_name,
            mime='application/pdf'
        )
    else:
        st.error("PDF not found!")

if __name__ == "__main__":
    main()
