#-.- coding: utf-8 -.-
from app import db
from app.models.easy import *
from app.models.student_info import User_info_table_interface


class Admins_vuses(db.Model):
    __tablename__ = 'admins_vuses'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    vus_id = db.Column(db.Integer, db.ForeignKey('VUS.id'))
    is_write = db.Column(db.Boolean)

class VUS(db.Model,User_info_table_interface):
    __tablename__ = 'VUS'
    id = db.Column(db.Integer, primary_key=True)
    number    = db.Column(db.Integer)
    code      = db.Column(db.Integer)
    name1     = db.Column(db.String(120))
    name2     = db.Column(db.String(120))
    rank      = db.Column(db.String(60) )
    tech_type = db.Column(db.String(120))

    users = db.relationship("User", secondary="admins_vuses", back_populates="vuses")
    is_active = db.Column(db.Boolean, default=True)

    def to_string(self):
        return '%03d %03d' % (self.number, self.code)

    def __init__(self):
        self.section_name = u'ВУС'
        self.is_fixed     = True
        self.placeholders = {
            'number' : u'123',
            'code' : u'123',
            'name1' : u'Расчетно-аналитических станций РХБЗ',
            'name2' : u'Вычислитель',
            'rank' : u'Рядовой',
            'tech_type' : u'Расчетно-аналитические станции РХБЗ',
        }
        self.en2ru = {
            'id' : None,
            'is_active' : None,
            'number' : u'Номер',
            'code' : u'Код',
            'name1' : u'Принадлежность',
            'name2' : u'Должность',
            'rank' : u'Звание',
            'tech_type' : u'Тип (марка) вооружения (военной техники)',
        }
        self.readonly_fields = set()



class User(db.Model):
    __tablename__ = 'user'
    id       = db.Column(db.Integer, primary_key=True)
    login    = db.Column(db.String(120), index=True, unique=True)
    password = db.Column(db.String(120), unique=False)
    role     = db.Column(db.SmallInteger, default=USER_STATES['ROLE_USER'])
    vus_id   = db.Column(db.Integer, db.ForeignKey('VUS.id'))
    approved = db.Column(db.Boolean, default=False)
    entrance_year = db.Column(db.Integer)
    processing_consent = db.Column(db.Boolean, default=False)

    students_info = db.relationship('Student_info', back_populates='user', uselist=False)
    vuses = db.relationship( "VUS", secondary="admins_vuses", back_populates="users")

    def get_id(self):
        return unicode(self.id)

    def is_active(self):
        return True 

    def is_authenticated(self):
        return True

    def __repr__(self):
        return '<User %r, %r>' % (self.login, self.password)

class Document(db.Model):
    __tablename__ = 'document'
    id       = db.Column(db.Integer, primary_key=True)
    name     = db.Column(db.String(120), index=True, unique=True)
    filename = db.Column(db.String(120))
    vus_id   = db.Column(db.Integer, db.ForeignKey('VUS.id'))

    #vus = db.relationship('VUS', back_populates='document', uselist=False)


