import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from google.api_core import exceptions
from google.cloud.firestore_v1.base_query import FieldFilter
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import sys
import time

key_file = "../credentials.json"
cred = credentials.Certificate(key_file)
firebase_admin.initialize_app(cred)

db = firestore.client()

# A single recursive query over a large collection times out on the server, so
# each collection is split into ranges of top-level documents, which are paged
# through independently and in parallel.
PAGE_SIZE = 1000
DOCUMENTS_PER_RANGE = 25
WORKERS = 16
RETRIES = 3

def set(my_dict, path, value):
    """Given `foo`, ['key1', 'key2', 'key3'], 'something', set foo['key1']['key2']['key3'] = 'something'"""
    here = my_dict
    for key in path[:-1]:
        # Create key with empty dictionary if it does not exist and move pointer.
        here = here.setdefault(key, {})
    # Merge instead of assigning, so a document never replaces subcollections
    # that were added to it before.
    here.setdefault(path[-1], {}).update(value)

def fetch_page(query):
    for attempt in range(RETRIES):
        try:
            return list(query.stream())
        except (exceptions.ServiceUnavailable, exceptions.DeadlineExceeded):
            if attempt == RETRIES - 1:
                raise
            time.sleep(2 ** attempt)

def export_range(collection, first_id, next_id):
    """Exports the top-level documents from `first_id` up to `next_id`
    (exclusive), including all of their subcollections."""
    # Document paths sort by segment, so the range also contains every
    # descendant of the documents in it.
    query = collection.recursive().where(
        filter=FieldFilter('__name__', '>=', collection.document(first_id))
    )
    if next_id is not None:
        query = query.where(
            filter=FieldFilter('__name__', '<', collection.document(next_id))
        )
    # Recursive queries are ordered by document path already.
    query = query.limit(PAGE_SIZE)

    data = {}
    count = 0
    last = None
    while True:
        documents = fetch_page(query.start_after(last) if last else query)
        for doc in documents:
            set(data, doc.reference.path.split('/')[1:], doc.to_dict())
        count += len(documents)
        if len(documents) < PAGE_SIZE:
            return data, count
        last = documents[-1]

def ranges(collection):
    # Includes documents without fields that only hold subcollections.
    ids = sorted(doc.id for doc in collection.list_documents(page_size=PAGE_SIZE))
    for start in range(0, len(ids), DOCUMENTS_PER_RANGE):
        end = start + DOCUMENTS_PER_RANGE
        yield ids[start], ids[end] if end < len(ids) else None

# Optionally pass collection names to export only those.
names = sys.argv[1:] or [collection.id for collection in db.collections()]

with ThreadPoolExecutor(max_workers=WORKERS) as executor:
    for collection_name in names:
        print(f"Exporting {collection_name}...")
        collection = db.collection(collection_name)
        json_file = collection_name + '.json'

        futures = [
            executor.submit(export_range, collection, first_id, next_id)
            for first_id, next_id in ranges(collection)
        ]
        data = {}
        total = 0
        for done, future in enumerate(as_completed(futures), 1):
            # Ranges never share a top-level document, so they merge without
            # overlap.
            range_data, count = future.result()
            data.update(range_data)
            total += count
            print(f"  {done}/{len(futures)} ranges, {total} documents", end='\r')
        print()

        with open(json_file, 'w') as file:
            json.dump(data, file, indent=4, sort_keys=True, default=str, ensure_ascii=False)

        print(f"☑️  Exported {total} documents to {json_file}.")
