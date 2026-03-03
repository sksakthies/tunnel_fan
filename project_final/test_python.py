import firebase_admin
from firebase_admin import credentials, db

cred = credentials.Certificate(r"C:\tunnel_fan\project_final\realtime_database.json")

firebase_admin.initialize_app(cred, {
    "databaseURL": "https://tunnelbooster-ff01f-default-rtdb.asia-southeast1.firebasedatabase.app"
})

print(db.reference("/").get())
print(db.reference("Fan-1").get())
print(db.reference("Fan-1/28-02-2026").get())