from datetime import datetime
from ..extensions import db


class Room(db.Model):
    __tablename__ = "rooms"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(6), unique=True, nullable=False)
    host_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    # waiting | playing | finished
    status = db.Column(db.String(20), default="waiting", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "host_id": self.host_id,
            "status": self.status,
        }
