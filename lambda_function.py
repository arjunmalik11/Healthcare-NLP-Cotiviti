import json
import boto3
import urllib
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak

REGION = 'us-east-1'

s3 = boto3.client('s3', region_name=REGION)
textract = boto3.client('textract', region_name=REGION)
comprehend = boto3.client('comprehend', region_name=REGION)
comprehend_medical = boto3.client('comprehendmedical', region_name=REGION)
bedrock_runtime = boto3.client('bedrock-runtime', region_name=REGION)

def invoke_bedrock_model(redacted_text, model_id):
    prompt = f"""
You are a medical document summarizer. Analyze the following redacted text and provide a brief summary on what is redacted and why in a list manner:

{redacted_text}
Do not include any sensitive information and information not present in the provided text. Do not include any additional text, greetings, or signatures. Start directly with the list:

"""
    
    response = bedrock_runtime.invoke_model(
        modelId=model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps({
            "prompt": prompt,
            "temperature": 0.1,
        })
    )
    result = json.loads(response['body'].read().decode())['generation']
    return result

def generate_redacted_pdf(redacted_text, ai_summary):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY))
    story = []

    # Add redacted text
    story.append(Paragraph("Redacted Document:", styles['Heading1']))
    for line in redacted_text.split('\n'):
        story.append(Paragraph(line, styles['Normal']))
        story.append(Spacer(1, 6))  # Add a small space between lines

    # Add a page break
    story.append(PageBreak())

    # Add AI-generated summary with improved formatting
    story.append(Paragraph("AI-Generated Summary:", styles['Heading1']))
    
    # Process the AI summary
    summary_lines = ai_summary.strip().split('\n')
    for line in summary_lines:
        line = line.strip()
        if line.startswith('*'):
            # Format bullet points
            story.append(Paragraph(f"• {line[1:].strip()}", styles['BodyText']))
        else:
            # Format other lines (like the "Here is the summary:" line)
            story.append(Paragraph(line, styles['Normal']))
        story.append(Spacer(1, 6))
        
    # Build the PDF
    doc.build(story)
    buffer.seek(0)
    return buffer

def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event))
        bucket = event['Records'][0]['s3']['bucket']['name']
        raw_key = event['Records'][0]['s3']['object']['key']
        document_key = urllib.parse.unquote_plus(raw_key)
        
        print(f"Processing document: {document_key} from bucket: {bucket}")

        # Extract text using Textract
        response = textract.analyze_document(
            Document={'S3Object': {'Bucket': bucket, 'Name': document_key}},
            FeatureTypes=["FORMS"]
        )
        
        print("Textract Response:", json.dumps(response))
        
        text = extract_text_from_textract_response(response)
        
        if not text.strip():
            print("No text extracted from document")
            return {
                'statusCode': 400,
                'body': json.dumps('No text found in document.')
            }
        
        print("Extracted text:", text[:500] + "..." if len(text) > 500 else text)

        # Detect PII and PHI using Comprehend and Comprehend Medical
        pii_entities = detect_pii_entities(text)
        phi_entities = detect_phi_entities(text)
        
        # Redact detected information
        redacted_text = redact_information(text, pii_entities, phi_entities)
        
        print("Redacted text:", redacted_text[:500] + "..." if len(redacted_text) > 500 else redacted_text)

        # Invoke Bedrock model to generate a summary of the redacted content
        model_id = 'meta.llama3-8b-instruct-v1:0'
        ai_summary = invoke_bedrock_model(redacted_text, model_id)
        
        print("AI-generated summary:", ai_summary)

        # Generate the redacted PDF with summary
        final_pdf_stream = generate_redacted_pdf(redacted_text, ai_summary)

        # Save the final PDF to S3
        redacted_bucket = 'medical-redacted-documents'
        redacted_key = document_key.split('/')[-1].replace('.pdf', '_redacted.pdf')
        s3.upload_fileobj(final_pdf_stream, redacted_bucket, redacted_key)
        
        print(f"Successfully saved redacted PDF to {redacted_bucket}/{redacted_key}")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Document processed and redacted successfully.',
                'redacted_text': redacted_text,
                'ai_summary': ai_summary,
                'redacted_pdf_s3_path': f"s3://{redacted_bucket}/{redacted_key}"
            })
        }
    
    except Exception as e:
        print(f"Error processing document: {str(e)}")
        print(f"Event: {json.dumps(event)}")
        print(f"Context: {context}")
        import traceback
        print("Traceback:", traceback.format_exc())
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error processing document: {str(e)}")
        }

def extract_text_from_textract_response(response):
    text = ""
    if 'Blocks' not in response:
        print("No 'Blocks' found in Textract response")
        return text

    for item in response['Blocks']:
        if item['BlockType'] == 'LINE':
            line_text = item.get('Text', '').strip()
            if line_text:
                text += line_text + "\n"

    if not text:
        print("No text content found in Textract response")
        print("Response structure:", json.dumps(response, indent=2))

    return text

def detect_pii_entities(text):
    response = comprehend.detect_pii_entities(Text=text, LanguageCode='en')
    print("PII Entities:", json.dumps(response['Entities'], indent=2))
    return [entity for entity in response['Entities'] if entity['Score'] > 0.8]

def detect_phi_entities(text):
    response = comprehend_medical.detect_phi(Text=text)
    phi_entities = [entity for entity in response['Entities'] if entity['Score'] > 0.8]
    return phi_entities

def redact_information(text, pii_entities, phi_entities):
    all_entities = sorted(pii_entities + phi_entities, key=lambda x: x['BeginOffset'])
    redacted_text = ""
    last_end = 0

    for entity in all_entities:
        start = entity['BeginOffset']
        end = entity['EndOffset']
        
        if start > last_end:
            redacted_text += text[last_end:start]
        
        if start >= last_end:
            redacted_text += '[REDACTED]'
            last_end = end

    redacted_text += text[last_end:]
    
    return redacted_text