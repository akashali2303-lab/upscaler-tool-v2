import os
import cv2
import numpy as np
import base64
import sys
from flask import Flask, request, jsonify
from flask_cors import CORS
from cv2 import dnn_superres

app = Flask(__name__)

# --- FIX CORS (Allow Everything) ---
CORS(app, resources={r"/*": {"origins": "*"}})

# --- LOAD ENGINE ---
sr = dnn_superres.DnnSuperResImpl_create()
model_path = os.path.join(os.getcwd(), "models", "FSRCNN_x3.pb")

print(f"--> Loading AI Model from: {model_path}")

if os.path.exists(model_path):
    try:
        sr.readModel(model_path)
        sr.setModel("fsrcnn", 3)
        print("✅ AI Engine Loaded Successfully")
    except Exception as e:
        print(f"❌ Error initializing model: {e}")
        sr = None
else:
    print(f"❌ CRITICAL: Model file NOT found at {model_path}")
    print("Did you upload 'FSRCNN_x3.pb' to GitHub?")
    sr = None

def process_image(image):
    # 1. Denoise
    clean = cv2.bilateralFilter(image, d=5, sigmaColor=75, sigmaSpace=75)
    # 2. Sharpen
    gaussian = cv2.GaussianBlur(clean, (0, 0), 3.0)
    return cv2.addWeighted(clean, 1.5, gaussian, -0.5, 0)

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "Online", "model_loaded": sr is not None}), 200

@app.route('/upscale', methods=['POST', 'OPTIONS'])
def upscale_image():
    # Handle Preflight Request for CORS
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    if sr is None: 
        print("Error: Attempted upscale with no model loaded.")
        return jsonify({"error": "Server Error: AI Model file is missing on server."}), 500
    
    if 'image' not in request.files: 
        return jsonify({"error": "No file uploaded"}), 400

    try:
        print("--> Receiving Image...")
        file = request.files['image']
        nparr = np.frombuffer(file.read(), np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None: return jsonify({"error": "Invalid image format"}), 400

        # Resize logic to prevent RAM crash on free tier
        h, w = img.shape[:2]
        print(f"--> Image Size: {w}x{h}")
        
        max_dim = 1000
        if h > max_dim or w > max_dim:
            print("--> Resizing image to prevent memory crash...")
            scale = max_dim / max(h, w)
            img = cv2.resize(img, (int(w*scale), int(h*scale)), interpolation=cv2.INTER_AREA)

        print("--> Upscaling...")
        upscaled = sr.upsample(img)
        
        print("--> Enhancing...")
        final_img = process_image(upscaled)

        print("--> Encoding...")
        _, buffer = cv2.imencode('.jpg', final_img, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        img_str = base64.b64encode(buffer).decode('utf-8')

        print("✅ Success!")
        return jsonify({
            "image": f"data:image/jpeg;base64,{img_str}",
            "old_res": f"{img.shape[1]}x{img.shape[0]}",
            "new_res": f"{final_img.shape[1]}x{final_img.shape[0]}"
        })

    except Exception as e:
        print(f"❌ Processing Error: {e}")
        # Identify the error in the browser console
        return jsonify({"error": f"Internal Server Error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)