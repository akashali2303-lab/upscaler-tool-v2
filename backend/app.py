import os
import cv2
import numpy as np
import base64
from flask import Flask, request, jsonify
from flask_cors import CORS
from cv2 import dnn_superres

app = Flask(__name__)
# Allow CORS for all domains (simplifies deployment)
CORS(app)

# --- LOAD ENGINE ---
# We use FSRCNN (Fast) + Post-Processing (Quality)
sr = dnn_superres.DnnSuperResImpl_create()
model_path = "models/FSRCNN_x3.pb"

try:
    if os.path.exists(model_path):
        sr.readModel(model_path)
        sr.setModel("fsrcnn", 3)
        print("✅ Production Engine Loaded: Hybrid Mode")
    else:
        print(f"❌ Critical: Model not found at {model_path}")
        sr = None
except Exception as e:
    print(f"❌ Error loading model: {e}")
    sr = None

def professional_cleanup(image):
    """
    The 'Secret Sauce':
    1. Bilateral Filter: Smooths skin/noise while keeping edges sharp.
    2. Unsharp Mask: Pops the details.
    """
    # 1. Clean (Remove Grain)
    clean = cv2.bilateralFilter(image, d=5, sigmaColor=75, sigmaSpace=75)
    
    # 2. Sharpen (Add Detail)
    gaussian = cv2.GaussianBlur(clean, (0, 0), 3.0)
    sharp = cv2.addWeighted(clean, 1.5, gaussian, -0.5, 0)
    
    return sharp

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "active", "engine": "FSRCNN_Hybrid"}), 200

@app.route('/upscale', methods=['POST'])
def upscale_image():
    if sr is None: 
        return jsonify({"error": "Server Error: Model missing"}), 500
    
    if 'image' not in request.files: 
        return jsonify({"error": "No file uploaded"}), 400

    try:
        # Read Image
        file = request.files['image']
        nparr = np.frombuffer(file.read(), np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None: return jsonify({"error": "Invalid image file"}), 400

        # 1. PRE-PROCESS: Gentle Denoise
        img = cv2.fastNlMeansDenoisingColored(img, None, 3, 3, 7, 21)

        # 2. RESIZE LIMIT (Cloud Protection)
        # Render Free Tier has low RAM. Limit input to 1200px.
        h, w = img.shape[:2]
        max_dim = 1200
        if h > max_dim or w > max_dim:
            scale = max_dim / max(h, w)
            img = cv2.resize(img, (int(w*scale), int(h*scale)), interpolation=cv2.INTER_AREA)

        # 3. UPSCALE
        upscaled = sr.upsample(img)

        # 4. POST-PROCESS
        final_img = professional_cleanup(upscaled)

        # 5. ENCODE
        _, buffer = cv2.imencode('.jpg', final_img, [int(cv2.IMWRITE_JPEG_QUALITY), 98])
        img_str = base64.b64encode(buffer).decode('utf-8')

        return jsonify({
            "image": f"data:image/jpeg;base64,{img_str}",
            "old_res": f"{img.shape[1]}x{img.shape[0]}",
            "new_res": f"{final_img.shape[1]}x{final_img.shape[0]}"
        })

    except Exception as e:
        print(f"Processing Error: {e}")
        return jsonify({"error": "Processing Failed"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)