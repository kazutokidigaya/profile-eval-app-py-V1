import streamlit as st
import time
import streamlit.components.v1 as components  # Import Streamlit


with open('styles.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    
def contact_us_section():
    st.text("hello")

def main():
    with open('app.html', 'r') as f:
        html_string = f.read()
    components.html(html_string, height=1500)
    # Layout with columns
    col1, col2 = st.columns([3, 1])  # Adjust the ratio based on your layout needs

    with col1:
        st.title("Evaluate Your Fitment for a Management Program")
        html_content = """
        <div style="text-align: left; margin: 10px 10px 30px 0;">
            <span>Use our Profile Evaluation Tool to assess<br>
            your readiness for management programs.<br>
            Simply upload your resume or CV, and our tool<br>
            will analyze your fitment for various management courses</span>
        </div>
        """
        st.markdown(html_content, unsafe_allow_html=True)
        if st.button("Go to Contact Us"):
            st.session_state["scroll_to_contact"] = True
        if "scroll_to_contact" in st.session_state:
            if st.session_state["scroll_to_contact"]:
                contact_us_section()

    with col2:
        st.image("https://lh3.googleusercontent.com/3tEeGNkBJnXg0N9dJu7oumnaFtmUKCcZl-cOKlhAYBtE3VvqmDf0W9HFBHCVBEOoH4Szf9QpOlSrgBRL4q4vOYdll1_GHiVL1eE=w4000", width=360) 
    
    
    html_content = """
    <div style="background-color: #f1f7ff; padding: 20px; margin: 20px 20px 20px 20px; text-align:center;">
        <p>Embarking on a management journey requires insight, preparation, and the right fit.</p>
        <p>That's where we come in! Our Profile Evaluation Tool is designed to illuminate your path to success in the management realm.</p>
        <p>Just upload your resume or CV, and let us do the rest.</p>
        <p>What will you get? A comprehensive analysis tailored to your profile, showcasing how you align with various 
        management programs. It's straightforward, insightful, and completely tailored to you.</p>
    </div>
    """
    st.markdown(html_content, unsafe_allow_html=True)

       
    # Registration Form
    with st.form("registration_form"):
        name = st.text_input("Name")
        email = st.text_input("Email Address")
        mobile = st.text_input("Mobile Number")
        
        # Add more fields as per your PDF
        
        # Form submission button
        submitted = st.form_submit_button("Register")
        if submitted:
            st.success("Thanks for registering!")  # Placeholder for form submission

    # Buttons and Interactions
    if st.button("Analyze Profile"):
        with st.spinner('Analyzing...'):
            time.sleep(3)  # Simulate a long process
        st.success('Analysis Complete!')  # Post-analysis message

    # Footer
    st.markdown("### Contact Us")
    st.markdown("For support or queries, please contact info@example.com")

if __name__ == "__main__":
    main()
