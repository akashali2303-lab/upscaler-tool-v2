import os
import cv2
import numpy as np
import base64
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime
from cv2 import dnn_superres

app = Flask(__name__)
CORS(app)

# MongoDB Setup (Uses Env Var or local fallback for testing)
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/upscaler_db")
try:
    client = MongoClient(MONGO_URI)
    db = client.get_database()
    history_collection = db.history
    print("Connected to MongoDB")
except Exception as e:
    print(f"MongoDB Connection Error: {e}")
    history_collection = None

# Initialize Super Resolution Model
sr = dnn_superres.DnnSuperResImpl_create()
model_path = "models/EDSR_x3.pb"
sr.readModel(model_path)
sr.setModel("edsr", 3) # Upscale by 3x

@app.route('/')
def home():
    return "Image Upscaler API is Running!"

@app.route('/upscale', methods=['POST'])
def upscale_image():
    if 'image' not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files['image']
    file_data = file.read()
    
    # Convert string data to numpy array
    nparr = np.frombuffer(file_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        return jsonify({"error": "Invalid image format"}), 400

    # UPSCALING PROCESS
    upscaled_img = sr.upsample(img)

    # Encode back to jpg
    _, buffer = cv2.imencode('.jpg', upscaled_img)
    img_str = base64.b64encode(buffer).decode('utf-8')

    # Save Metadata to MongoDB
    if history_collection is not None:
        history_collection.insert_one({
            "filename": file.filename,
            "timestamp": datetime.utcnow(),
            "original_size": img.shape,
            "upscaled_size": upscaled_img.shape
        })

    return jsonify({
        "message": "Upscaling successful", 
        "image": f"data:image/jpeg;base64,{img_str}",
        "old_res": f"{img.shape[1]}x{img.shape[0]}",
        "new_res": f"{upscaled_img.shape[1]}x{upscaled_img.shape[0]}"
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
