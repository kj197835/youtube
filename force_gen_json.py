from fetch_data import generate_frontend_json, get_credentials, fetch_channel_info, get_session, build
import config
import shutil

session = get_session()
# Need CID?
# Just dummy or fetch?
# Logic requires CID for other parts?
# I'll just hardcode or fetch if easy.
# Actually I can just modify generate_frontend_json to NOT fail if CID is missing?
# Or query channel from DB.
from database import Channel
ch = session.query(Channel).first()
cid = ch.id if ch else "UNKNOWN"
print(f"Using CID: {cid}")

generate_frontend_json(session, cid)
print("Manually generated JSON.")
