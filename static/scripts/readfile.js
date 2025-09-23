// Read uploaded file, preview of first 5 rows, convert to DwC on confirmation
document.getElementById("dataForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const headersEl = document.getElementById("headers");
    const dwcConfirm = document.getElementById("dwcConfirm");
    const dwcResults = document.getElementById("dwcResults");

    headersEl.innerHTML = "<p>Loading preview...</p>";
    dwcResults.innerHTML = "";
    dwcConfirm.classList.add("hidden");

    try {
        const response = await fetch("/process_file", { method: "POST", body: formData });
        const result = await response.json();

        if (result.error) {
            headersEl.innerHTML = `<p style="color:red;">Error: ${result.error}</p>`;
            return;
        }

        headersEl.innerHTML = "";
        for (const [sheet, data] of Object.entries(result.sheets)) {
            const sectionId = sheet.replace(/\W/g, "_"); // safe ID for toggle

            // Wrap everything in a toggleable preview section
            const wrapper = document.createElement("div");
            wrapper.classList.add("dwc-preview-section");

            // Toggle button
            const toggleBtn = document.createElement("button");
            toggleBtn.type = "button";
            toggleBtn.classList.add("toggle-btn");
            toggleBtn.textContent = `${sheet} (click to toggle preview)`;
            toggleBtn.onclick = () => {
                document.getElementById(sectionId).classList.toggle("hidden");
            };
            wrapper.appendChild(toggleBtn);

            // Content container (hidden by default)
            const contentDiv = document.createElement("div");
            contentDiv.id = sectionId;
            contentDiv.classList.add("hidden");

            // Table build
            const table = document.createElement("table");
            table.classList.add("preview-table");

            const thead = document.createElement("thead");
            const headerRow = document.createElement("tr");
            data.headers.forEach(h => { const th = document.createElement("th"); th.textContent = h; headerRow.appendChild(th); });
            thead.appendChild(headerRow);
            table.appendChild(thead);

            const tbody = document.createElement("tbody");
            data.rows.forEach(row => {
                const tr = document.createElement("tr");
                row.forEach(cell => { const td = document.createElement("td"); td.textContent = cell; tr.appendChild(td); });
                tbody.appendChild(tr);
            });
            table.appendChild(tbody);
            // Put table inside contentDiv
            contentDiv.appendChild(table);
            wrapper.appendChild(contentDiv);

            // Add to results
            headersEl.appendChild(wrapper);
        }

        dwcConfirm.classList.remove("hidden");
        document.getElementById("convertBtn").onclick = async () => {
            dwcResults.innerHTML = "<p>Processing DwC conversion...</p>";
            const dwcResponse = await fetch("/convert_to_dwc", { method: "POST", body: formData });
            const dwcResult = await dwcResponse.json();

            if (dwcResult.error) {
                dwcResults.innerHTML = `<p style="color:red;">Error: ${dwcResult.error}</p>`;
                return;
            }

            let previewsHtml = "";
            for (const [filename, preview] of Object.entries(dwcResult.previews)) {
                const sectionId = filename.replace(/\W/g, "_");
                previewsHtml += `
                    <div class="dwc-preview-section">
                        <button type="button" class="toggle-btn" onclick="document.getElementById('${sectionId}').classList.toggle('hidden')">
                            ${filename} (toggle preview)
                        </button>
                        <div id="${sectionId}" class="hidden">${preview}</div>
                    </div>
                `;
            }

            dwcResults.innerHTML = `
                <h3>Preview of converted DwC data (first 5 rows each)</h3>
                ${previewsHtml}
                <h3>Download all files:</h3>
                <a href="${dwcResult.files}" target="_blank">Download ZIP</a>
            `;
        };

    } catch (err) {
        headersEl.innerHTML = `<p style="color:red;">Unexpected error: ${err}</p>`;
    }
});
