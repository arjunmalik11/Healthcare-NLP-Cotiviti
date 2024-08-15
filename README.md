# Healthcare-NLP-Redacter

A Healthcare Natural Language Processing (NLP) solution focused on redacting Personally Identifiable Information (PII) and Protected Health Information (PHI) from medical documents. This repository provides a simple and effective way to ensure the privacy and security of sensitive health information using NLP techniques.

## Overview

This project implements a redaction pipeline that processes medical documents, identifies sensitive information (PII/PHI), and redacts it. The solution is designed to work with AWS services, integrating a Lambda function that gets triggered by file uploads to an S3 bucket. After redaction, the processed document is stored in another S3 bucket, and a summary of the redactions is generated using a generative AI model.

## Features

- **Automated Redaction**: Automatically redacts PII/PHI from uploaded medical documents.
- **Generative AI Summary**: Generates a summary explaining what information was redacted and why.
- **AWS Integration**: Uses AWS Lambda for serverless processing and S3 for file storage.
- **Streamlit Interface**: A simple user interface built with Streamlit for uploading documents, triggering the redaction process, and downloading the redacted documents.

## Usage

1. **Upload a PDF Document**:

   - Use the Streamlit interface to upload a PDF document to the S3 bucket.
   - This triggers the Lambda function that processes the document.

2. **Redaction Process**:

   - The Lambda function identifies and redacts PII/PHI from the document.
   - A summary of the redaction process is generated using an open-source generative AI model.

3. **Download Redacted Document**:
   - After processing, the redacted document is saved to another S3 bucket.
   - You can download the redacted document through the Streamlit interface.

## Project Structure

- **Lambda Function**: Contains the core redaction logic and integration with generative AI models for summaries.
- **Streamlit Interface**: Provides an easy-to-use web interface for document upload and download.
- **S3 Buckets**: Stores the original and redacted documents.

## Roadmap

- **Enhanced PII/PHI Detection**: Improve the accuracy and coverage of the redaction process.
- **Customizable Redaction**: Allow users to define specific types of information to redact.
- **Expanded Document Formats**: Support for additional document formats beyond PDF.
- **Extended Interface Features**: More functionality in the Streamlit interface, such as viewing the redaction summary directly on the platform.
