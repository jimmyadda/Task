import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json
import sqlite3
from flask import redirect, request, session
import flask_login
from flask_mail import Mail, Message
import os
import smtplib
import logging



###globals
path = os.getcwd()
database_filename = "Tasker.db"
#Mail Settings
with open('config.json') as config_file:
    config_data = json.load(config_file)
mail_settings = config_data['mail_settings']

#functions
def database_write(sql,data=None):
    connection = sqlite3.connect(database_filename)
    connection.row_factory = sqlite3.Row
    db = connection.cursor()
    row_affected = 0
    if data:
        row_affected = db.execute(sql, data).rowcount
    else:
        row_affected = db.execute(sql).rowcount
    connection.commit()
    db.close()
    connection.close()

    return row_affected

def database_read(sql,data=None):
    connection = sqlite3.connect(database_filename)
    connection.row_factory = sqlite3.Row
    db = connection.cursor()

    if data:
         db.execute(sql, data)
    else:
         db.execute(sql)
    records = db.fetchall()    
    rows = [dict(record) for record in records]

    db.close()
    connection.close()
    return rows


def send_mail(notification=''):
    form = session['formData']
    user = flask_login.current_user.get_dict() 
    task_url = request.host_url + f"/main?folderid={form['folderid']}&id={form['id']}"
    assignTo_mail = database_read(f"select email from accounts WHERE name ='{form['assignto']}' order by name;")
    Project_data= database_read(f"select name from folders WHERE id ='{form['folderid']}' order by name;")
    #Create Main
    projname= Project_data[0]['name']
    subject="Task Number : [#" +form['id']+" ] -" +form['title']
    sender_email= str(mail_settings['MAIL_USERNAME'])
    receiver_email = str(assignTo_mail[0]['email'])
    #Build Msg
    # Email content
    email_body = '''
                <b>Subject:</b> {Subject}<br>
                <b>Reported By:</b> {Reported By}<br>
                <b>Assigned To:</b> {Assigned To}<br>
                <b>Project:</b> {Project}<br>
                <b>TaskID:</b> {TaskID}<br>
                <b>Category:</b> {Category}<br>
                <b>Priority:</b> {Priority}<br>
                <b>Status:</b> {Status}<br>
                <b>Date Created:</b> {Date Created}<br>
                <br>
                <b>Description:</b><br>
                {Description}
                '''
        # Email data
    email_data = {
        'Subject': subject,    
        'Reported By': user['userid'],
        'Assigned To': form['assignto'],
        'Project': projname,
        'TaskID': form['id'],
        'Category': form['category'],
        'Priority': form['priority'],
        'Status': form['status'],
        'Date Created': form['created'],
        'Description': form['desc']
        }
    email_content = email_body.format(**email_data)
    email_content += f"<br><p><a href={task_url}>Go to Task</a></p>"
    # Create MIME message
    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = receiver_email    
    message['Subject'] = str(subject)
    message.attach(MIMEText(email_content, 'html',_charset='utf-8'))

    # Connect to the SMTP server and send the email
    with smtplib.SMTP(mail_settings['MAIL_SERVER'], 587) as server:
        server.starttls()
        server.login(mail_settings['MAIL_USERNAME'], mail_settings['MAIL_PASSWORD'])
        server.sendmail(sender_email, receiver_email, message.as_string().encode("UTF-8"))
        server.close()
    print('Email sent!')
    #Log
    return redirect(f"/main?folderid={form['folderid']}&id={form['id']}")


def send_notification(data):
    form = session['formData']
    user = flask_login.current_user.get_dict() 

    subject="Notification Mail"
    assignTo_mail = database_read(f"select email from accounts WHERE name ='{form['assignto']}' order by name;")
    task_url = request.host_url + f"/main?folderid={form['folderid']}&id={form['id']}"

    sender_email= str(mail_settings['MAIL_USERNAME'])
    receiver_email = str(assignTo_mail[0]['email'])
    form = session['formData']
    user = flask_login.current_user.get_dict() 
    email_body = '''
                <b>Subject:</b> {Subject}<br>
                <b>Reported By:</b> {Reported By}<br>
                <b>Assigned To:</b> {Assigned To}<br>
                <b>TaskID:</b> {TaskID}<br>
                <b>Date Created:</b> {Date Created}<br>
                <br>
                <b>Note:</b><br>
                {note}
                ''' 
    # Email data
    email_data = {
            'Subject': subject,    
            'Reported By': user['userid'],
            'Assigned To': form['assignto'],
            'TaskID': form['id'],
            'Date Created': form['created'],
            'note': data
            } 
    email_content = email_body.format(**email_data)
    email_content += f"<br><p><a href={task_url}>Go to Task</a></p>"
    # Create MIME message
    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = receiver_email    
    message['Subject'] = str(subject)
    message.attach(MIMEText(email_content, 'html',_charset='utf-8'))

    # Connect to the SMTP server and send the email
    with smtplib.SMTP(mail_settings['MAIL_SERVER'], 587) as server:
        server.starttls()
        server.login(mail_settings['MAIL_USERNAME'], mail_settings['MAIL_PASSWORD'])
        server.sendmail(sender_email, receiver_email, message.as_string().encode("UTF-8"))
        server.close()
    print('Email sent!')
    #Log
    return "ok"