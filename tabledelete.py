import lancedb
import os

def clean_lancedb(db_path="./code_index_db", table_name="code_vectors"):
    """
    Cleans the LanceDB environment by dropping the existing table 
    or deleting all records.
    """
    if not os.path.exists(db_path):
        print(f"ℹ️ Database path '{db_path}' does not exist. Nothing to clean.")
        return

    # Connect to the local database
    db = lancedb.connect(db_path)

    try:
        # Option 1: Drop the entire table (Recommended for schema changes)
        if table_name in db.table_names():
            print(f"🗑️ Dropping table: {table_name}...")
            db.drop_table(table_name)
            print(f"✅ Table '{table_name}' has been removed.")
        else:
            print(f"ℹ️ Table '{table_name}' not found.")

        # Option 2: Optional - Delete the physical folder for a total reset
        # import shutil
        # shutil.rmtree(db_path)
        # print(f"✅ Physical database folder '{db_path}' deleted.")

    except Exception as e:
        print(f"❌ An error occurred during cleaning: {e}")

if __name__ == "__main__":
    # Ensure this matches the path and table name used in your storage.py
    clean_lancedb()