function addRemoveButton(container) {
    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.textContent = "Remove";
    removeButton.className = "remove-btn";
    removeButton.onclick = function() {
        container.remove();
    };
    container.appendChild(removeButton);
}
function addKeywordInput() {
    const newInputContainer = document.createElement("div");
    newInputContainer.className = "keyword-input-container";
    newInputContainer.style.marginTop = "5px";  // Add some spacing for better visuals
    
    const newInput = document.createElement("input");
    newInput.type = "text";
    newInput.name = "keywords";  // Keep name="keywords" so Flask collects them as a list
    newInput.className = "keyword-input";
    newInput.placeholder = "Enter a keyword";
    newInput.style.marginTop = "5px";  // Add some spacing for better visuals  
    
    newInputContainer.appendChild(newInput);
    addRemoveButton(newInputContainer);
    // Append the new input to the container
    document.getElementById("keywords-container").appendChild(newInputContainer);
}
function addOutputInput(name ="", url = "") {
    const newInputContainer = document.createElement("div");
    newInputContainer.className = "outputs-container";
    newInputContainer.style.marginTop = "5px";  // Add some spacing for better visuals
    
    const newInputRow = document.createElement("div");
    newInputRow.className = "flex-row";
    const newInputLabel = document.createElement("div");
    newInputLabel.className = "form-label";
    newInputLabel.textContent = "Name:";
    const newInputDiv = document.createElement("div");
    newInputDiv.className = "flex-col input-col";
    const newInput = document.createElement("input");
    newInput.type = "text";
    newInput.name = "outputs";  
    newInput.value = name;
    newInput.className = "outputs-input";
    newInput.placeholder = "e.g. name of a product, service, etc.";
    newInput.style.marginTop = "5px";  // Add some spacing for better visuals
    newInputDiv.appendChild(newInput);
    newInputRow.appendChild(newInputLabel);
    newInputRow.appendChild(newInputDiv);

    const inputURLRow = document.createElement("div");
    inputURLRow.className = "flex-row";
    const inputURLLabel = document.createElement("div");
    inputURLLabel.className = "form-label";
    inputURLLabel.textContent = "URL:";
    const inputURLDiv = document.createElement("div");
    inputURLDiv.className = "flex-col input-col";
    const inputURL = document.createElement("input");
    inputURL.type = "text";
    inputURL.name = "outputs_url";
    inputURL.value = url;
    inputURL.className = "outputs-url";
    inputURL.placeholder = "url for product, service, etc.";
    inputURL.style.marginTop = "5px";
    inputURLDiv.appendChild(inputURL);
    inputURLRow.appendChild(inputURLLabel);
    inputURLRow.appendChild(inputURLDiv);
    
    newInputContainer.appendChild(newInputRow);
    newInputContainer.appendChild(inputURLRow);
    addRemoveButton(newInputContainer);
    // Append the new input to the container
    document.getElementById("outputs-container").appendChild(newInputContainer);
}
function addSOPInput(name ="", url = "", isOBPS = "") {
    const newInputContainer = document.createElement("div");
    newInputContainer.className = "sops-input-container";
    newInputContainer.style.marginTop = "5px";
    
    const sopNameRow = document.createElement("div"); // div boxes for pretty layout
    sopNameRow.className = "flex-row";
    const sopNameRowLabel = document.createElement("div");
    sopNameRowLabel.className = "form-label";
    sopNameRowLabel.textContent = "SOP Name:";
    const sopNameDiv = document.createElement("div");
    sopNameDiv.className = "flex-col input-col";
    const sopName = document.createElement("input");
    sopName.type = "text";
    sopName.name = "sops_name";  
    sopName.className = "sops-name"; 
    sopName.placeholder = "Name of SOP e.g. MarineGEO Seagrass Habitat Monitoring Protocol";
    sopName.value = name;
    sopName.style.marginTop = "5px";
    sopNameDiv.appendChild(sopName);
    sopNameRow.appendChild(sopNameRowLabel);
    sopNameRow.appendChild(sopNameDiv);
    
    const sopURLRow = document.createElement("div"); // div boxes for pretty layout
    sopURLRow.className = "flex-row";
    const sopURLRowLabel = document.createElement("div");
    sopURLRowLabel.className = "form-label";
    sopURLRowLabel.textContent = "SOP URL:";
    const sopURLDiv = document.createElement("div");
    sopURLDiv.className = "flex-col input-col";
    const sopURL = document.createElement("input");
    sopURL.type = "url";
    sopURL.name = "sops_url";  
    sopURL.className = "sops-url"; 
    sopURL.placeholder = "Link to SOP e.g. https://repository.oceanbestpractices.org/handle/11329/2465";
    sopURL.value = url;
    sopURL.style.marginTop = "5px";
    sopURLDiv.appendChild(sopURL);
    sopURLRow.appendChild(sopURLRowLabel);
    sopURLRow.appendChild(sopURLDiv);

    // Create the checkbox for OBPs  --> I've now removed this logic as it's not necessary. Links to OBPS should be obvious from the URL
    // const checkboxContainer = document.createElement("div");
    // checkboxContainer.style.marginTop = "5px";
    // checkboxContainer.style.display = "flex"; // Use flexbox to align items on the same line
    // checkboxContainer.style.alignItems = "center"; // Vertically align the checkbox and label

    // const checkbox = document.createElement("input");
    // checkbox.type = "checkbox";
    // checkbox.name = "sop_obps";
    // checkbox.value = "yes";
    // checkbox.id = `sop_obps_${Date.now()}`; // Unique ID for the checkbox

    // const checkboxLabel = document.createElement("label");
    // checkboxLabel.htmlFor = checkbox.id;
    // checkboxLabel.textContent = "Is this SOP included in the Ocean Best Practices System (OBPS)?";
    // checkboxLabel.style.marginLeft = "5px"; // Add some spacing between the checkbox and the label

    // // Append the checkbox and label to the container
    // checkboxContainer.appendChild(checkbox);
    // checkboxContainer.appendChild(checkboxLabel);

    newInputContainer.appendChild(sopNameRow);
    newInputContainer.appendChild(sopURLRow);
    //newInputContainer.appendChild(checkboxContainer);  / I have temporarily removed this line until confirming if this output is wanted
    // if (isOBPS === "yes") checkbox.checked = true;
    addRemoveButton(newInputContainer);

    document.getElementById("sops-container").appendChild(newInputContainer);
    }
function addContactInput(name = "", email = "", type = "", url = "") {
        // Create a new container for the contact
        const contactContainer = document.createElement("div");
        contactContainer.className = "contact-container";
        contactContainer.style.marginTop = "10px"; // Add spacing between pairs

        // Create the input for the contact type
        const typeRow = document.createElement("div"); // div boxes for pretty layout
        typeRow.className = "flex-row";
        const typeLabel = document.createElement("div");
        typeLabel.className = "form-label";
        typeLabel.textContent = "Contact Type:";
        const typeSelectDiv = document.createElement("div");
        typeSelectDiv.className = "flex-col input-col";
        const typeSelect = document.createElement("select");
        typeSelect.name = "contact_types";  // Flask will collect these as a list
        typeSelect.className = "contact-type-select";
        typeSelect.style.marginRight = "10px";
        typeSelect.required = true;

            // Add a default "Select contact type" option
        const defaultOption = document.createElement("option");
        defaultOption.value = ""; // Empty value
        defaultOption.textContent = "Select contact type";
        defaultOption.disabled = true; // Make it unselectable
        defaultOption.selected = !type; // Select this by default if no type is provided
        typeSelect.appendChild(defaultOption);

            // Add dropdown options
        const types = ["General Inquiries", "Technical Support", "Regional Support", "Helpdesk", "Principle Investigator", "Other"];
        types.forEach(optionType  => {
            const option = document.createElement("option");
            option.value = optionType ;
            option.textContent = optionType ;
            if (optionType === type) {
                option.selected = true; // Preselect the type
            }
            typeSelect.appendChild(option);
        });
        typeSelectDiv.appendChild(typeSelect);
        typeRow.appendChild(typeLabel);
        typeRow.appendChild(typeSelectDiv);

        // Create the input for the name of the contact
        const nameRow = document.createElement("div");
        nameRow.className = "flex-row";
        const nameLabel = document.createElement("div");
        nameLabel.className = "form-label";
        nameLabel.textContent = "Name:";
        const nameDiv = document.createElement("div");
        nameDiv.className = "flex-col input-col";
        const nameInput = document.createElement("input");
        nameInput.type = "text";
        nameInput.name = "contact_names";  // Flask will collect these as a list
        nameInput.className = "contact-name-input";
        nameInput.placeholder = "Enter contact name, e.g. Contact Us Page";
        nameInput.value = name;
        nameInput.style.marginRight = "10px"; // Add spacing between the two inputs
        nameInput.required = true;
        nameDiv.appendChild(nameInput);
        nameRow.appendChild(nameLabel);
        nameRow.appendChild(nameDiv);
    
        // Create the input for the contact email
        const emailRow = document.createElement("div");
        emailRow.className = "flex-row";
        const emailLabel = document.createElement("div");
        emailLabel.className = "form-label";
        emailLabel.textContent = "Email:";
        const emailDiv = document.createElement("div");
        emailDiv.className = "flex-col input-col";
        const emailInput = document.createElement("input");
        emailInput.type = "email";
        emailInput.name = "contact_emails";  // Flask will collect these as a list
        emailInput.className = "contact-email-input";
        emailInput.placeholder = "Enter contact email, e.g. helpdesk@company.org";
        emailInput.value = email;
        emailInput.required = false;
        emailDiv.appendChild(emailInput);
        emailRow.appendChild(emailLabel);
        emailRow.appendChild(emailDiv);

        // Create the input for the contact url
        const urlRow = document.createElement("div");
        urlRow.className = "flex-row";
        const urlLabel = document.createElement("div");
        urlLabel.className = "form-label";
        urlLabel.textContent = "URL:";
        const urlDiv = document.createElement("div");
        urlDiv.className = "flex-col input-col";
        const urlInput = document.createElement("input");
        urlInput.type = "url";
        urlInput.name = "contact_ids";  // Flask will collect these as a list
        urlInput.className = "contact-id-input";
        urlInput.placeholder = "Enter contact url, e.g. www.company.org/contact-us";
        urlInput.value = url;
        urlDiv.appendChild(urlInput);
        urlRow.appendChild(urlLabel);
        urlRow.appendChild(urlDiv);
    
        // Append both inputs to the contact container
        contactContainer.appendChild(typeRow);
        contactContainer.appendChild(nameRow);
        contactContainer.appendChild(emailRow);
        contactContainer.appendChild(urlRow);
        addRemoveButton(contactContainer);
        
    
        // Append the contact container to the main container
        document.getElementById("contacts-container").appendChild(contactContainer);
    }

function addFunders(name = "", url = "", award = "", identifier = "") {
        // Create a new container for the contact pair
        const funderContainer = document.createElement("div");
        funderContainer.className = "funder-container";
        funderContainer.style.marginTop = "10px"; // Add spacing between pairs
    
        // Create the input for the funder organization name
        const fundingOrgRow = document.createElement("div"); // div boxes for pretty layout
        fundingOrgRow.className = "flex-row";
        const fundingOrgLabel = document.createElement("div");
        fundingOrgLabel.className = "form-label";
        fundingOrgLabel.textContent = "Funding Organization:";
        const fundingOrgDiv = document.createElement("div");
        fundingOrgDiv.className = "flex-col input-col";
        const fundingOrg = document.createElement("input");
        fundingOrg.type = "text";
        fundingOrg.name = "funder_name";  // Flask will collect these as a list
        fundingOrg.className = "funder-name";
        fundingOrg.placeholder = "Funding organization name, e.g. European Union";
        fundingOrg.value = name;
        fundingOrg.style.marginRight = "10px"; // Add spacing between the two inputs
        fundingOrgDiv.appendChild(fundingOrg);
        fundingOrgRow.appendChild(fundingOrgLabel);
        fundingOrgRow.appendChild(fundingOrgDiv);

        // Create the input for the funder url
        const fundingURLRow = document.createElement("div"); // div boxes for pretty layout
        fundingURLRow.className = "flex-row";
        const fundingURLLabel = document.createElement("div");
        fundingURLLabel.className = "form-label";
        fundingURLLabel.textContent = "Funding URL:";
        const fundingURLDiv = document.createElement("div");
        fundingURLDiv.className = "flex-col input-col";
        const fundingURL = document.createElement("input");
        fundingURL.type = "url";
        fundingURL.name = "funder_url";  // Flask will collect these as a list
        fundingURL.className = "funder-url";
        fundingURL.placeholder = "Funding organization URL, e.g. https://european-union.europa.eu/";
        fundingURL.value = url;
        fundingURL.style.marginRight = "10px";
        fundingURLDiv.appendChild(fundingURL);
        fundingURLRow.appendChild(fundingURLLabel);
        fundingURLRow.appendChild(fundingURLDiv);

        // Create the input for the funder award
        const awardInputRow = document.createElement("div");
        awardInputRow.className = "flex-row";
        const awardInputLabel = document.createElement("div");
        awardInputLabel.className = "form-label";
        awardInputLabel.textContent = "Funding Award:";
        const awardInputDiv = document.createElement("div");
        awardInputDiv.className = "flex-col input-col";
        const awardInput = document.createElement("input");
        awardInput.type = "text";
        awardInput.name = "funding_name";  // Flask will collect these as a list
        awardInput.className = "funding-name";
        awardInput.placeholder = "Funding award name, e.g. Horizon Europe";
        awardInput.value = award;
        awardInput.style.marginRight = "10px";
        awardInputDiv.appendChild(awardInput);
        awardInputRow.appendChild(awardInputLabel);
        awardInputRow.appendChild(awardInputDiv);
        
        // Create the input for the funder identifer
        const identiferFundingRow = document.createElement("div");
        identiferFundingRow.className = "flex-row";
        const identiferFundingLabel = document.createElement("div");
        identiferFundingLabel.className = "form-label";
        identiferFundingLabel.textContent = "Funding Identifier:";
        const identiferFundingDiv = document.createElement("div");
        identiferFundingDiv.className = "flex-col input-col";
        const identiferFunding = document.createElement("input");
        identiferFunding.type = "text";
        identiferFunding.name = "funding_identifier";  // Flask will collect these as a list
        identiferFunding.className = "funding-identifier";
        identiferFunding.placeholder = "Funding award identifier number, e.g. 101136748";
        identiferFunding.value = identifier;
        identiferFunding.style.marginRight = "10px";
        identiferFundingDiv.appendChild(identiferFunding);
        identiferFundingRow.appendChild(identiferFundingLabel);
        identiferFundingRow.appendChild(identiferFundingDiv);

        // Append both inputs to the contact container
        funderContainer.appendChild(fundingOrgRow);
        funderContainer.appendChild(fundingURLRow);
        funderContainer.appendChild(awardInputRow);
        funderContainer.appendChild(identiferFundingRow);
        addRemoveButton(funderContainer);
    
        // Append the contact container to the main container
        document.getElementById("funder-container").appendChild(funderContainer);
    }