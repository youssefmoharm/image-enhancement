from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
import cv2
import numpy as np
from PIL import Image
import base64
import io
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Serve static files
@app.route('/<path:path>')
def serve_file(path):
    return send_from_directory('.', path)

# Serve auth page as index
@app.route('/')
def serve_index():
    return send_from_directory('.', 'auth.html')

# Serve main application page
@app.route('/app')
def serve_app():
    return send_from_directory('.', 'index2.html')

# Serve authentication page
@app.route('/auth')
def serve_auth():
    return send_from_directory('.', 'auth.html')

# Image enhancement functions
def apply_histogram_equalization(image):
    img_array = np.array(image)
    if len(img_array.shape) == 2:
        equalized = cv2.equalizeHist(img_array)
        return Image.fromarray(cv2.cvtColor(equalized, cv2.COLOR_GRAY2RGB))
    else:
        img_yuv = cv2.cvtColor(img_array, cv2.COLOR_RGB2YUV)
        img_yuv[:,:,0] = cv2.equalizeHist(img_yuv[:,:,0])
        equalized = cv2.cvtColor(img_yuv, cv2.COLOR_YUV2RGB)
        return Image.fromarray(equalized)

def apply_gaussian_blur(image):
    img_array = np.array(image)
    blurred = cv2.GaussianBlur(img_array, (5, 5), 0)
    return Image.fromarray(blurred)

def apply_sharpening(image):
    img_array = np.array(image)
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharpened = cv2.filter2D(img_array, -1, kernel)
    return Image.fromarray(sharpened)

def apply_edge_detection(image):
    img_array = np.array(image)
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 100, 200)
    return Image.fromarray(cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB))

def apply_complement(image):
    img_array = np.array(image)
    complement = 255 - img_array
    return Image.fromarray(complement)

# Handle image enhancement
@app.route('/api/enhance', methods=['POST'])
def enhance_image():
    try:
        data = request.json
        image_data = data['image'].split(',')[1]  # Remove the data URL prefix
        enhancement_type = data['enhancement']
        
        # Convert base64 to image
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        
        # Apply enhancement
        if enhancement_type == 'histogram':
            enhanced = apply_histogram_equalization(image)
        elif enhancement_type == 'gaussian':
            enhanced = apply_gaussian_blur(image)
        elif enhancement_type == 'sharpening':
            enhanced = apply_sharpening(image)
        elif enhancement_type == 'edge':
            enhanced = apply_edge_detection(image)
        elif enhancement_type == 'complement':
            enhanced = apply_complement(image)
        else:
            return jsonify({"error": "Invalid enhancement type"}), 400
        
        # Convert back to base64
        buffered = io.BytesIO()
        enhanced.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        # Update user's enhancement history if user is logged in
        if 'email' in data:
            try:
                with open('users.json', 'r') as f:
                    users = json.load(f)
                if data['email'] in users:
                    users[data['email']]['enhancement_count'] += 1
                    if enhancement_type not in users[data['email']]['enhancement_types']:
                        users[data['email']]['enhancement_types'].append(enhancement_type)
                    users[data['email']]['enhancement_history'].append({
                        "technique": enhancement_type,
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    with open('users.json', 'w') as f:
                        json.dump(users, f, indent=4)
            except Exception as e:
                print("Error updating user history:", str(e))
        
        return jsonify({"enhanced_image": f"data:image/png;base64,{img_str}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Handle user registration
@app.route('/users.json', methods=['POST'])
def register_user():
    try:
        users = {}
        if os.path.exists('users.json'):
            with open('users.json', 'r') as f:
                users = json.load(f)
        
        new_data = request.json
        users.update(new_data)
        
        with open('users.json', 'w') as f:
            json.dump(users, f, indent=4)
        
        return jsonify({"message": "Success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Handle user data retrieval
@app.route('/users.json', methods=['GET'])
def get_users():
    try:
        if os.path.exists('users.json'):
            with open('users.json', 'r') as f:
                users = json.load(f)
            return jsonify(users)
        return jsonify({})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=8000, debug=True) 