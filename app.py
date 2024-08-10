from flask import Flask, request, render_template, jsonify
import boto3
from botocore.exceptions import NoCredentialsError
import os
import base64

app = Flask(__name__)

# AWS region and bucket name
REGION = 'us-west-2'
BUCKET_NAME = 'Anshupsp'

# Initialize boto3 client for S3 and Rekognition
s3_client = boto3.client('s3', region_name=REGION)
rekognition_client = boto3.client('rekognition', region_name=REGION)

def list_images_in_s3(bucket_name):
    """List all images in the specified S3 bucket."""
    try:
        response = s3_client.list_objects_v2(Bucket=bucket_name)
        if 'Contents' in response:
            return [obj['Key'] for obj in response['Contents']]
        else:
            return []
    except NoCredentialsError:
        print("Credentials not available.")
        return []

def compare_faces(source_image, target_image):
    """Compare faces between the source and target images."""
    response = rekognition_client.compare_faces(
        SourceImage={'S3Object': {'Bucket': BUCKET_NAME, 'Name': source_image}},
        TargetImage={'S3Object': {'Bucket': BUCKET_NAME, 'Name': target_image}},
        SimilarityThreshold=90  # Adjust the similarity threshold as needed
    )
    return response

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_image():
    data = request.json
    image_data = data['image']
    image_bytes = base64.b64decode(image_data.split(',')[1])
    
    uploads_dir = os.path.join(app.instance_path, 'uploads')
    os.makedirs(uploads_dir, exist_ok=True)
    file_path = os.path.join(uploads_dir, 'captured_image.png')
    
    with open(file_path, 'wb') as file:
        file.write(image_bytes)
    
    s3_client.upload_file(file_path, BUCKET_NAME, 'captured_image.png')
    os.remove(file_path)
    
    s3_images = list_images_in_s3(BUCKET_NAME)
    for s3_image in s3_images:
        if s3_image == 'captured_image.png':
            continue
        response = compare_faces('captured_image.png', s3_image)
        if response['FaceMatches']:
            return jsonify({"status": "Person authorized", "redirect": "/chat"})
    
    return jsonify({"status": "Person not authorized", "redirect": None})

@app.route('/chat')
def chat():
    return render_template('chat.html')

@app.route('/chat', methods=['POST'])
def chat_with_bot():
    data = request.json
    user_message = data['message']

    # Lex bot configuration
    LEX_BOT_NAME = 'Maya-AI'
    LEX_BOT_ALIAS = 'mayaAlias'
    LEX_BOT_USER_ID = 'User123'

    lex_client = boto3.client('lexV2-runtime', region_name='us-east-1')
    
    try:
        response = lex_client.post_text(
            botName=LEX_BOT_NAME,
            botAlias=LEX_BOT_ALIAS,
            userId=LEX_BOT_USER_ID,
            inputText=user_message
        )
        bot_response = response['message']
    except Exception as e:
        print(f"Error interacting with Lex bot: {e}")
        bot_response = "Sorry, there was an error processing your request."

    return jsonify({"response": bot_response})

if __name__ == "__main__":
    app.run(debug=True)
