// CHANGE THIS URL AFTER DEPLOYING BACKEND TO RENDER
const BACKEND_URL = "https://YOUR-RENDER-APP-NAME.onrender.com"; 

const imageInput = document.getElementById('imageInput');
const statusText = document.getElementById('statusText');
const upscaleBtn = document.getElementById('upscaleBtn');

imageInput.addEventListener('change', function() {
    if (this.files && this.files[0]) {
        const reader = new FileReader();
        reader.onload = function(e) {
            document.getElementById('originalPreview').src = e.target.result;
            document.getElementById('resultContainer').style.display = 'flex';
        }
        reader.readAsDataURL(this.files[0]);
    }
});

async function uploadImage() {
    if (!imageInput.files[0]) {
        alert("Please select an image first.");
        return;
    }

    const formData = new FormData();
    formData.append("image", imageInput.files[0]);

    upscaleBtn.disabled = true;
    statusText.innerText = "Processing... This uses CPU so it might take 10-20 seconds.";

    try {
        // If testing locally, use http://localhost:5000/upscale
        // If deployed, use the Render URL
        const urlToUse = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
                         ? 'http://localhost:5000/upscale' 
                         : `${BACKEND_URL}/upscale`;

        const response = await fetch(urlToUse, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            document.getElementById('upscaledPreview').src = data.image;
            document.getElementById('downloadLink').href = data.image;
            document.getElementById('oldRes').innerText = data.old_res + " px";
            document.getElementById('newRes').innerText = data.new_res + " px";
            statusText.innerText = "Done!";
        } else {
            statusText.innerText = "Error: " + data.error;
        }
    } catch (error) {
        console.error("Error:", error);
        statusText.innerText = "Failed to connect to server.";
    } finally {
        upscaleBtn.disabled = false;
    }
}
