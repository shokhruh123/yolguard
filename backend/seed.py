"""Seed: admin/specialist/drivers + vehicles. Passwords hashed."""
from app.db import SessionLocal, Base, engine
from app import models, security

Base.metadata.create_all(bind=engine)
db = SessionLocal()
def user(phone, pw, name, role):
    u = db.query(models.User).filter_by(phone=phone).first()
    if not u:
        u = models.User(phone=phone, password_hash=security.hash_password(pw), full_name=name, role=role)
        db.add(u); db.commit(); db.refresh(u)
    return u

admin = user("+998900000001", "admin123", "Admin", "admin")
spec = user("+998900000002", "spec1234", "Specialist", "specialist")
d1 = user("+998900000011", "driver123", "Driver A", "driver")
d2 = user("+998900000012", "driver123", "Driver B", "driver")
for owner, plate, make, model in [(d1, "01A777AA", "Chevrolet", "Cobalt"), (d2, "01B888BB", "Chevrolet", "Nexia")]:
    if not db.query(models.Vehicle).filter_by(plate=plate).first():
        db.add(models.Vehicle(owner_id=owner.id, plate=plate, make=make, model=model, year=2020))
db.commit()
print("seed ok:", [u.phone for u in (admin, spec, d1, d2)])
