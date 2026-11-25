"""Promote an existing account to administrator. Run only from a trusted server shell."""
import argparse, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.app.core.database import Base, engine, SessionLocal
from backend.app.models.user import User

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("email")
    args=parser.parse_args()
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        user=db.query(User).filter(User.email==args.email.lower()).first()
        if not user: raise SystemExit("User not found. Create the account first.")
        user.is_superuser=True
        db.commit()
        print(f"Administrator enabled for {user.email}. Protect this account with a strong password and MFA at the identity-provider level.")
if __name__=="__main__": main()
