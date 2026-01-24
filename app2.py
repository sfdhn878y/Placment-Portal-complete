from flask import Flask

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer,primary_key = True)
    name = db.Column(db.String(200))


class Student_profile(db.Model):
    id = db.Column(db.Integer,primary_key = True)
    cgpa = db.Column(db.String(200))

    user_id = db.Column(db.Integer,db.ForeignKey("user.id"),unique=True)
