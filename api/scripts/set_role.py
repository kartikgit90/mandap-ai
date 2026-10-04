"""Give a user a role (couple, editor or admin).

Run it in Google Cloud Shell, which is already logged in as you:

    cd mandap-ai/api
    pip install --quiet firebase-admin
    python scripts/set_role.py you@example.com admin

The user must have logged in to the website at least once (so Firebase knows them).
They need to log out and back in to see the new role.

Why a script and not a button: only the project owner should be able to make admins.
This runs with your own Google identity, so nobody using the website can do it.
"""

import sys

import firebase_admin
from firebase_admin import auth

ROLES = {"couple", "editor", "admin"}


def main() -> None:
    if len(sys.argv) != 3 or sys.argv[2] not in ROLES:
        print("Usage: python scripts/set_role.py <email> <couple|editor|admin>")
        sys.exit(1)

    email, role = sys.argv[1], sys.argv[2]
    firebase_admin.initialize_app(options={"projectId": "mandap-ai"})

    try:
        user = auth.get_user_by_email(email)
    except auth.UserNotFoundError:
        print(f"No user with email {email}. Log in to the website once first.")
        sys.exit(1)

    claims = dict(user.custom_claims or {})
    claims["role"] = role
    auth.set_custom_user_claims(user.uid, claims)
    print(f"Done: {email} is now '{role}'. Log out and log back in to see it.")


if __name__ == "__main__":
    main()
