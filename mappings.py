# Paths use compact JSON without the "schema:" prefix. Data ingested from GitHub is passed
# through strip_schema_org_prefixes() in helpers.py before map_form_to_schema() so these
# paths align with makeFormIntoJson output (add_schema_prefix).
schema_field_mapping = {
    "project_name": ("legalName", str),
    "shortname": ("name", str),
    "url": ("url", str),
    "description": ("description", str),
    "projids": ("identifier.url", list),
    "projid_types": ("identifier.description", list),
    "parentOrganization": ("parentOrganization.legalName", str),
    "parentOrganization_url": ("parentOrganization.url", str),
    "license": ("publishingPrinciples.name", str),
    "datapolicy_name": ("publishingPrinciples.name", str),
    "datapolicy_text": ("publishingPrinciples.text", str),
    "datapolicy_url": ("publishingPrinciples.url", str),
    
    # Temporal coverage
    "temporal_coverage_start": ("foundingDate", str), 
    "temporal_coverage_end": ("dissolutionDate", str),

    # Contact information
    "contact_names": ("contactPoint.name", list),
    "contact_emails": ("contactPoint.email", list),
    "contact_urls": ("contactPoint.url", list),
    "contact_types": ("contactPoint.contactType", list),
    
    # Spatial coverage
    "spatial_coverage_name": ("areaServed.name", str),
    "spatial_coverage_identifier": ("areaServed.identifier", str),
    "north": ("areaServed.geo.geosparql:asWKT.@value", str),
    "south": ("areaServed.geo.geosparql:asWKT.@value", str),
    "east": ("areaServed.geo.geosparql:asWKT.@value", str),
    "west": ("areaServed.geo.geosparql:asWKT.@value", str),
    "wktstring": ("areaServed.geosparql:hasGeometry.geosparql:asWKT.@value", str),

    # Keywords
    "selected-keywords-json": ("keywords", list),
    #"variables_measured": ("variableMeasured", list),

    # Funding information
    "funder_name": ("funding.funder.name", list),
    "funder_url": ("funding.funder.url", list),
    "funding_name": ("funding.name", list),
    "funding_identifier": ("funding.identifier", list),

    # Outputs
    "outputs": ("makesOffer", list),
}
actions_field_mapping = {
    # Actions: SOPs & platforms, sampling frequency
    "sops": ("actionProcess", list),
    "measurement_platforms": ("instrument", list),
    "sampling_frequency": ("description", str),
}
frequency_field_mapping = {
    # Only fields for metadata_frequency
    "frequency": ("frequency", str),
}