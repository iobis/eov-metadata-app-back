import json
import re

def get_first_or_str(val):
    # """Return a string representation of the first element if val is a list, set, or dict; else return val as string."""
    if isinstance(val, list) and val:
        return str(val[0])
    elif isinstance(val, set) and val:
        return str(next(iter(val)))
    elif isinstance(val, dict) and val:
        # If dict has a 'name' or 'url' key, use it; else use the first value
        for key in ['name', 'url']:
            if key in val:
                return get_first_or_str(val[key])
        return str(next(iter(val.values())))
    return str(val)

def generate_form(prefilled_data=None, actions_data=None, frequency_data=None):
    with open("schema.json") as f:
        form_schema = json.load(f)

        form_html = ""
        prefilled_data = prefilled_data or {}
        actions_data = actions_data or {}
        frequency_data = frequency_data or {}
        print(f"Prefilled data: {json.dumps(prefilled_data, indent=4)}")
        print(f"Actions data: {json.dumps(actions_data, indent=4)}")
        print(f"Frequency data: {json.dumps(frequency_data, indent=4)}")

        form_html += """
        <h2>General Information</h2>
        """
        ### Data Producer Name ###
        form_html += f"""
        Data producers may include monitoring programs, projects, institutions, etc.
        <div class="flex-row">
            <div class="form-label">
                <h4><label for='project_name'>Data Producer Name:<span class="required">*</span><span class="info-circle" data-tooltip="Enter the full name or title of the data producer. Data producers may include monitoring programs, projects, institutions, etc.">ⓘ</span></label></h4>
            </div>
            <div class="flex-col input-col">
                <input type='text' name='project_name' id='project_name' value="{prefilled_data.get('legalName', '')}" placeholder="Co-Creating Transformative Pathways to Biological and Ecosystem Ocean Observations" required>
                <div class='previous'><strong>Previously entered:</strong> {prefilled_data.get('legalName', 'N/A')}</div>
            </div>
        </div>
        <br>
        """
        ### Data Producer Acronym ###
        form_html += f"""
        <div class="flex-row">
            <div class="form-label">
                <h4><label for='shortname'>Data Producer Acrynom:<span class="info-circle" data-tooltip="Enter the short name or acrynom of the data producer.">ⓘ</span></label></h4>
            </div>
            <div class="flex-col input-col">
                <input type='text' name='shortname' id='shortname' value="{prefilled_data.get('name', '')}" placeholder="BioEcoOcean">
                <div class='previous'><strong>Previously entered:</strong> {prefilled_data.get('name', 'N/A')}</div>
            </div>
        </div>
        <br>
        """
        ### URL ###
        form_html += f"""
        <div class="flex-row">
            <div class="form-label">
                <label for='url'>URL:<span class="required">*</span><span class="info-circle" data-tooltip="Provide the URL to the homepage for the data producer.">ⓘ</span></label>
            </div>
            <div class="flex-col input-col">
                <input type='url' name='url' id='url' value="{prefilled_data.get('url', '')}" placeholder="https://bioecoocean.org/" required>
                <div class='previous'><strong>Previously entered:</strong> {prefilled_data.get('url', 'N/A')}</div>
            </div>
        </div>
        <br>
        """
        ### Project ID ###
        form_html += f"""
        <div class="flex-row">
            <div class="form-label">
                <label for='projid'>Data producer ID:<span class="info-circle" data-tooltip="Provide the ID for the entity producing EOV data, e.g. project, institution, programme, etc. IDs could include a Research Activity Identifier (RAiD), or Research Organization Registry identifier (ROR ID). If you do not currently have one it can be added later. The ID will facilitate connecting the data producer metadata with other outputs e.g. datasets in OBIS">ⓘ</span></label>
            </div>
            <div class="flex-col input-col">
                <input type='text' name='projid' id='projid' value="{prefilled_data.get('identifier', {}).get('url', '')}" placeholder="e.g. a RAiD, or ROR ID">
                <div class='previous'><strong>Previously entered:</strong> {prefilled_data.get('identifier', {}).get('url', 'N/A')}</div>
            </div>
        </div>
        """
        identifier_types = form_schema.get("identifier_types", {})
        projid_type_value = prefilled_data.get('identifier', {}).get('description', '')

        form_html += f"""
        <div class="flex-row">
            <div class="form-label">
                Identifier Type:
            </div>
            <div class="flex-col input-col">
                <select name='projid_type' id='projid_type'>
                <option value='' disabled selected>Select type</option>
        """
        for key, info in identifier_types.items():
            selected = "selected" if projid_type_value == key else ""
            form_html += f"<option value='{key}' {selected}>{info['name']}</option>"
        form_html += """
                </select>
                <div class='previous'><strong>Previously entered:</strong> {}</div>
                <a> If your desired type is not listed, please contact us to have it added. To generate a DOI for your entry, click the button and fill the form below, ten copy the generated DOI into the field above. Some fields may have been prepopulated for you using information in the form. Please confirm data is correct before creating your DOI. Contact helpdesk@obis.org to correct or update information.</a>
            
        """.format(projid_type_value if projid_type_value else "N/A")
        # Add DataCite button
        form_html += f"""
        <button type="button" id="generate-doi-btn" onclick="toggleDoiForm()" style="width: 40%;">Generate DOI</button></div>
        </div>
        <div id="doi-form-container" style="display: none; border: 1px solid #ccc; padding: 1px 15px; margin: 10px 0; background-color: #f9f9f9;">
            <h3>DOI Information</h3>
            <h4>Title</h4>
            The title by which the resource is known.
            <input type="text" id="doi-title" name="doi-title" placeholder="Title for the DOI" style="width: 100%; margin: 5px 0;">
            
            <h4>URL</h4>           
            The location of the landing page with more information about the resource.
            <input type="url" id="doi-url" name="doi-url" placeholder="https://example.com" style="width: 100%; margin: 5px 0;">
            
            <h4>Creator</h4>
            The main researchers or organizations involved in producing the resource, in priority order.
            <div id="creators-container">
                <!-- Creators will be added here dynamically -->
            </div>
            <button type="button" onclick="addCreator()">Add Creator</button>          
            
            <h4>Publisher</h4>
            The name of the entity that holds, archives, publishes prints, distributes, releases, issues, or produces the resource.
            <input type="text" id="doi-publisher" name="doi-publisher" placeholder="Publisher Name" style="width: 100%; margin: 5px 0;">
            
            <button type="button" id="submit-doi-btn" onclick="submitDoiRequest()">Create DOI</button>
            <button type="button" onclick="toggleDoiForm()">Cancel</button>
        </div><br>
        <span id="doi-result"></span><br>
        """

        ### Description ###
        form_html += f"""
        <div class="flex-row">
            <div class="form-label">
                <label for='description'>Description: <span class="info-circle" data-tooltip="Provide a brief description of the project.">ⓘ</span></label>
            </div>
            <div class="flex-col input-col">
                <textarea name='description' id='description' maxlength="2000" placeholder="BioEcoOcean was funded by the European Union under grant agreement No. 101136748 with 5.7 million EUR to address this challenge. Over the course of 4 years, from February 2024 to January 2027, a consortium of 9 European partners aims to create, and demonstrate the value of, a globally applicable Blueprint for Integrated Ocean Science (BIOS).">{prefilled_data.get('description', '')}</textarea>
                <div class='previous'><strong>Previously entered:</strong> {prefilled_data.get('description', 'N/A')}</div>
            </div>
        </div><br>
        """

        # Parent organization
        form_html += f"""
        <label for='parentOrganization'>Parent Organization: <span class="info-circle" data-tooltip="Provide the name and URL of the parent or administering organization, if applicable.">ⓘ</span></label>
        
        <div class="flex-row">
            <div class="form-label">
                Name: 
            </div>
            <div class="flex-col input-col">
                <input type='text' name='parentOrganization' id='parentOrganization' value="{prefilled_data.get('parentOrganization.legalName', '')}" placeholder="Argo">
                <div class='previous'><strong>Previously entered:</strong> {prefilled_data.get('parentOrganization.legalName', 'N/A')}</div>
            </div>
        </div>
        
        <div class="flex-row" style="max-width:100%;align-items: baseline; justify-content: left">
            <div class="form-label">
                URL:                 
            </div>
            <div class="flex-col input-col">
                <input type='text' name='parentOrganization_url' id='parentOrganization_url' value="{prefilled_data.get('parentOrganization.url', '')}" placeholder="https://argo.ucsd.edu/about/">
                <div class='previous'><strong>Previously entered:</strong> {prefilled_data.get('parentOrganization.url', 'N/A')}</div>
            </div>
        </div><br>
        """

        ### Keywords Section ###
        #Get EOV names to filter against - note that I need to check there's not overlap with EOV section
        variable_measured_fields = form_schema["categories_definition"]["variable_measured"]["fields"]
        eov_names = set()
        for field in variable_measured_fields.values():
            if "options" in field:
                eov_names.update(option["name"] for option in field["options"].values())

        keywords = prefilled_data.get("keywords", [])
        # Filter keywords
        true_keywords = [kw for kw in keywords if kw.get("name") not in eov_names]
        print("True Keywords: ", true_keywords, flush=True)
        keywords_display = ", ".join([keyword["name"] for keyword in true_keywords if "name" in keyword]) if true_keywords else "N/A"
        form_html += f"""
        <div class="flex-row">
            <div class="form-label">
                <label for='keywords'>Keywords: <span class='info-circle' data-tooltip='Enter relevant keywords from controlled vocabulary collections for the data producer.'>ⓘ</span></label>
            </div>
            <div class="flex-col input-col">
                <div class="search-container">
                    <input type="text" id="ontology-search" name="ontology_term" placeholder="Search using a minimum of 3 characters, e.g. 'coral', 'sea', etc." autocomplete="off">
                    <button type="button" id="ontology-search-btn">Search</button>
                    <div class='previous'><strong>Previously entered: </strong>{keywords_display}</div>
                    <div style="max-width: 90%;">Type in the box above to search for a keyword from a controlled vocabulary collection. This will query both The Environment Ontology (ENVO) and the BODC NERC Vocabulary Server. Please confirm a keyword is relevant by clicking the associated link and reading its definition. Selected keywords will be populated in the box below.</div><br>
                </div>
            </div>
        </div>

        <!-- Results Table -->
        <div class="table-scroll">
        <table id="results-table" class="scrollable-table" style="display:none;">
            <thead>
                <tr>
                    <th>Keyword</th>
                    <th>URL</th>
                    <th>Source</th>
                </tr>
            </thead>
            <tbody>
                <!-- Dynamically populated rows will go here -->
            </tbody>
        </table>
        </div>
        <div class="flex-row" style="align-items: anchor-center">
            <div class="form-label">
                <p style="font-style:italic">Selected Keywords:<p>
            </div>
            <div class="flex-col input-col">
                <div id="selected-keywords-list" class="selected-keywords-list">
                <!-- Selected keywords will appear here -->
                </div>
            </div>
        </div>
        <input type="hidden" id="selected-keywords-json" name="selected-keywords-json" value="">
        <br>
        """
        # prefill only true keywords
        if true_keywords:
            for kw in true_keywords:
                label = kw.get("name", "")
                url = kw.get("url", "")
                source = kw.get("source", "")
                obo_id = kw.get("termCode", "")
                form_html += f"""
                <script>
                    document.addEventListener("DOMContentLoaded", function() {{
                        addSelectedKeyword("{label}", "{url}", "{source}", "{obo_id}");
                    }});
                </script>
                """

        ### License section ###
        license_field = form_schema.get("categories_definition", {}).get("license", None)
        if license_field:
            license_value = prefilled_data.get("publishingPrinciples", {}).get("name", 'N/A')

            # Show previously entered value above the field
            form_html += f"""
            <div class="flex-row">
                <div class="form-label">
                    <label for='license'>{license_field['name']}:<span class='info-circle' data-tooltip='Select the most appropriate license(s) for the data produced.'>ⓘ</span></label>
                </div>
                <div class="flex-col input-col">
                    <select name='license' id='license' multiple size=4 style="height:125px">
            """
            #form_html += "<option value='' selected>Select option</option>"
            for option_key, option in license_field['options'].items(): #option_key is necessary to get the key from schema
                selected = "selected" if option['name'] == license_value else ""
                form_html += f"<option value='{option['name']}|{option['url']}' {selected}>{option['name']}</option>"
            form_html += f"""
                    </select>
                    <div class='previous'><strong>Previously entered:</strong> {license_value if license_value else 'N/A'}</div>
                    <div style="max-width: 90%;">Please select which <a href='https://creativecommons.org/share-your-work/cclicenses/'>Creative Commons license</a> you expect the data produced by your entry to adhere to. Select as many as applicable. If none of the licenses above apply, and/or you would like to provide the link to an organizational policy, please optionally fill in the fields below.</div>
                </div>
                </div>
                """
        else:
            # Handle the case where 'license' is missing
            form_html += "<p><strong>Error: License field is missing in the schema.</strong></p>"
        
        # Specific policy statements
        form_html += f"""
        <div class="flex-row">
            <div class="form-label">
                Policy Name:
            </div>
            <div class="flex-col input-col">
                <input type="text" name="datapolicy_name" id='datapolicy_name' placeholder="Name of policy, e.g. IOC Data Policy and Terms of Use (2023)">
            </div>
        </div>
        <div class="flex-row">
            <div class="form-label">
                Description:
            </div>
            <div class="flex-col input-col">
                <input type="text" name="datapolicy_text" id='datapolicy_text' placeholder="Brief description of policy">
            </div>
        </div>
        <div class="flex-row">
            <div class="form-label">
                Policy URL:
            </div>
            <div class="flex-col input-col">
                <input type="text" name="datapolicy_url" id='datapolicy_url' placeholder="URL pointing to policy, e.g. https://iode.org/resources/ioc-data-policy-and-terms-of-use-2023/">
            </div>
        </div><br>
        """

        ### Sampling frequency ###
        frequency_options = form_schema["categories_definition"]["frequency"]["options"]
        sampling_freq_value = actions_data.get('description', '')

        form_html += f"""
        <div class="flex-row">
            <div class="form-label">
                <label for='sampling_frequency'>Sampling frequency:<span class='info-circle' data-tooltip='Select the frequency at which field sampling occurs.'>ⓘ</span></label>
            </div>
            <div class="flex-col input-col">
                <select name="sampling_frequency" id="sampling_frequency">
                    <option value="" disabled {'selected' if not sampling_freq_value else ''}>Select an option</option>
        """

        for key, option in frequency_options.items():
            selected = "selected" if sampling_freq_value == key else ""
            form_html += f"<option value='{key}' {selected}>{option['name'].title()}</option>"

        form_html += f"""
                </select>
                <div class='previous'><strong>Previously entered:</strong> {sampling_freq_value if sampling_freq_value else 'N/A'}</div>
            </div>
        </div>
        <br>
        """

        ### Update frequency ###
        update_freq_value = frequency_data.get('frequency', '')

        form_html += f"""
        <div class="flex-row">
            <div class="form-label">
                <label for='frequency'>Metadata update frequency:<span class="required">*</span><span class='info-circle' data-tooltip='Select the frequency you expect metadata documented in this form to be updated.'>ⓘ</span></label>
            </div>
            <div class="flex-col input-col">
                <select name="frequency" id="frequency" required>
                    <option value="" disabled {'selected' if not update_freq_value else ''}>Select an option</option>
        """

        for key, option in frequency_options.items():
            selected = "selected" if update_freq_value == key else ""
            form_html += f"<option value='{key}' {selected}>{option['name'].title()}</option>"

        form_html += f"""
                </select>
                <div class='previous'><strong>Previously entered:</strong> {update_freq_value if update_freq_value else 'N/A'}</div>
            </div>
        </div><br>
        """
        form_html += "<hr style='border: none; border-bottom: dashed 2px #002366; '>"

        ### Contact Information ###
        # Note to self add a flex box so I can add labels to the input boxes
        form_html += f"""
        <label for='contact_name'>
            <h2>Programme Contacts:<span class="required">*</span>
            <span class="info-circle" data-tooltip="Provide contact information for your entry. Can include helpdesk emails, contact pages, or individual or organizational contact information. URLs can link to support or contact pages.">ⓘ</span>
            </h2></label>
        <div class='previous'><strong>Previously entered:</strong>
        Type: {", ".join(prefilled_data.get('contactPoint', {}).get('contactType', 'N/A')) if prefilled_data.get('contactPoint', {}).get('contactType') else "N/A"};
        Names: {", ".join(prefilled_data.get('contactPoint', {}).get('name', 'N/A')) if prefilled_data.get('contactPoint', {}).get('name') else "N/A"};
        Email: {", ".join(prefilled_data.get('contactPoint', {}).get('email', 'N/A')) if prefilled_data.get('contactPoint', {}).get('email') else "N/A"};
        URL: {", ".join(prefilled_data.get('contactPoint', {}).get('url', 'N/A')) if prefilled_data.get('contactPoint', {}).get('url') else "N/A"}
        </div>
        """
        form_html += f"""
        <div id="contacts-container">
        </div>
        """
        contacts = prefilled_data.get("contactPoint", [])
        print("contact info:", contacts)
        print(f"Contacts data type: {type(contacts)}, content: {contacts}")

        if isinstance(contacts, dict):
            # Restructure the contacts from a dictionary of lists into a list of dictionaries
            contact_list = []
            length = len(contacts.get('name', []))
            for i in range(length):
                contact = {
                    'name': contacts.get('name', [])[i] if i < len(contacts.get('name', [])) else "",
                    'email': contacts.get('email', [])[i] if i < len(contacts.get('email', [])) else "",
                    'contactType': contacts.get('contactType', [])[i] if i < len(contacts.get('contactType', [])) else "",
                    'url': contacts.get('url', [])[i] if i < len(contacts.get('url', [])) else ""
                }
                contact_list.append(contact)
            contacts = contact_list
        elif isinstance(contacts, list):
            # If it's already a list, keep it as is
            pass

        print("Restructured contacts:", contacts)

        # Call the JavaScript function for each prefilled contact
        if contacts:
            if isinstance(contacts, dict):  # Single contact
                contacts = [contacts]
            for contact in contacts:
                contact_names = contact.get("name", "")
                contact_emails = contact.get("email", "")
                contact_types = contact.get("contactType", "")
                contact_urls = contact.get("url", "")
                form_html += f"""
                <script>
                    addContactInput("{contact_names}", "{contact_emails}", "{contact_types}", "{contact_urls}", true);
                </script>
                """
        else:
            form_html += """
            """
        # Add the dynamic container for new inputs
        form_html += "<div id='contacts-container'></div>"
        if not contacts:  # Only add the script if no prefilled data exists
            form_html += """
            <script>
                window.addEventListener("load", function() {
                    addContactInput();
                });
            </script>
            """
        form_html += """
        <button type="button" onclick="addContactInput()">Add Contact</button>
        <br><br>
        """
        form_html += "<hr style='border: none; border-bottom: dashed 2px #002366; '>"

        ### Coverage ###
        form_html += "<h2>Coverage</h2>"
        
        # Temporal coverage
        form_html += f"""
        <label for='temporal_coverage'>Temporal Coverage:<span class="info-circle" data-tooltip="Specify the date range for the project. Leave End Date blank if there is no known end date.">ⓘ</span></label>
        <div class="flex-row">
            <div class="form-label">
                Start date:
            </div>
            <div class="flex-col input-col">    
                <input type='date' name='temporal_coverage_start' id='temporal_coverage_start'
                    value="{prefilled_data.get('foundingDate', '') }" >
            </div>
        </div>
        <div class="flex-row">
            <div class="form-label">
                End  date:
            </div>
            <div class="flex-col input-col">        
                <input type='date' name='temporal_coverage_end' id='temporal_coverage_end' value="{prefilled_data.get('dissolutionDate', '')}" >
                <div class='previous'><strong>Previously entered:</strong>
                    Start: {prefilled_data.get('foundingDate', 'N/A')},
                    End: {prefilled_data.get('dissolutionDate', 'N/A')}
                </div>
            </div>
        </div>
        <br>
        """

        # Spatial Coverage
        regional_id_str = 'MRGID: '
        form_html += f"""
        <div class="flex-row">
            <div class="form-label">
                <label for="spatial_coverage_name">Spatial Coverage: <span class='info-circle' data-tooltip='Specify the name and MRGID of the area where the programme takes place. Use the search box to select an area from Marine Regions. Use the map below to also add bounding area coordinates.'>ⓘ</span></label>
            </div>
            <div class="flex-col input-col">
                <div>
                <input type="text" id="search_regions" placeholder="Search for a region. Minimum 3 characters, e.g., 'hud', 'bay'">
                <button type="button" id="search_regions_btn" style="max-width:35%">Search</button>
                <div class='previous'><strong>Previously entered:</strong> {prefilled_data.get('areaServed', {}).get("name", 'N/A')} {regional_id_str}{prefilled_data.get('areaServed', {}).get("identifier", 'N/A')}</div>
                <div style="max-width: 90%;">Use the search box above to search for a marine location. Names are obtained from <a href="https://www.marineregions.org/gazetteer.php?p=search">Marine Regions Gazetteer.</div>
                </div>
            </div>
        </div>
        
        <!-- Table to display search results -->
        <div class="table-scroll">
        <table id="regions_table" style="width:100%; display:none;">
            <thead>
                <tr>
                    <th>Region Name</th>
                    <th>Type</th>
                    <th>Source</th>
                </tr>
            </thead>
            <tbody>
                <!-- Dynamically populated rows will go here -->
            </tbody>
        </table>
        </div>
        <a><i>Auto-populated fields:</i></a><br>
        <div class="flex-row">
            <div class="form-label">
                Name: 
            </div>
            <div class="flex-col input-col">
                <input type="spatial" name="spatial_coverage_name" id="spatial_coverage_name" value="{prefilled_data.get('areaServed', {}).get("name", '')}" readonly>
            </div>
        </div>
        <div class="flex-row">
            <div class="form-label">
                MRGID: 
            </div>
            <div class="flex-col input-col">    
                <input type="text" name="spatial_coverage_identifier" id="spatial_coverage_identifier" value="{prefilled_data.get('areaServed', {}).get("identifier", '')}" readonly>
                <button type="button" onclick="clearMarineRegions()" style="width: 40%;">Clear Location</button>
            </div>
        </div>
        <br><br>
        """
        wkt_value = prefilled_data.get('areaServed', {}).get("geo", {}).get("geosparql:asWKT", {}).get("@value", "")
        print("Raw WKT:", wkt_value)

        # Extract just the POLYGON coordinates string
        match = re.search(r'POLYGON\s*\(\((.*?)\)\)', wkt_value)
        coords_raw = match.group(1) if match else ""
        print("Extracted POLYGON coords:", coords_raw)

        coordinates = []
        if coords_raw:
            for pair in coords_raw.split(","):
                lon_str, lat_str = pair.strip().split()
                lon, lat = float(lon_str), float(lat_str)
                coordinates.append((lat, lon))  # (lat, lon)

        # Extract bounding box values
        if coordinates:
            lats = [lat for lat, lon in coordinates]
            lons = [lon for lat, lon in coordinates]
            north = max(lats)
            south = min(lats)
            east = max(lons)
            west = min(lons)
        else:
            north = south = east = west = ""

        print("Bounding box:", north, south, east, west)

        form_html += f"""
        <a>Draw Bounding Area</a>
        <div id="map" style="width: 80vw; max-width: 100%; height: 50vh;"></div>
        <div class="flex-col" style="align-items: center;">
            <div class="flex-row">
                <div class="flex-col">
                    <label for="maxy" id="maxy">North (max latitude):</label>
                    <input type="text" id="north" name="north" value="{north}">
                </div>
                <div class="flex-col">
                    <label for="east" id="maxx">East (max longitude):</label>
                    <input type="text" id="east" name="east" value="{east}">
                </div>
            </div>
            <div class="flex-row">
                <div class="flex-col">
                    <label for="south" id="miny">South (min latitude):</label>
                    <input type="text" id="south" name="south" value="{south}">
                </div>
                <div class="flex-col">
                    <label for="west" id="minx">West (min longitude):</label>
                    <input type="text" id="west" name="west" value="{west}">
                </div>
            </div>
            <div class="flex-col">
                <button type="button" onclick="clearBoundingCoordinates()">Clear Bounding Coordinates</button>
            </div>
        </div>
        <br>
        """
        
        ## Provide custom WKT string
        wkt_previous = prefilled_data.get('areaServed', {}).get("geosparql:hasGeometry", {}).get("geosparql:asWKT", {}).get("@value", "")
        form_html += f"""
        <div class="flex-row">
            <div class="form-label">
                WKT String: <span class='info-circle' data-tooltip='Optionally provide a WKT string that captures the general sampling area. Please ensure the string uses EPSG:4326.'>ⓘ</span>
            </div>
            <div class="flex-col input-col">    
                <input type="text" name="wktstring" id="wktstring" value="{wkt_previous}" placeholder="POLYGON ((-64.8 32.3, -65.5 18.3, -80.3 25.2, -64.8 32.3))">
                <div class='previous'><strong>Previously entered:</strong> {wkt_previous or 'N/A'}</div>
                <div>Well-Known Text (WKT) strings are a text format to respresent spatial geometries (e.g. points, lines, polygons). For help generating WKT strings, see <a href="https://wktmap.com/">https://wktmap.com/</a></div>
            </div>
        </div>
        """
        form_html += "<hr style='border: none; border-bottom: dashed 2px #002366; '>"

        ### EOVs and Variables ###
        # Need to get the EOV names from the schema to cross reference with form output. Will use this to prepopulate checkboxes
        def extract_eov_groups(form_schema):
            fields = form_schema["categories_definition"]["variable_measured"]["fields"]
            bioeco_eovs = set(option["name"] for option in fields.get("bioeco_eovs", {}).get("options", {}).values())
            other_eovs = set(option["name"] for option in fields.get("other_eovs", {}).get("options", {}).values())
            subvars = set(option["name"] for option in fields.get("sub-variables", {}).get("options", {}).values())
            ebvs = set(option["name"] for option in fields.get("ebvs", {}).get("options", {}).values())
            return bioeco_eovs, other_eovs, subvars, ebvs
        bioeco_eovs, other_eovs, subvars, ebvs = extract_eov_groups(form_schema)

        # Build selected sets for each group
        keywords = prefilled_data.get("keywords", [])
        selected_bioeco = [kw["name"] for kw in keywords if kw.get("name") in bioeco_eovs]
        selected_other = [kw["name"] for kw in keywords if kw.get("name") in other_eovs]
        selected_subvars = [kw["name"] for kw in keywords if kw.get("name") in subvars]
        selected_ebvs = [kw["name"] for kw in keywords if kw.get("name") in ebvs]
        selected_eov_names = set(selected_bioeco + selected_other + selected_subvars + selected_ebvs)

        def process_fields(fields, prefilled_data):
            html = ""
            for field_key, field in fields.items():
                if "options" in field:  # Checkbox handling
                    html += f"<label for='{field_key}'><h4>{field.get('name', 'Unknown Field')}</h4></label>"
                    if field_key == "bioeco_eovs":
                        prev = ', '.join(selected_bioeco) or 'N/A'
                        html += f"<div class='previous'><strong>BioEco EOVs previously entered:</strong> {prev}</div>"
                    elif field_key == "other_eovs":
                        prev = ', '.join(selected_other) or 'N/A'
                        html += f"<div class='previous'><strong>Other EOVs previously entered:</strong> {prev}</div>"
                    elif field_key == "sub-variables":
                        prev = ', '.join(selected_subvars) or 'N/A'
                        html += f"<div class='previous'><strong>Sub-variables previously entered:</strong> {prev}</div>"
                    elif field_key == "ebvs":
                        prev = ', '.join(selected_ebvs) or 'N/A'
                        html += f"<div class='previous'><strong>EBVs previously entered:</strong> {prev}</div>"

                    

                    # Ensure category_value is a list if it's a string
                    #category_value_list = category_value.split(", ") if isinstance(category_value, str) else category_value
                    # Create a scrollable div for checkboxes
                    html += f"<div class='checkbox-container'>"
                    sorted_options = sorted(field["options"].items(), key=lambda item: item[1]["name"].lower())
                    for option_key, option in sorted_options:
                        # Check if the option name is in the list of previously entered values
                        checked = "checked" if option["name"] in selected_eov_names else ""
                        property_id = option.get("propertyID", "")
                        if isinstance(property_id, list):
                            property_id = ", ".join(property_id)
                        option_value = f"{option['name']}|{property_id}"
                        html += f"<input type='checkbox' name='{field_key}' value='{option_value}' {checked}> {option['name']}<br>"
                    html += "</div>"
                # elif field.get("type") == "text":  # Text input handling
                #     html += f"<label for='{field_key}'>{field.get('name', 'Unknown Field')}</label>"
                #     html += f"<input type='text' name='{field_key}' id='{field_key}' value='{value}'>"
            return html

        # Render the EOV section
        form_html += "<h2>EOV Information<span class='info-circle' data-tooltip='For each section below, check the EOVs that are monitored.'>ⓘ</span></h2>"
        form_html += "In this section, please provide information all EOVs, sub-variables, etc. that are monitored, measured, or relevant for your entry. Please also include information on which observing approaches, platforms, and/or technologies are used. EOVs are defined by GOOS, and sub-variables are listed in corresponding specification sheets. See <a href='https://goosocean.org/what-we-do/framework/essential-ocean-variables/' target='_blank'>here</a>."
        eov_fields = form_schema["categories_definition"]["variable_measured"]["fields"]
        form_html += process_fields(eov_fields, prefilled_data)

        ### Platforms ###
        instruments = actions_data.get("instrument", [])
        selected_platforms = []
        for instrument in instruments:
            if instrument and "name" in instrument:
                name = instrument.get("name", "")
                url = instrument.get("url", "")
                selected_platforms.append(f"{name}|{url}")

        # Get platform options from schema
        platform_options = form_schema["categories_definition"]["measurementTechnique"]["fields"]["measurement_platforms"]["options"]
        form_html += "<h3>Sampling approach <span class='info-circle' data-tooltip='Sampling approach, or measurement platforms, include any observing approach, platforms and/or technologies used to collect information about EOVs.'>ⓘ</span></h3>"
        platforms_display = ', '.join([p.split('|')[0] for p in selected_platforms]) if selected_platforms else 'N/A'
        form_html += f"<div class='previous'><strong>Previously entered approaches:</strong> {platforms_display}</div>"
        form_html += "<div class='checkbox-container'>"
        for key, option in platform_options.items():
            value = f"{option['name']}|{option.get('propertyID', '')}"
            checked = "checked" if value in selected_platforms else ""
            form_html += f"<input type='checkbox' name='measurement_platforms' value='{value}' {checked}> {option['name']}<br>"
        form_html += "</div>"


        ### SOP section ###
        # use the prefilled potential_actions as above
        sops = actions_data.get("actionProcess", [])
        sop_entries = []
        for sop in sops:
            sop_name = sop.get("name", "")
            sop_url = sop.get("url", "")
            is_obps = "yes" if sop.get("isPartOf") else ""
            sop_entries.append({"name": sop_name, "url": sop_url, "is_obps": is_obps})

        form_html += "<label for='sops'><h3> Standard Operating Procedures <span class='info-circle' data-tooltip='Provide a link to a resource that describes any Methods or Standard Operating Procedures (SOPs) used to monitor the selected EOVs.'>ⓘ</span></h3></label>"
        form_html += "<div class='previous'><strong>Previously entered SOPs: </strong>"
        if sop_entries:
            for sop in sop_entries:
                sop_name = sop.get("name", "N/A")
                sop_url = sop.get("url", "N/A")
                form_html += f"Name: {sop_name} URL: {sop_url} "
        else:
            form_html += "N/A"
        form_html += "</div>"
        form_html += "<div id='sops-container'>"
        if sop_entries:
            for sop in sop_entries:
                name = sop["name"]
                url = sop["url"]
                is_obps = sop["is_obps"]
                form_html += f"""
                <script>
                    addSOPInput("{name}", "{url}", "{is_obps}");
                </script>
                """
        form_html += "</div>"
        form_html += '<button type="button" onclick="addSOPInput()">Add a SOP link</button><br>'

        form_html += "<hr style='border: none; border-bottom: dashed 2px #002366; '>"

        ### Outputs section ###
        outputs = prefilled_data.get("makesOffer", [])
        outputs_entries = []
        if isinstance(outputs, list):
            for offer in outputs:
                item = offer.get("itemOffered", {})
                offer_name = item.get("name", "N/A")
                offer_url = item.get("url", "")
                outputs_entries.append({"name": offer_name, "url": offer_url})
        else:
            outputs_entries = []

        form_html += "<label for='outputs'><h2>Outputs: <span class='info-circle' data-tooltip='Enter relevant outputs that are related to your entry.'>ⓘ</span></h2></label>"
        form_html += "<p>Please optionally provide the link to any relevant outputs that are associated with your entry. This may include products, portals, etc. If you have already linked any such outputs with ODIS or the BioEco Portal, you can provide them again here if you wish. Note that datasets published to OBIS would not need to be added here, and you can use the same data producer ID in OBIS metadata to ensure your entry is linked with OBIS data. </p>"
        form_html += "<div class='previous'><strong>Previously entered: </strong>"
        if outputs_entries:
            for offer in outputs_entries:
                offer_name = offer.get("name", "N/A")
                offer_url = offer.get("url", "N/A")
                form_html += f"Name: {offer_name} URL: {offer_url} "
        else:
            form_html += "N/A"
        form_html += "</div>"

        form_html += "<div id='outputs-container'>"
        if outputs_entries:
            for offer in outputs_entries:
                name = offer["name"]
                url = offer["url"]
                form_html += f"""
                <script>
                    addOutputInput("{name}","{url}");
                </script>
            """
        form_html += "</div>"
        form_html += '<button type="button" onclick="addOutputInput()">Add an Output</button><br>'

        form_html += "<hr style='border: none; border-bottom: dashed 2px #002366; '>"

        ### Funding section ###
        form_html += "<label for='funder-container'><h2>Funding Information <span class='info-circle' data-tooltip='Provide information about funding organizations and awards.'>ⓘ</span></h2></label>"
        form_html += "<p>Please provide information about the funding that supports your entry.</p>"

        funding_data = prefilled_data.get("funding", [])
        form_html += f"""
        <div class="previous"><strong>Previously entered:</strong>
            Funder name: {", ".join(prefilled_data.get("funding", {}).get("funder", {}).get("name", [])) if prefilled_data.get("funding", {}).get("funder", {}).get("name") else "N/A"},
            Funder URL: {", ".join(prefilled_data.get("funding", {}).get("funder", {}).get("url", [])) if prefilled_data.get("funding", {}).get("funder", {}).get("url") else "N/A"},
            Funding award name: {", ".join(prefilled_data.get("funding", {}).get("name", [])) if prefilled_data.get("funding", {}).get("name") else "N/A"},
            Funding award identifier: {", ".join(prefilled_data.get("funding", {}).get("identifier", [])) if prefilled_data.get("funding", {}).get("identifier") else "N/A"}
        </div>
        """
        print("Funding data:", funding_data)

        # Normalize the funding data into a list of dictionaries
        if isinstance(funding_data, dict):  # If it's a dict of lists, restructure into list of dicts
            funding_list = []
            length = len(funding_data.get("name", []))
            for i in range(length):
                #funder_info = funding_data.get("funder", [{}])[i] if i < len(funding_data.get("funder", [])) else {}
                #print("Funder info:", funder_info)  # Debugging
                funding_entry = {
                    "funder_name": funding_data.get("funder", {}).get("name", [])[i] if i < len(funding_data.get("funder", {}).get("name", [])) else "",
                    "funder_url": funding_data.get("funder", {}).get("url", [])[i] if i < len(funding_data.get("funder", {}).get("url", [])) else "",
                    "name": funding_data.get("name", [])[i] if i < len(funding_data.get("name", [])) else "",
                    "identifier": funding_data.get("identifier", [])[i] if i < len(funding_data.get("identifier", [])) else ""
                }
                funding_list.append(funding_entry)
            funding_data = funding_list
        elif isinstance(funding_data, list):  # If it's already a list, use as is
            pass

        # Debug: Print the normalized funding data
        print("Normalized funding data:", funding_data)

        # Generate the form fields for prefilled funding data
        form_html += '<div id="funder-container"></div>'
        if funding_data:
            for funding in funding_data:
                funder_name = funding.get('funder_name', '')
                funder_url = funding.get('funder_url', '')
                award_name = funding.get('name', '')
                award_id = funding.get('identifier', '')
                form_html += f"""
                <script>
                    window.addEventListener("DOMContentLoaded", function() {{
                        addFunders("{funder_name}", "{funder_url}", "{award_name}", "{award_id}");
                    }});
                </script>
                """
        else:
            form_html += """
            <script>
                window.addEventListener("load", function() {
                    addFunders();
                });
            </script>
            """
        form_html += '<button type="button" onclick="addFunders()">Add a Funder</button><br>'

        form_html += "<hr style='border: none; border-bottom: dashed 2px #002366; '>"

        return form_html