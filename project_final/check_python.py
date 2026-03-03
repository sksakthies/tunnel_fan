import json

with open(r"C:\project_final\real_database.json", "r") as f:
    data = json.load(f)

print("project_id:", data.get("project_id"))
print("client_email:", data.get("client_email"))