from flask import request
import json
from mappings import schema_field_mapping, actions_field_mapping, frequency_field_mapping
from processMappings import map_form_to_schema
from config_constants import REPO_OWNER, GITHUB_REPO, JSON_FOLDER

with open("schema.json") as f:
    form_schema = json.load(f)

def add_schema_prefix(obj):
    """
    Recursively add 'schema:' to plain JSON keys so they compact to schema.org terms.
    Keys that are already qualified (contain ':', e.g. geosparql:asWKT)
    are left unchanged so GeoSPARQL and similar terms are not turned into schema:geosparql:asWKT.
    """
    if isinstance(obj, dict):
        new_obj = {}
        for k, v in obj.items():
            if k.startswith("@"):
                new_obj[k] = add_schema_prefix(v)
            elif ":" in k:
                new_obj[k] = add_schema_prefix(v)
            else:
                new_obj[f"schema:{k}"] = add_schema_prefix(v)
        return new_obj
    if isinstance(obj, list):
        return [add_schema_prefix(item) for item in obj]
    return obj

def clean_dict(data):
    return {k: v for k, v in data.items() if v}

def makeFormJson():
    if request.method == "POST":
        ########## Create the schema entry ##########
        schema_entry = {
            "@context": {
                "schema": "http://schema.org/",
                "geosparql": "http://www.opengis.net/ont/geosparql#"
            },
            "@type": "schema:ResearchProject",
        }

        ########## Collect and sanitize submitted form data ##########
        submitted_data = request.form.to_dict(flat=False)  # Support multi-select fields
        sanitized_data = {}
        for key, value in submitted_data.items():
            sanitized_data[key] = value if isinstance(value, list) else value
        print("san data: ", sanitized_data)

        # Mappings
        mapped_schema_entry = map_form_to_schema(sanitized_data, schema_field_mapping, base_type="Project")
        schema_entry.update(mapped_schema_entry)

        # Ensure @context and @type are preserved
        schema_entry.setdefault("@context", {
            "@vocab": "https://schema.org/",
            "geosparql": "http://www.opengis.net/ont/geosparql#"
        })
        schema_entry.setdefault("@type", "Project")

        # Remove @context from schema_entry for @graph
        schema_entry.pop("@context", None)
        actions_json = map_form_to_schema(sanitized_data, actions_field_mapping, base_type="Action")
        metadata_frequency = map_form_to_schema(sanitized_data, frequency_field_mapping)

        ## Build the @id
        shortname = sanitized_data.get('shortname', [""])[0]
        project_name = sanitized_data.get('project_name', [""])[0]
        project_name_sanitized = (shortname or project_name).replace(" ", "_")
        schema_entry["@id"] = f"https://raw.githubusercontent.com/BioEcoOcean/metadata-tracking-dev/refs/heads/main/jsonFiles/{project_name_sanitized}/{project_name_sanitized}.json"

        ## Add legalName, name, url, description
        schema_entry["legalName"] = sanitized_data.get("project_name", [""])[0]
        if sanitized_data.get("shortname", [""])[0]:
            schema_entry["name"] = sanitized_data.get("shortname", [""])[0]
        schema_entry["url"] = sanitized_data.get("url", [""])[0]
        if sanitized_data.get("description", [""])[0]:
            schema_entry["description"] = sanitized_data.get("description", [""])[0]
        
        ## Handle the projid & identifier field
        projid_type = request.form.get("projid_type", "")
        identifier_types = form_schema.get("identifier_types", {})
        projid_type_url = identifier_types.get(projid_type, {}).get("url", "")
        def extract_identifier_value(projid_type, projid_url):
            if projid_type == "DOI" and projid_url.startswith("https://doi.org/"):
                return projid_url.replace("https://doi.org/", "")
            elif projid_type == "RAiD" and projid_url.startswith("https://raid.org/"):
                return projid_url.replace("https://raid.org/", "")
            elif projid_type == "ROR" and projid_url.startswith("https://ror.org/"):
                return projid_url.replace("https://ror.org/", "")
            # fallback: try to get everything after the last slash
            return projid_url.rstrip('/').split('/')[-1]
        if sanitized_data.get("projid", [""])[0]:
            projid_url = sanitized_data.get("projid", [""])[0]
            value = extract_identifier_value(projid_type, projid_url)
            schema_entry["identifier"] = { #will need to be updated with some logic for if it's a DOI or not
                "@type": "schema:PropertyValue",
                "description": sanitized_data.get("projid_type", [""])[0],
                "propertyID": projid_type_url,
                "url": projid_url,
                "value": value #need to add logic to get the value from the url
            }
        
        ## Parent organization
        if sanitized_data.get("parentOrganization", [""])[0]:
            schema_entry["parentOrganization"] = {
                "@type": "schema:Organization",
                "legalName": sanitized_data.get("parentOrganization", [""])[0],
                "url": sanitized_data.get("parentOrganization_url", [""])[0]
                }

        ## Get the license field
        license_data = sanitized_data.get("license", [""])[0]
        license_name, license_url = license_data.split("|") if license_data else (license_data, "")
        publishing_principles =[{
            "@type": "schema:CreativeWork",
            "name": license_name,
            "url": license_url
        }]
        datapolicy_name = sanitized_data.get("datapolicy_name", [""])[0]
        datapolicy_text = sanitized_data.get("datapolicy_text", [""])[0]
        datapolicy_url = sanitized_data.get("datapolicy_url", [""])[0]
        if datapolicy_name and datapolicy_text and datapolicy_url:
            publishing_principles.append({
                "@type": "schema:CreativeWork",
                "name": datapolicy_name,
                "url": datapolicy_url,
                "text": datapolicy_text
        })
        schema_entry["publishingPrinciples"] = publishing_principles
        
        ## Add time coverage
        if sanitized_data.get("temporal_coverage_start", [""])[0]:
            schema_entry["foundingDate"] = sanitized_data.get("temporal_coverage_start", [""])[0]
        if sanitized_data.get("temporal_coverage_end", [""])[0]:
            schema_entry["dissolutionDate"] = sanitized_data.get("temporal_coverage_end", [""])[0]

        ## Handle the spatialCoverage field
        area_name = sanitized_data.get("spatial_coverage_name", [""])[0]
        area_id = sanitized_data.get("spatial_coverage_identifier", [""])[0]
        south = sanitized_data.get("south", [""])[0]
        west = sanitized_data.get("west", [""])[0]
        north = sanitized_data.get("north", [""])[0]
        east = sanitized_data.get("east", [""])[0]
        if area_name and area_id:
            # For named areas, add as areaServed for now, but to align, perhaps integrate
            area_served = {
                "@type": "schema:Place",
                "name": area_name,
                "identifier": area_id,
            }
            if south and west and north and east:
                area_served["geo"] = {
                        "@type": "schema:GeoShape",
                        "description": "Bounding box polygon with lat long (Y X) coordinate order.",
                        "geosparql:asWKT": {
                            "@type": "http://www.opengis.net/ont/geosparql#wktLiteral",
                            "@value": f"<http://www.opengis.net/def/crs/OGC/1.3/CRS84> POLYGON(({west} {south}, {east} {south}, {east} {north}, {west} {north}, {west} {south} ))"
                            }
                }
            schema_entry["areaServed"] = [area_served]
        print("bounds: ", north, south, east, west)
        wktstring = sanitized_data.get("wktstring", [""])[0]
        if wktstring:
            # Ensure areaServed is a list before appending
            if "areaServed" not in schema_entry:
                schema_entry["areaServed"] = []
            elif not isinstance(schema_entry["areaServed"], list):
                # If it's a dict (from mapping), convert to list
                schema_entry["areaServed"] = [schema_entry["areaServed"]]
            
            schema_entry["areaServed"].append({
                "geosparql:hasGeometry": {
                    "geosparql:asWKT": {
                        "@type": "http://www.opengis.net/ont/geosparql#wktLiteral",
                        "@value": f"<http://www.opengis.net/def/crs/OGC/1.3/CRS84> {wktstring}"
                    }
                }
            })

        ## Add keywords (select & EOVs)
        keywords_list = []
        selected_keywords_json = request.form.get("selected-keywords-json")  # A hidden input containing the JSON array of selected keywords
        print("selected keywords json: ", selected_keywords_json)
        if selected_keywords_json:
            try:
                selected_keywords = json.loads(selected_keywords_json)  # Parse the JSON string into a Python list of dictionaries
                keywords_list.extend([
                    {
                        "identifier": keyword.get("id"),
                        "@type": "schema:DefinedTerm",
                        "termCode": keyword.get("obo_id"),  # Using identifier as the termCode
                        "name": keyword.get("label"),
                        "url": keyword.get("id")  # Using identifier as the URL
                    }
                    for keyword in selected_keywords
                    if keyword.get("id") and keyword.get("label")  # Ensure both id and label exist
                ])
            except json.JSONDecodeError:
                pass

        ## Handle EOVs as keywords
        for eov_category in ['bioeco_eovs', 'other_eovs','ebvs', 'sub-variables']: # I removed 'ebvs' - do we need them in the form??
            if eov_category in sanitized_data:
                for eov in sanitized_data[eov_category]:
                    name, propertyID = eov.split("|")
                    propertyID_list = [pid.strip() for pid in propertyID.split(",") if pid.strip()]
                    if name and propertyID_list:  # Ensure both fields have data
                        keywords_list.append({
                            "@type": "schema:DefinedTerm",
                            "name": name,
                            "url": propertyID_list if len(propertyID_list) > 1 else propertyID_list[0],  # Use list if multiple, string if one
                        })
        if keywords_list:
            schema_entry["keywords"] = keywords_list

        ## Process funding and funder details
        funder_name = sanitized_data.get("funder_name", [])
        funder_url = sanitized_data.get("funder_url", [])
        funding_name = sanitized_data.get("funding_name", [])
        funding_identifier = sanitized_data.get("funding_identifier", [])

        # Initialize the funding list
        funding = []
        # Iterate through funding information and create individual entries
        for i in range(max(len(funding_name), len(funding_identifier), len(funder_name), len(funder_url))):
            # Create a single funder entry
            funder = {
                "@type": "schema:FundingAgency",
                "name": funder_name[i] if i < len(funder_name) else "",
                "legalName": funder_name[i] if i < len(funder_name) else "",
                "url": funder_url[i] if i < len(funder_url) else ""
            }
            funder = funder if funder["name"] or funder["url"] else None
            # Create a single funding entry with its associated funder
            funding_entry = {
                "@type": "schema:MonetaryGrant",
                "name": funding_name[i] if i < len(funding_name) else "",
                "identifier": funding_identifier[i] if i < len(funding_identifier) else "",
                "funder": funder
            }

            # Append the funding entry if it has meaningful data
            if funding_entry["name"] or funding_entry["identifier"] or funding_entry["funder"]:
                funding.append(funding_entry)

        if funding:  # Only add to schema_entry if the funding list is not empty
            schema_entry["funding"] = funding

        ## Add contact points
        contact_names = request.form.getlist("contact_names")
        contact_emails = request.form.getlist("contact_emails")
        contact_types = request.form.getlist("contact_types")
        contact_ids = request.form.getlist("contact_ids")
        num_contacts = max(len(contact_names), len(contact_emails), len(contact_types), len(contact_ids))

        contact_points = []

        # Iterate through the list, for the number of contacts
        for i in range(num_contacts):
            # Safely get each field for the current contact, defaulting to empty string if not available
            name = contact_names[i] if i < len(contact_names) else ""
            email = contact_emails[i] if i < len(contact_emails) else ""
            type = contact_types[i] if i < len(contact_types) else ""
            identifier = contact_ids[i] if i < len(contact_ids) else ""

            # Add the contact entry to the 'contactPoint' list
            if any([name, email, type, identifier]):
                contact_points.append({
                    "@type": "schema:ContactPoint",
                    "contactType": type,
                    "name": name,
                    "email": email,
                    "url": identifier
                })

            if contact_points:
                schema_entry["contactPoint"] = contact_points

        ## Get outputs
        outputs = request.form.getlist("outputs")  # Collect all 'outputs' input values
        outputs_urls = request.form.getlist("outputs_url")
        sanitized_outputs = [
            (name.strip(), url.strip())
            for name, url in zip(outputs, outputs_urls)
            if name.strip() or url.strip()
        ]
        sanitized_data["outputs"] = sanitized_outputs if sanitized_outputs else []

        # Add outputs to schema_entry as a list of offers
        if sanitized_outputs:
            schema_entry["makesOffer"] = []
            for offer_name, offer_url in sanitized_outputs:
                schema_entry["makesOffer"].append({
                    "@type": "schema:Offer",
                    "name": f"Distribution of {offer_name}",
                    "itemOffered": {
                        "@type": "schema:CreativeWork",
                        "name": offer_name,
                        "url": offer_url
                    }
                })

        ## Add platforms in potentialAction https://schema.org/potentialAction --> MOVED TO SEPARATE ACTIONS JSON
        # schema_entry["potentialAction"] = []
        # if 'measurement_platforms' in sanitized_data:
        #     for platform in sanitized_data['measurement_platforms']:
        #         name, propertyID = platform.split("|")
        #         schema_entry["potentialAction"].append({
        #             "@type": "Action",
        #             "agent": {
        #                 "@type": "Project",
        #                 "@id": schema_entry["@id"],  # Pointing to the id of the project itself
        #                 "name": project_name  # Pointing to the id of the project itself and where its json is
        #             }, # Pointing to the id of the project itself and where its json is
        #             "instrument": {
        #                 "name": name,
        #                 "identifier": propertyID

        #             }

        #         })

        ## Add SOP URLs to --> potentialAction? https://schema.org/potentialAction
        # sop_urls = [url.strip() for url in request.form.getlist("sops") if url.strip()]
        # sop_obps_values = request.form.getlist("sop_obps")  # Get the OBPs checkbox values
        # if sop_urls:
        #     for i, sop in enumerate(sop_urls):
        #         # Start building the SOP entry
        #         sop_entry = {
        #             "@type": "Action",
        #             "agent": {
        #                 "@type": "Project",
        #                 "@id": schema_entry["@id"],  # Pointing to the id of the project itself
        #                 "name": project_name  # Pointing to the id of the project itself and where its json is
        #             },
        #             "actionProcess": {
        #                 "@type": "HowTo", #or CreativeWork?
        #                 "url": sop
        #             }
        #         }

        #         # Add isPartOf only if OBPs checkbox is "yes"
        #         if i < len(sop_obps_values) and sop_obps_values[i].lower() == "yes":
        #             sop_entry["actionProcess"]["isPartOf"] = {
        #                 "@type": "Collection", #what type should this be?
        #                 "name": "Ocean Best Practices",
        #                 "url": "https://www.oceanbestpractices.org/"
        #             }

        #         # Append the SOP entry to the measurementTechnique
        #         schema_entry["potentialAction"].append(sop_entry)

        ########## Build the separate JSON for Actions ##########
        actions_json = {
            "@type": "schema:Action",
            "agent": {
                "@type": "schema:ResearchProject",
                "@id": schema_entry["@id"],  # Pointing to the id of the project itself
                "name": project_name  # Pointing to the id of the project itself and where its json is
            }
        }
        ## Build the @id
        actions_json["@id"] = f"https://raw.githubusercontent.com/{REPO_OWNER}/{GITHUB_REPO}/refs/heads/main/jsonFiles/{project_name_sanitized}/{project_name_sanitized}.json"

        ## Add platforms to instrument
        actions_json["instrument"] = []
        if 'measurement_platforms' in sanitized_data:
            for platform in sanitized_data['measurement_platforms']:
                name, propertyID = platform.split("|")
                actions_json["instrument"].append({
                    "@type": "schema:Thing",
                    "name": name,
                    "url": propertyID
                })

        ## Add SOP URLs to an actionProcess HowTo
        actions_json["actionProcess"] = []
        sops_url = request.form.getlist("sops_url")
        sops_name = request.form.getlist("sops_name")
        # Ensure all lists are the same length
        num_sops = max(len(sops_url), len(sops_name))
        for i in range(num_sops):
            sop_entry = {
                "@type": "schema:HowTo",
                "url": sops_url[i] if i < len(sops_url) else ""
                }
            if i < len(sops_name):
                sop_entry["name"] = sops_name[i]
            if sop_entry.get("url") or sop_entry.get("name"):
                actions_json["actionProcess"].append(sop_entry)

                # remove the OBPS as the link should work fine for connecting don't need to indicate
                #Add isPartOf only if OBPs checkbox is "yes"  --> remove this block
                # if i < len(sop_obps_values) and sop_obps_values[i].lower() == "yes":
                #     sop_entry["actionProcess"]["isPartOf"] = {
                #         "@type": "Collection", #what type should this be?
                #         "name": "Ocean Best Practices",
                #         "url": "https://www.oceanbestpractices.org/"
                #     }

                # Append the SOP entry to the measurementTechnique
                #actions_json["actionProcess"].append(sop_entry)

        # Add sampling frequency
        if sanitized_data.get("sampling_frequency", [""])[0]:
            actions_json["description"] = sanitized_data.get("sampling_frequency", [""])[0]

        ########## Create small file for frequency for the sitemap ##########
        metadata_frequency = {}
        if sanitized_data.get("frequency", [""])[0]:
            metadata_frequency["schema:frequency"] = sanitized_data.get("frequency", ["Never"])[0]

        # Apply schema prefix to Project and Action nodes (qualified names like geosparql:asWKT unchanged)
        schema_entry = add_schema_prefix(schema_entry)
        actions_json = add_schema_prefix(actions_json)

        ########## Combine into @graph structure ##########
        # Create the @graph array
        graph = [schema_entry, actions_json, metadata_frequency]

        # Create the final output with @graph
        output = {
            "@context": {
                "schema": "http://schema.org/",
                "geosparql": "http://www.opengis.net/ont/geosparql#"
            },
            "@graph": graph
        }

        return output