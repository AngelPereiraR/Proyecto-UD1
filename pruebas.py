from pymongo import MongoClient

uri = "mongodb+srv://angelmanuelpereirarodriguezalu_db_user:<db_password>@smartparkingcluster.t3tblwx.mongodb.net/?retryWrites=true&w=majority&appName=SmartParkingCluster"
client = MongoClient(uri)

# Probar conexión
db = client.smartparking
print(db.list_collection_names())

# Insertar documento de prueba
test_bay = {
    "bay_id": "TEST-001",
    "parking_id": "PK-CADIZ-01",
    "level": "L1",
    "occupied": False,
    "updated_at": "2025-10-18T10:00:00Z"
}
db.bays.insert_one(test_bay)
print("✓ Conexión exitosa a MongoDB Atlas")