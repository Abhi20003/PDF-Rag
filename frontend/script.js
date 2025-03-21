const serverUrl = "http://127.0.0.1:8000";

document.addEventListener("DOMContentLoaded", function () {
    // Hide loading popup
    let loadingPopup = document.getElementById("loadingPopup");
    if (loadingPopup) {
        loadingPopup.style.display = "none";
    }

    // Load stored PDF summaries from backend
    fetch(`${serverUrl}/get-all-summaries`)
        .then(response => {
            if (!response.ok) {
                throw new Error("Failed to fetch summaries");
            }
            return response.json();
        })
        .then(data => {
            data.forEach(pdf => {
                addNewPdfTab(pdf.pdf_name, pdf.summary);
            });
        })
        .catch(error => {
            console.error("Error fetching summaries:", error);
        });

    setTimeout(() => {
        // Remove active class from all tabs and panes
        document.querySelectorAll('.tab-pane').forEach(pane => {
            pane.classList.remove('show', 'active');
        });
        
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
        });
        
        // Make chat tab and section active
        const chatSection = document.getElementById('chatSection');
        const chatTab = document.getElementById('chat-tab');
        
        if (chatSection) chatSection.classList.add('show', 'active');
        if (chatTab) chatTab.classList.add('active');
    }, 100);
});

function showLoading() {
    let loadingPopup = document.getElementById("loadingPopup");
    if (loadingPopup) {
        loadingPopup.style.display = "block";
    }
}

function hideLoading() {
    let loadingPopup = document.getElementById("loadingPopup");
    if (loadingPopup) {
        loadingPopup.style.display = "none";
    }
}

function uploadFiles() {
    let files = document.getElementById("fileInput").files;
    if (files.length === 0) {
        alert("Please select at least one file.");
        return;
    }
    
    for (let file of files) {
        let formData = new FormData();
        formData.append("files", file);
        showLoading();

        fetch(`${serverUrl}/upload`, {
            method: "POST",
            body: formData
        })
        .then(response => response.json().then(data => ({ status: response.status, body: data })))
        .then(({ status, body }) => {
            hideLoading();
            let uploadStatus = document.getElementById("uploadStatus");

            if (status !== 200) {
                throw new Error(body.detail || "Unknown error occurred.");
            }

            uploadStatus.innerText = "Upload successful!";
            uploadStatus.style.color = "#4CAF50"; 
            setTimeout(() => { uploadStatus.innerText = ""; }, 10000);

            if (body.summary) {
                let pdfName = file.name;

                // Store the summary in the backend
                fetch(`${serverUrl}/store-summary`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ pdf_name: pdfName, summary: body.summary })
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error("Failed to store summary");
                    }
                    return response.json();
                })
                .then(data => {
                    addNewPdfTab(pdfName, body.summary);
                    
                    // Make sure chat tab is active after adding new tab
                    setTimeout(() => {
                        document.getElementById('chat-tab').click();
                    }, 100);
                })
                .catch(error => {
                    console.error("Error storing summary:", error);
                });
            }
        })
        .catch(error => {
            hideLoading();
            console.error("Error:", error);
            let uploadStatus = document.getElementById("uploadStatus");
            uploadStatus.innerText = "Upload failed: " + error.message;
            uploadStatus.style.color = "#FF5252"; // Red for errors

            setTimeout(() => { uploadStatus.innerText = ""; }, 10000);
        });
    }
}

function sendQuery() {
    let queryText = document.getElementById("queryInput").value.trim();
    if (!queryText) return;

    let chatbox = document.getElementById("chatbox");
    chatbox.innerHTML += `<p style="color: #BB86FC;"><strong>You:</strong> ${queryText}</p>`;
    document.getElementById("queryInput").value = "";

    let existingTypingIndicator = document.getElementById("typingIndicator");
    if (!existingTypingIndicator) {
        let typingIndicator = document.createElement("p");
        typingIndicator.id = "typingIndicator";
        typingIndicator.style.color = "#03DAC6"; 
        typingIndicator.innerHTML = '<strong>Bot:</strong> <span class="dots">...</span>';
        chatbox.appendChild(typingIndicator);
        chatbox.scrollTop = chatbox.scrollHeight;
    }

    fetch(`${serverUrl}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: queryText })
    })
    .then(response => response.json())
    .then(data => {
        let typingElement = document.getElementById("typingIndicator");
        if (typingElement) typingElement.remove();

        chatbox.innerHTML += `<p style="color: #4CAF50;"><strong>Bot:</strong> ${data.response}</p>`;
        chatbox.scrollTop = chatbox.scrollHeight;
    })
    .catch(error => {
        console.error("Error:", error);
        let typingElement = document.getElementById("typingIndicator");
        if (typingElement) typingElement.remove();

        chatbox.innerHTML += `<p style="color: #FF5252;"><strong>Bot:</strong> Error fetching response.</p>`;
        chatbox.scrollTop = chatbox.scrollHeight;
    });
}

function addNewPdfTab(pdfName, summary) {
    let tabContainer = document.querySelector(".nav.flex-column");
    let contentContainer = document.querySelector(".tab-content");

    // Check if this PDF tab already exists to avoid duplicates
    if (document.getElementById(`${pdfName}-tab`)) {
        return;
    }

    // Create new tab link
    let newTab = document.createElement("li");
    newTab.className = "nav-item";
    newTab.innerHTML = `<a class="nav-link" id="${pdfName}-tab" href="#${pdfName}-section" data-bs-toggle="pill">${pdfName}</a>`;
    tabContainer.appendChild(newTab);

    // Create new content section
    let newSection = document.createElement("div");
    newSection.className = "tab-pane fade";
    newSection.id = `${pdfName}-section`;
    newSection.innerHTML = `<h3>Summary</h3><p class="border p-3 bg-light">${summary}</p>`;
    contentContainer.appendChild(newSection);
}
