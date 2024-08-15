import streamlit as st
import time
import os
from typing import Optional

# Global variable to hold the S3 client
s3_client = None

def get_s3_client():
    global s3_client
    if s3_client is None:
        import boto3
        from botocore.exceptions import NoCredentialsError
        try:
            s3_client = boto3.client('s3',
                aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
                aws_session_token=os.environ.get('AWS_SESSION_TOKEN'),
                region_name=os.environ.get('AWS_REGION', 'us-east-1')
            )
        except NoCredentialsError:
            st.error("No AWS credentials found. Please set up your AWS credentials.")
    return s3_client

# S3 bucket names
input_bucket = os.environ.get('INPUT_BUCKET', 'medical-non-redacted-documents')
output_bucket = os.environ.get('OUTPUT_BUCKET', 'medical-redacted-documents')

def upload_to_s3(file, bucket: str, object_name: str) -> bool:
    s3 = get_s3_client()
    if s3 is None:
        return False
    try:
        s3.upload_fileobj(file, bucket, object_name)
        return True
    except Exception as e:
        st.error(f"Error uploading file: {e}")
        return False

def check_processed_file(bucket: str, object_name: str) -> bool:
    s3 = get_s3_client()
    if s3 is None:
        return False
    try:
        s3.head_object(Bucket=bucket, Key=object_name)
        return True
    except:
        return False

def get_pdf_content(bucket: str, object_name: str) -> Optional[bytes]:
    s3 = get_s3_client()
    if s3 is None:
        return None
    try:
        response = s3.get_object(Bucket=bucket, Key=object_name)
        return response['Body'].read()
    except Exception as e:
        st.error(f"Error retrieving PDF content: {e}")
        return None

def main():
    st.set_page_config(page_title="Medical Document Redactor", layout="wide")

    # Custom CSS
    st.markdown("""
    <style>
    .stApp {
        background-color: #1E1E1E;
        color: #FFFFFF;
    }
    .stButton>button {
        color: #FFFFFF;
        background-color: #FF69B4;
        border-radius: 25px;
        border: 2px solid #FF69B4;
        padding: 10px 24px;
        font-size: 16px;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #FF1493;
        border-color: #FF1493;
    }
    .css-1d391kg {
        background-color: #000080;
    }
    .stDownloadButton>button {
        color: #FFFFFF;
        background-color: #FF69B4;
        border-radius: 25px;
        border: 2px solid #FF69B4;
        padding: 10px 24px;
        font-size: 16px;
        transition: all 0.3s;
    }
    .stDownloadButton>button:hover {
        background-color: #FF1493;
        border-color: #FF1493;
    }
    .custom-box {
        background-color: #2E2E2E;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
    }
    .title {
        color: #FF69B4;
        font-size: 48px;
        font-weight: bold;
        text-align: center;
        margin-bottom: 30px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<h1 class='title'>Medical Document Redactor</h1>", unsafe_allow_html=True)
    
    st.markdown("<div class='custom-box'>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    
    if uploaded_file is not None:
        if st.button("Upload & Process"):
            if upload_to_s3(uploaded_file, input_bucket, uploaded_file.name):
                with st.spinner("...."):
                    processed_file_name = uploaded_file.name.replace('.pdf', '_redacted.pdf')
                    
                    for _ in range(60):  # Wait up to 60 seconds
                        if check_processed_file(output_bucket, processed_file_name):
                            st.success("File Redacted!")
                            
                            pdf_content = get_pdf_content(output_bucket, processed_file_name)
                            if pdf_content:
                                st.download_button(
                                    label="Download Redacted PDF",
                                    data=pdf_content,
                                    file_name=processed_file_name,
                                    mime="application/pdf",
                                    key="download_button"
                                )
                            else:
                                st.error("Failed to retrieve PDF content for download.")
                            break
                        time.sleep(1)
                    else:
                        st.warning("Processing is taking longer than expected. Please check back later or refresh the page.")
    st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()