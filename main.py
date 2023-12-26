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

# Define admin credentials
ADMIN_USERNAME = "admin@gmail.com"
ADMIN_PASSWORD = "admin123@"

def check_credentials(username, password):
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD

def admin_panel():
    """Function that contains the admin panel"""
    admin_choice = st.sidebar.selectbox("Choose an option", ["View Users", "View PDF Uploads"])

    if admin_choice == "View Users":
        view_users()
    elif admin_choice == "View PDF Uploads":
        view_pdf_uploads()

def view_users():
    st.subheader("Registered Users")
    users = list(user_data_collection.find())
    df = pd.DataFrame(users)
    st.write(df)

def view_pdf_uploads():
    st.subheader("PDF Uploads")
    pdf_uploads = list(pdf_uploads_collection.find())
    pdf_df = pd.DataFrame(pdf_uploads)
    pdf_df['file_bytes'] = '[Binary Data]'  # Simplifying for display

    # Fetch user data to display email alongside PDF uploads
    users = list(user_data_collection.find({}, {'_id': 1, 'email': 1}))
    user_df = pd.DataFrame(users).set_index('_id')  # Set _id as index for easier merging

    # Merge PDF uploads with user data on 'user_id' == '_id'
    merged_df = pdf_df.merge(user_df, left_on='user_id', right_index=True, how='left')
    merged_df['User Email'] = merged_df['email'].fillna('No email')  # Handle missing emails
    merged_df['Selection'] = merged_df['User Email'] + " - " + merged_df['file_name']

    # Display the dataframe with the unique ID and other relevant details
    st.write(merged_df[['user_id', 'file_name', 'User Email', 'created_at']])  # Adjust columns as needed

    # Prepare options for the selectbox including the email and file name for convenience
    pdf_options = merged_df['Selection'].tolist()

    # Optional: Code to download a specific PDF
    selected_option = st.selectbox("Select a PDF to download:", pdf_options)

    if selected_option:
        selected_id = merged_df[merged_df['Selection'] == selected_option]['user_id'].iloc[0]
        download_pdf(selected_id)

def download_pdf(_id):
    pdf_document = pdf_uploads_collection.find_one({"user_id": _id})
    if pdf_document:
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

def main():
    st.title("Admin Panel")

    # User Authentication
    if 'authenticated' not in st.session_state:
        st.session_state['authenticated'] = False

    if not st.session_state['authenticated']:
        with st.container():
            st.write("## Admin LogIn")  # Optional: You might want to remove or change this line
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.button("Login"):
                if check_credentials(username, password):
                    st.session_state['authenticated'] = True
                    st.experimental_rerun()
                else:
                    st.error("Invalid username or password")
    else:
        admin_panel()

if __name__ == "__main__":
    main()