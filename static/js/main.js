console.log("JavaScript loaded!");

document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM Content Loaded!");
    const callForm = document.getElementById('callForm');
    const statusDisplay = document.getElementById('statusDisplay');
    
    if (!callForm) {
        console.error("Call form not found!");
    }
    if (!statusDisplay) {
        console.error("Status display not found!");
    }

    callForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const phoneNumber = document.getElementById('phoneNumber').value;
        const voice = document.getElementById('voice').value;
        const prompt = document.getElementById('prompt').value;

        try {
            statusDisplay.textContent = 'Initiating call...';
            
            const response = await fetch('/make-call', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    phone_number: phoneNumber,
                    voice: voice,
                    prompt: prompt
                })
            });

            const data = await response.json();
            
            if (response.ok) {
                statusDisplay.textContent = `Call initiated! SID: ${data.call_sid}`;
            } else {
                statusDisplay.textContent = `Error: ${data.error}`;
            }
        } catch (error) {
            statusDisplay.textContent = `Error: ${error.message}`;
        }
    });
}); 