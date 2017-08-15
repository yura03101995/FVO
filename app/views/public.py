#-.- coding: utf-8 -.-
from app import app, db
from flask import render_template, request, flash, redirect, url_for, abort
from flask_login import login_required, login_user, current_user, logout_user
from sqlalchemy import desc
from app.models import User, VUS, Document, Comments, Student_info, Basic_information 
from app.models import Certificates_change_name, Communications, Passports,International_passports
from app.models import Registration_certificates, Middle_education, Spec_middle_education 
from app.models import High_education, Military_education, Languages, Mothers_fathers 
from app.models import Brothers_sisters_children, Married_certificates, Personal_data
from app.models.easy import *
from app.views.easy import *

from werkzeug.security import check_password_hash
import json
import sys
from hidden import user_role

########## data workers, перенести в отдельный модуль перед финальным тестированием
class InputValue:
    def __init__(self, eng, rus, inp_type, placeholder, is_readonly=False, value=''):
        self.eng = eng
        self.rus = rus
        self.inp_type = inp_type
        self.placeholder = placeholder
        self.value = value
        self.is_readonly = is_readonly
        self.valid = ( self.eng is not None and self.rus is not None )

    def copy(self):
        return InputValue( eng=self.eng, rus=self.rus, inp_type=self.inp_type, 
                           placeholder=self.placeholder, is_readonly=self.is_readonly, value=self.value )

def get_quiz_state(user_id):
    student_info = User.query.get(user_id).students_info

    has_unchecked = False
    has_unfilled  = False
    has_declined  = False
    for table in get_user_tables():
        state = student_info['table_'+table]
        if state == TABLE_STATES['DECLINED']:
            has_declined = True 
        elif state == TABLE_STATES['EDITED']:
            has_unchecked = True
        elif state == TABLE_STATES['NOT_EDITED']:
            has_unfilled  = True

    state = QUIZ_STATES['APPROVED']
    if has_unchecked:
        state = QUIZ_STATES['NOT_CHECKED']
    elif has_declined:
        state = QUIZ_STATES['DECLINED']
    elif has_unfilled:
        state = QUIZ_STATES['NOT_FILLED']

    if state == QUIZ_STATES['APPROVED']:
        for table in get_admin_tables():
            state = student_info['table_'+table]
            if state != TABLE_STATES['APPROVED']:
                state = QUIZ_STATES['NOT_CHECKED']
    
    return state

def fill_section_values(fields, user_info):
    for field in fields:
        if user_info[field.eng] is not None:
            field.value = user_info[field.eng]
    return True

def get_sections_data_by_id(user_id, tables):
    student_info = User.query.get( user_id ).students_info

    sections_arr = []
    for table in tables:
        fields_table = get_fields( table )
        s = get_class_by_tablename( table )()
 
        fields_table = [InputValue(
                            x[0], 
                            s.get_russian_name(x[0]), 
                            x[1], 
                            s.placeholder(x[0]),
                            is_readonly=s.is_readonly(x[0])
                        ) for x in fields_table]
        fields_table = filter(lambda x: x.valid, fields_table)

        section_info = { 
                         'fields': fields_table, 'is_fixed': s.is_fixed, 'table_name':table, 
                         'section_name': s.get_section_name(), 'section_number': len(sections_arr) 
                       }
        if s.is_fixed:
            table_record = student_info[table]
            if table_record:
                fill_section_values(section_info['fields'], table_record) 
        else:
            table_records = student_info[table]
            if table_records is not None:
                section_info['filled_fields'] = []
                for i in range(len(table_records)):
                    element = [x.copy() for x in section_info['fields']]
                    fill_section_values(element, table_records[i])
                    section_info['filled_fields'].append(element)
        sections_arr.append(section_info)

    return sections_arr


def get_section_statuses(user_id):
    student_info = User.query.get( user_id ).students_info
    return dict( map(lambda s: (s[0][len('table_'):], student_info[s[0]]), get_fields('student_info')) )

def get_section_comments(user_id):
    student_info = User.query.get( user_id ).students_info
    d = {}
    for table in get_user_tables():
        val = student_info['comments'][table + '_comment']
        d[table] = val if val is not None else ''
    return d
##########

@app.route('/')
@app.route('/index')
@app.route('/ready')
@login_required
def ready():
    if user_role() < 1:
        return redirect(url_for('profile'))

    if user_role()==USER_STATES['ROLE_ADMIN']:
        users = db.session.query(User).filter_by(role = 0, approved = True, vus_id=current_user.vus_id).order_by(desc(User.entrance_year)).order_by(User.vus_id)
    else:
        users = db.session.query(User).filter_by(role = 0, approved = True).order_by(desc(User.entrance_year)).order_by(User.vus_id)
    documents = Document.query.all()

    vuses = VUS.query.all()

    userInfo = []
    for user in users:
        vusString = ''
        for vus in vuses:
            if vus.id == user.vus_id:
                vusString = vus.to_string()
                break

        userInfo.append({
            'id' : user.id,
            'lastName' : user.students_info.basic_information.last_name,
            'firstName' : user.students_info.basic_information.first_name,
            'middleName' : user.students_info.basic_information.middle_name,
            'year' : user.login[-4:],
            'vus' : vusString
        })

    docs = []
    for document in documents:
        docs.append({
            'id' : document.id,
            'name' : document.name
        })

    return render_template('ready.html', title=u'Готовые', tab_active=1, users=userInfo, 
        docs=docs, vuses=vuses, is_readonly=user_role()==USER_STATES['ROLE_READONLY_ADMIN'])

@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'GET':
        role = user_role()
        if role < 0:
            return render_template('login.html', navprivate=True, title=u'Вход')
        elif role == 0:
            return redirect(url_for('profile'))
        else:
            return redirect(url_for('ready'))

    data = json.loads(request.data)
    login = data['login']
    password = data['password']
    registered_user = User.query.filter_by(login=login).first()

    if registered_user is None or not check_password_hash(registered_user.password, password):
        return gen_error(u'Неправильная пара ЛОГИН-ПАРОЛЬ')
    login_user(registered_user)
    return gen_success()

@app.route('/logout',methods=['POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/inprocess')
@login_required
def inprocess():
    role = user_role()
    if role < 1:
        abort(404)
    if( role == USER_STATES[ 'ROLE_ADMIN' ]):
        users = User.query.filter_by(role = 0, approved = False, vus_id=current_user.vus_id)
    else:
        users = User.query.filter_by(role = 0, approved = False)

    vuses = { vus.id : vus for vus in VUS.query.all() }

    return render_template('inprocess.html', title=u'В процессе', tab_active=2, users = users, 
        vuses = vuses, is_readonly=role==USER_STATES['ROLE_READONLY_ADMIN'])

@app.route('/inprocess/<user_id>')
@login_required
def to_page_approve_user(user_id):
    if user_role() < 1:
        abort(404)

    sections_arr = get_sections_data_by_id(user_id, get_admin_tables() + get_user_tables())
    admin_sections = set(get_admin_tables())

    section_statuses = get_section_statuses(user_id)
    comments = get_section_comments(user_id)
    status = get_quiz_state(user_id)

    return render_template('user-admin.html', title=u'Одобрение аккаунта', sections=sections_arr, table_states=TABLE_STATES,
        quiz_status=status, section_statuses=section_statuses, user_id=user_id, navprivate=True, quiz_states=QUIZ_STATES, 
        comments=comments, is_readonly=user_role()==USER_STATES['ROLE_READONLY_ADMIN'], admin_sections=admin_sections)


@app.route('/documents')
@login_required
def documents():
    if user_role() < 1:
        abort(404)
    if user_role() != USER_STATES['ROLE_ADMIN']:
        vuses = VUS.query.all()
        docs = Document.query.all()
    else:
        vuses = VUS.query.get(current_user.vus_id)
        vuses = [vuses]
        docs = Document.query.filter_by(vus_id=current_user.vus_id)
    vuses_name_by_id = { vus.id : vus.to_string() for vus in vuses }
    return render_template('documents.html', title=u'Документы', tab_active=3, vuses=vuses, 
        vuses_name_by_id=vuses_name_by_id, docs=docs, 
        is_readonly=user_role()==USER_STATES['ROLE_READONLY_ADMIN'])

@app.route('/rule_admins')
@login_required
def rule_admins():
    if user_role() < 1:
        abort(404)
    vuses = VUS.query.all()
    admins = User.query.filter(User.role > 0).filter(User.role != USER_STATES['ROLE_SUPER_ADMIN'])
    return render_template('rule_admins.html', title=u'Управление администраторами', 
        tab_active=7, is_super_admin=user_role()==USER_STATES['ROLE_SUPER_ADMIN'], 
        admins=admins, vuses=vuses)

@app.route('/account_creator')
@login_required
def account_creator():
    if user_role() < 1:
        abort(404)
    if current_user.role==USER_STATES['ROLE_ADMIN']:
        vuses = VUS.query.get(current_user.vus_id)
        vuses = [vuses]
    else:
        vuses = VUS.query.all()

    return render_template('account_creator.html', title=u'Создание аккаунтов', tab_active=4, 
        vuses=vuses, is_super_admin=current_user.role==USER_STATES['ROLE_SUPER_ADMIN'],
        is_readonly=current_user.role==USER_STATES['ROLE_READONLY_ADMIN'])

@app.route('/search')
@login_required
def search():
    if user_role() < 1:
        abort(404)

    vuses = VUS.query.all()

    return render_template('search.html', title=u'Поиск', tab_active=5, vuses=vuses)

@app.route('/profile')
@login_required
def profile():
    if user_role() > 0:
        return redirect('ready')
        
    processing_consent = current_user.processing_consent
    sections_arr     = get_sections_data_by_id(current_user.id, get_user_tables())
    section_statuses = get_section_statuses(current_user.id)
    is_approved      = current_user.approved
    quiz_status      = get_quiz_state(current_user.id)
    comments         = get_section_comments(current_user.id)
    if processing_consent:
        return render_template('user.html', title=u'Данные', sections=sections_arr, 
            table_states=TABLE_STATES,
            section_statuses=section_statuses, is_approved=is_approved, 
            quiz_status=quiz_status, quiz_states=QUIZ_STATES,
            user_id=current_user.id, comments=comments, navprivate=True)
    else:
        return render_template('processing_consent.html', title=u'Согласие на обработку',
         navprivate=True)

@app.route('/add_vus')
@login_required
def add_vus():
    if user_role() < 1:
        abort(404)

    s = VUS();
    fields = get_fields( 'VUS' )
    fields = [ InputValue( x[0], 
                s.get_russian_name(x[0]), 
                x[1], 
                s.placeholder(x[0])
                ) for x in fields]
    fields = filter(lambda x: x.valid, fields)
    return render_template('add_vus.html',fields=fields, tab_active=6, 
        is_super_admin=user_role()==USER_STATES['ROLE_SUPER_ADMIN'])