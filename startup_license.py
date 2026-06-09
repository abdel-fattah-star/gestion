import hashlib
import os
import sys
import platform
from datetime import datetime

SECRET = "A3H_SECRET_2026"


# =========================
# MACHINE ID
# =========================
def get_machine_id():

    raw = (
        platform.node() +
        platform.processor()
    )

    return hashlib.sha256(
        raw.encode()
    ).hexdigest()


# =========================
# VERIFY LICENSE
# =========================
def verify_license():

    # dossier application
    BASE_DIR = os.path.dirname(
        os.path.abspath(sys.argv[0])
    )

    path = os.path.join(
        BASE_DIR,
        "license.key"
    )

    # -------------------------
    # fichier licence existe ?
    # -------------------------
    if not os.path.exists(path):

        raise Exception("LICENCE EXPIREE")
    # -------------------------
    # lecture licence
    # -------------------------
    try:

        with open(path, "r") as f:

            saved_machine_id = f.readline().strip()
            saved_license_key = f.readline().strip()
            expiry_date = f.readline().strip()

    except:

        print("ERREUR LECTURE LICENCE")
        sys.exit(1)

    # -------------------------
    # verification machine
    # -------------------------
    current_machine_id = get_machine_id()

    if current_machine_id != saved_machine_id:

        print("LICENCE NON VALIDE POUR CETTE MACHINE")
        sys.exit(1)

    # -------------------------
    # verification clé
    # -------------------------
    expected_key = hashlib.sha256(
        (saved_machine_id + SECRET).encode()
    ).hexdigest()

    if expected_key != saved_license_key:

        print("LICENCE INVALIDE")
        sys.exit(1)

    # -------------------------
    # verification date
    # -------------------------
    try:

        expiry = datetime.strptime(
            expiry_date,
            "%d/%m/%Y"
        ).date()

    except:

        print("DATE LICENCE INVALIDE")
        sys.exit(1)

    today = datetime.today().date()

    if today > expiry:

        print("LICENCE EXPIREE")
        sys.exit(1)

    # -------------------------
    # licence OK
    # -------------------------
    return True