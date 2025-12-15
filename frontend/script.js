// Render URL will go here later
// Make sure to add /upscale at the end!
let API_URL = "https://upscaler-tool-v2.onrender.com/upscale";

const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const actionBtn = document.getElementById('actionBtn');
const statusMsg = document.getElementById('statusMsg');
const loading = document.getElementById('loading');
const resultArea = document.getElementById('resultArea');

// Handle Drag & Drop
dropZone.onclick = () => fileInput.click();
fileInput.onchange = () => handleFile(fileInput.files[0]);

dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.style.borderColor = '#00f2fe'; });
dropZone.addEventListener('dragleave', (e) => { e.preventDefault(); dropZone.style.borderColor = 'rgba(255,255,255,0.1)'; });
dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.style.borderColor = 'rgba(255,255,255,0.1)';
    handleFile(e.dataTransfer.files[0]);
});

function handleFile(file) {
    if (file && file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = (e) => {
            document.getElementById('prevOriginal').src = e.target.result;
            statusMsg.innerText = `Selected: ${file.name}`;
            actionBtn.disabled = false;
            resultArea.style.display = 'none';
        }
        reader.readAsDataURL(file);
    }
}

actionBtn.onclick = async () => {
    const file = fileInput.files[0] || document.getElementById('fileInput').files[0]; // fallback
    if (!file) return;

    // Detect if we are on the deployed site
    if (window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1") {
        API_URL = "https://upscaler-tool-v2.onrender.com"; // You will update this later
    }

    const formData = new FormData();
    formData.append("image", file);

    actionBtn.disabled = true;
    actionBtn.innerText = "Enhancing...";
    loading.style.display = 'block';
    statusMsg.innerText = "AI is removing noise and sharpening details...";

    try {
        const response = await fetch(API_URL, { method: 'POST', body: formData });
        const data = await response.json();

        if (response.ok) {
            document.getElementById('prevEnhanced').src = data.image;
            document.getElementById('downloadBtn').href = data.image;
            document.getElementById('metaOriginal').innerText = data.old_res;
            document.getElementById('metaEnhanced').innerText = data.new_res;
            
            resultArea.style.display = 'block';
            statusMsg.innerText = "Enhancement Complete!";
            resultArea.scrollIntoView({ behavior: 'smooth' });
        } else {
            statusMsg.innerText = "Error: " + data.error;
        }
    } catch (error) {
        console.error(error);
        statusMsg.innerText = "Connection Failed. Is backend running?";
    } finally {
        loading.style.display = 'none';
        actionBtn.disabled = false;
        actionBtn.innerText = "Start Enhancement";
    }
};