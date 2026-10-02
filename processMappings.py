# A dictionary that maps form field names to the JSON schema field names in the GitHub issue, with transformation functions if needed
from mappings import schema_field_mapping, actions_field_mapping, frequency_field_mapping

def get_nested_value(data, field_path, default=None):
    """Helper function to get a value from a nested dictionary using a dot-separated path."""
    keys = field_path if isinstance(field_path, list) else field_path.split(".")
    for key in keys:
        if isinstance(data, list):
            # If the current level is a list, try to get a list of values for the key
            # Extract all items in the list that are dictionaries and have the key
            data = [item.get(key) for item in data if isinstance(item, dict) and item.get(key) is not None]
            if not data:  # If no dictionaries with the key are found, return default
                return default
        elif isinstance(data, dict):
            # If the current level is a dict, get the value for the key
            data = data.get(key, default)
        else:
            # Key path cannot be resolved if data is not a dict or list
            return default
    return data

def map_form_to_schema(form_data, field_mapping, base_type=None):
    schema_entry = {}
    if base_type:
        schema_entry["@type"] = base_type

    # Preserve structured project metadata that is not represented as a simple form field mapping, such as additionalProperty entries containing TRLs
    if isinstance(form_data, dict) and "additionalProperty" in form_data:
        schema_entry["additionalProperty"] = form_data.get("additionalProperty")

    for form_field, (schema_field, field_type) in field_mapping.items():
    # Split the schema field to handle nested fields
        keys = schema_field.split(".")

        # Get the value from the form data
        value = get_nested_value(form_data, keys)

        # Skip fields that aren't present at all
        if value is None:
            continue

        # Process lists appropriately
        if isinstance(value, list):
            # If the schema specifies a list type, keep it as a list
            if field_type == list:
                value = value
            # Otherwise, extract the first element of the list for single fields
            elif field_type == str and value:
                value = value[0]

        # Convert the value to the correct type
        elif field_type == str:
            value = str(value)

        # Insert into schema
        temp = schema_entry
        for key in keys[:-1]:
            temp = temp.setdefault(key, {})
        temp[keys[-1]] = value

    return schema_entry


# test_data = {
#     "contactPoint": {
#         "name": "Elizabeth Lawrence",
#         "email": "elizabeth-lawrence@outlook.com"
#     },
#     "funding": [
#         {
#             "funder": {
#                 "name": "European Commission",
#                 "url": "https://commission.europa.eu/index_en"
#             }
#         }
#     ]
# }

# contact_name = get_nested_value(test_data, "contactPoint.name")
# print(contact_name)  # Should print "Elizabeth Lawrence"

# funder_name = get_nested_value(test_data, "funding.funder.name")
# print(funder_name)  # Should print "European Commission"
