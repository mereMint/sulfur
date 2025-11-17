from dotenv import load_dotenv
import os

load_dotenv()

db_pass = os.getenv('DB_PASS', '')
print(f'DB_PASS value: "{db_pass}"')
print(f'DB_PASS length: {len(db_pass)}')
print(f'DB_PASS is empty string: {db_pass == ""}')
print(f'DB_PASS is None: {db_pass is None}')
