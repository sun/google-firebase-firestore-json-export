# Google Firebase Firestore JSON Export

Exports a Google Firestore database recursively including all collections and
subcollections into plain JSON files.

Uses the built-in `recursive()` flag of the Query class:
https://cloud.google.com/python/docs/reference/firestore/latest/query#recursive

Allows you to analyze the data in your Firestore database locally without being
constrained to Firestore or BigQuery limitations.  For example:

- Finding incomplete documents
- Finding broken document references
- Finding documents without fields
- Querying subcollections of collections without documents

You can use custom scripts or the powerful [jq command-line JSON processor](https://jqlang.github.io/jq/)
to perform complex lookups, such as [this example](https://unix.stackexchange.com/a/466241/228730),
or the following, which extracts all documents that do not have the key `'createdBy'`:

```console
jq -r 'with_entries(select(.value.createdBy == null))' collection.json
```


:warning: **Warning**: A complete export causes 1 read operation for every document in
your Firestore database.  Depending on the size of your database, this might
induce costs for database reads.


## Requirements

- Python 3


## Setup and Usage

1. Install firebase-admin via pip
    ```console
    $ pip3 install firebase-admin
    ```

2. Run export to JSON.
    ```console
    $ python3 main.py
    ```


## Todos

- Serialize TimestampWithNanoseconds (instead of converting to string)
  https://code.luasoftware.com/tutorials/google-cloud-firestore/python-firestore-query-documents-to-json

- Serialize document references (e.g. as document path instead of address)
  ```
  "ref": "<google.cloud.firestore_v1.document.DocumentReference object at 0x111ef1c50>"
  ```

- Import into local Firestore emulator

- Allow to export as line-delimited JSON (LDJSON) to allow streaming and avoid
  loading the whole db into memory when importing.
