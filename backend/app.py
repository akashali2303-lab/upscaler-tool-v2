import os
import cv2
import numpy as np
import base64
from flask import Flask, request, jsonify
from flask_cors import CORS
from cv2 import dnn_superres

app = Flask(__name__)

# --- THE FIX: ALLOW ALL ORIGINS ---
# This tells the browser: "It is okay to talk to me from Vercel, Netlify, or Anywhere."
CORS(app, resources={r"/*": {"origins": "*"}})

# --- LOAD ENGINE ---
sr = dnn_superres.DnnSuperResImpl_create()
model_path = os.path.join(os.getcwd(), "models", "FSRCNN_x3.pb")

# Load model safely
if os.path.exists(model_path):
    try:
        sr.readModel(model_path)
        sr.setModel("fsrcnn", 3)
        print("✅ AI Engine Loaded")
    except Exception as e:
        print(f"❌ Model Error: {e}")
        sr = None
else:
    print(f"❌ Critical: Model not found at {model_path}")
    sr = None

def process_image(image):
    # Smooth out noise
    clean = cv2.bilateralFilter(image, d=5, sigmaColor=75, sigmaSpace=75)
    # Sharpen edges
    gaussian = cv2.GaussianBlur(clean, (0, 0), 3.0)
    return cv2.addWeighted(clean, 1.5, gaussian, -0.5, 0)

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "Active", "cors": "Enabled"}), 200

@app.route('/upscale', methods=['POST', 'OPTIONS'])
def upscale_image():
    # --- MANUAL CORS HANDLING (Double Security) ---
    # If the browser asks "Can I upload?", we say "YES" immediately.
    if request.method == 'OPTIONS':
        response = jsonify({'message': 'OK'})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "*")
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        return response, 200

    if sr is None: return jsonify({"error": "Server Error: Model missing"}), 500
    if 'image' not in request.files: return jsonify({"error": "No file uploaded"}), 400

    try:
        file = request.files['image']
        nparr = np.frombuffer(file.read(), np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None: return jsonify({"error": "Invalid image"}), 400

        # Resize limit
        h, w = img.shape[:2]
        max_dim = 1200
        if h > max_dim or w > max_dim:
            scale = max_dim / max(h, w)
            img = cv2.resize(img, (int(w*scale), int(h*scale)), interpolation=cv2.INTER_AREA)

        # Upscale
        upscaled = sr.upsample(img)
        final_img = process_image(upscaled)

        # Encode
        _, buffer = cv2.imencode('.jpg', final_img, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        img_str = base64.b64encode(buffer).decode('utf-8')

        # Send response with explicit CORS headers
        response = jsonify({
            "image": f"data:image/jpeg;base64,{img_str}",
            "old_res": f"{img.shape[1]}x{img.shape[0]}",
            "new_res": f"{final_img.shape[1]}x{final_img.shape[0]}"
        })
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "Processing Failed"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)