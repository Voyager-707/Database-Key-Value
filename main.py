from database import Database

db = Database("data.db")

db.set("name", "Martin")
db.set("age", "20")

print(db.get("name"))
print(db.get("age"))

print(db.contains("name"))



print(db.contains("name"))
print(db.get("name"))

db.close()