import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import json

key_file = "../credentials.json"
cred = credentials.Certificate(key_file)
firebase_admin.initialize_app(cred)

db = firestore.client()

# @thanks https://stackoverflow.com/a/57561744/811306
def set(my_dict, field_path, value):
    """Given `foo`, 'key1.key2.key3', 'something', set foo['key1']['key2']['key3'] = 'something'"""
    here = my_dict
    keys = field_path.split('.')
    for key in keys[:-1]:
        # Create key with empty dictionary if it does not exist and move pointer.
        here = here.setdefault(key, {})
    here[keys[-1]] = value

# for collection in [{id: 'dayplans'}]:
for collection in db.collections():
    collection_name = collection.id
    print(f"Exporting {collection_name}...")
    json_file = collection_name + '.json'

    # documents = db.collection(collection_name).recursive().limit(100).get()
    documents = db.collection(collection_name).recursive().get()
    data = {}
    for doc in documents:
        print(doc.reference.path)
        keys = doc.reference.path.split('/')[1:]
        key = '.'.join(keys)
        set(data, key, doc.to_dict())

    # print(json.dumps(data, indent=2, default=str))

    with open(json_file, 'w') as file:
        json.dump(data, file, indent=4, sort_keys=True, default=str, ensure_ascii=False)

    print(f"☑️  Exported to {json_file}.")
