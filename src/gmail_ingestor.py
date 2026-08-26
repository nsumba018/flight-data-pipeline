import imaplib
import json
import os
from email import policy
from email.parser import BytesParser
from pathlib import Path

from dotenv import load_dotenv


# =========================================================
# CONFIGURATION
# =========================================================

load_dotenv()

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993

SENDER = "aimsdata@rwandair.com"
ATTACHMENT_NAME = "X2-FS-.txt"

RAW_DATA_DIR = Path("data/raw")
STATE_FILE = Path("data/ingestion_state.json")


# =========================================================
# VALIDATE CONFIGURATION
# =========================================================

if not GMAIL_ADDRESS:
    raise ValueError("GMAIL_ADDRESS is missing from .env")

if not GMAIL_APP_PASSWORD:
    raise ValueError("GMAIL_APP_PASSWORD is missing from .env")


# =========================================================
# GMAIL CONNECTION
# =========================================================

def connect_to_gmail():

    print("Connecting to Gmail...")

    mail = imaplib.IMAP4_SSL(
        IMAP_SERVER,
        IMAP_PORT
    )

    mail.login(
        GMAIL_ADDRESS,
        GMAIL_APP_PASSWORD
    )

    mail.select("INBOX")

    print("Successfully connected to Gmail.")

    return mail


# =========================================================
# STATE MANAGEMENT
# =========================================================

def load_last_uid():

    if not STATE_FILE.exists():
        return None

    with open(STATE_FILE, "r") as file:
        state = json.load(file)

    return state.get("last_processed_uid")


def save_last_uid(uid):

    STATE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    state = {
        "last_processed_uid": uid
    }

    with open(STATE_FILE, "w") as file:
        json.dump(
            state,
            file,
            indent=4
        )


# =========================================================
# FIND AIMS EMAILS
# =========================================================

def find_aims_emails(mail):

    status, data = mail.uid(
        "SEARCH",
        None,
        f'FROM "{SENDER}"'
    )

    if status != "OK":
        raise RuntimeError(
            "Failed to search Gmail."
        )

    uids = data[0].split()

    return uids


# =========================================================
# FETCH EMAIL
# =========================================================

def fetch_email(mail, uid):

    status, message_data = mail.uid(
        "FETCH",
        uid,
        "(RFC822)"
    )

    if status != "OK":
        print(
            f"Could not fetch UID {uid.decode()}"
        )
        return None

    raw_email = message_data[0][1]

    message = BytesParser(
        policy=policy.default
    ).parsebytes(raw_email)

    return message


# =========================================================
# EXTRACT ATTACHMENT
# =========================================================

def extract_attachment(mail, uid):

    message = fetch_email(
        mail,
        uid
    )

    if message is None:
        return False

    for part in message.iter_attachments():

        filename = part.get_filename()

        if filename == ATTACHMENT_NAME:

            RAW_DATA_DIR.mkdir(
                parents=True,
                exist_ok=True
            )

            uid_number = uid.decode()

            output_filename = (
                f"X2-FS_uid_{uid_number}.txt"
            )

            output_path = (
                RAW_DATA_DIR / output_filename
            )

            with open(
                output_path,
                "wb"
            ) as file:

                file.write(
                    part.get_payload(
                        decode=True
                    )
                )

            print(
                f"Extracted UID {uid_number}: "
                f"{output_path}"
            )

            return True

    print(
        f"UID {uid.decode()} "
        f"does not contain {ATTACHMENT_NAME}"
    )

    return False


# =========================================================
# INITIAL HISTORICAL LOAD
# =========================================================

def initial_load(mail, uids):

    print()
    print(
        f"Initial load: processing "
        f"{len(uids)} AIMS email(s)..."
    )
    print()

    highest_uid = None

    for uid in uids:

        extract_attachment(
            mail,
            uid
        )

        highest_uid = uid

    if highest_uid:

        highest_uid_number = int(
            highest_uid.decode()
        )

        save_last_uid(
            highest_uid_number
        )

        print()
        print(
            f"Initial load complete."
        )

        print(
            f"Last processed UID: "
            f"{highest_uid_number}"
        )


# =========================================================
# MAIN
# =========================================================

def main():

    mail = None

    try:

        mail = connect_to_gmail()

        last_uid = load_last_uid()

        all_uids = find_aims_emails(
            mail
        )

        print(
            f"Found {len(all_uids)} "
            f"AIMS email(s)."
        )

        # ---------------------------------------------
        # First run
        # ---------------------------------------------

        if last_uid is None:

            initial_load(
                mail,
                all_uids
            )

        # ---------------------------------------------
        # Future runs
        # ---------------------------------------------

        else:

            new_uids = [
                uid
                for uid in all_uids
                if int(uid.decode()) > last_uid
            ]

            print(
                f"Last processed UID: "
                f"{last_uid}"
            )

            print(
                f"New AIMS emails: "
                f"{len(new_uids)}"
            )

            for uid in new_uids:

                extract_attachment(
                    mail,
                    uid
                )

                save_last_uid(
                    int(uid.decode())
                )

    finally:

        if mail is not None:

            try:
                mail.logout()

            except Exception:
                pass


if __name__ == "__main__":
    main()