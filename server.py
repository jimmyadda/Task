import base64
import pathlib
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
from time import sleep
from flask import Flask, send_file,flash,render_template,request,redirect, send_from_directory, session
import flask_login
import sqlite3
from datetime import datetime
import uuid
import hashlib
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
from create_account import create_account
from mail import send_notification
import json


app = Flask(__name__)
database_filename = "Tasker.db"
app.config['SECRET_KEY'] = 'AvivimSecretKey'
path = os.getcwd()

UPLOAD_FOLDER = os.path.join(path, 'uploads')
if not os.path.isdir(UPLOAD_FOLDER):
    os.mkdir(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
#Mail Settings
with open('config.json') as config_file:
    config_data = json.load(config_file)
mail_settings = config_data['mail_settings']

app.config.update(mail_settings)
mail = Mail(app)
#Logs
handler = logging.FileHandler('LogFile.log') # creates handler for the log file
app.logger.addHandler(handler) # Add it to the built-in logger
app.logger.setLevel(logging.DEBUG)         # Set the log level to debug
logger = app.logger
#Log in 
login_manager = flask_login.LoginManager()
login_manager.init_app(app)


class User(flask_login.UserMixin):
    def __init__(self,userid,email,name):
        self.email = email
        self.name = name
        self.id = userid
    def get_dict(self):
        return{'userid': self.id,'email': self.email, 'name': self.name}

@login_manager.user_loader
def load_user(userid):
    users = database_read(f"select  * from accounts where userid='{userid}';")
    if len(users)!=1:
        return None
    else:
        user = User(users[0]['userid'],users[0]['email'],users[0]['name'])
        user.id = userid
        return user


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


@app.route("/")
def index_page():
    if flask_login.current_user.is_authenticated:
        logger.info(str(flask_login.current_user.get_dict()) + "Has Logged in")
        return redirect("/main")
    else:
        return redirect("/login")


@app.route("/register", methods=['GET'])
def registration_page():
    return render_template('register.html', alert="")

@app.route("/register", methods=['POST'])
def registration_request():
    form = dict(request.values)
    
    folderid="0"
    if 'folderid' in request.values:
        folderid = request.values['folderid']
    id="1"
    if 'id' in request.values:
        id = request.values['id']
    reg_email = request.values['email']
    if reg_email:
        ok = create_account(form)
        session['formData'] = form
        print('ok:' ,ok)
        if ok == 1:            
            user = load_user(form['userid'])
            logger.info("New User Created: "+ user.name)           
            flask_login.login_user(user)            
            return redirect('/main') 
        else:
            return redirect(f"/error") 
    else:
         return render_template('/register.html',alert = "Please insert valid email to register!")


@app.route("/login", methods=['GET'])
def login_page():
    return render_template('login.html',alert ="")

@app.route("/login", methods=['POST'])
def login_request():
    form = dict(request.values)
    users = database_read("select * from accounts where userid=:userid",form)

    if len(users) == 1: #user name exist, password not checked
        salt = users[0]['salt']
        saved_key = users[0]['password']
        generated_key = hashlib.pbkdf2_hmac('sha256',form['password'].encode('utf-8'),salt.encode('utf-8'),10000).hex()

        if saved_key == generated_key: #password match
            user = load_user(form['userid'])
            logger.info(f"Login successfull - '{form['userid']}'  date: {str(datetime.now())}")
            flask_login.login_user(user)
            return redirect('/main')
        else: #password incorrect
           logger.info(f"Login Failed - '{form['userid']}'  date: {str(datetime.now())}")
           return render_template('/login.html',alert = "Invalid user/password. please try again.") 
    else: #user name does not exist
        logger.info(f"Login Failed - '{form['userid']}'  date: {str(datetime.now())}")
        return render_template('/login.html',alert = "Invalid user/password. please try again.")


@app.route("/logout")
@flask_login.login_required
def logout_page():
    flask_login.logout_user()
    return redirect("/")

@app.route("/main")
@flask_login.login_required
def main_page():
    folderid="0"
    if 'folderid' in request.values:
        folderid = request.values['folderid']
    id="1"
    if 'id' in request.values:
        id = request.values['id']

    user = flask_login.current_user.get_dict()
    
    task_users = database_read(f"select name,email from accounts  order by name;")
    folders = database_read(f"select * from folders order by name;")
    tasks = database_read(f"select * from tasks where folderid= '{folderid}' AND status != 'CLOSE';")
    maintask = database_read(f"select * from tasks where id= '{id}';") #AND userid='{user['userid']}'

    closedtasks = database_read(f"select * from tasks where status = 'CLOSE';")
    tasksfiles = database_read(f"select * from tasksfiles where id= '{id}';")
    TaskNotes = database_read(f"select * from TasksNotes where id= '{id}';")
    TaskCategories = database_read(f"select * from categories;")
    if len(maintask) == 1:
        maintask = maintask[0]
    else:
        maintask={}
    return render_template('main.html',user=user,folders=folders,tasks=tasks,maintask=maintask,folderid=folderid,id=id,task_users=task_users,tasksfiles=tasksfiles,TaskNotes=TaskNotes,TaskCategories=TaskCategories,closedtasks=closedtasks)

@app.route("/save_task", methods=['POST'])
@flask_login.login_required
def task_update():
    user = flask_login.current_user.get_dict()
    form = dict(request.values)
    id = form['id']
    folderid = form['folderid']
    session['formData'] = form
    change_in_task=""
    if 'submit-close' in form:
        form['status']= 'CLOSE'  #status open or close
        change_in_task= "Task was Closed"
        #Log
        logger.info(f"Task '{id}' has been closed by: {user['userid']} date: {str(datetime.now())}")
        #sendmail
        ok = send_notification(change_in_task) 
    if 'submit-reopen' in form:
        form['status']= 'OPEN'  #status open or close
        change_in_task= "Task was Reopened"
        #Log
        logger.info(f"Task '{id}' has been Reopened by: {user['userid']} date: {str(datetime.now())}")
        #sendmail
        ok = send_notification(change_in_task)         
    if 'submit-delete' in form:
        database_write(f"delete from tasks where id='{id}';")
        change_in_task= "Task was Deleted"
        #Log
        logger.info(f"Task '{id}' has been delete by: {user['userid']} date: {str(datetime.now())}")
        #mail
        ok = send_notification(change_in_task) 
        return redirect(f"/main?folderid={folderid}")
    if id == "": #new TASK
        id = str(uuid.uuid1())
        form['id'] = id
        form['status'] = 'OPEN'
        form['created'] = datetime.now().strftime("%Y-%m-%d")
        sql = """insert into tasks 
        (userid,folderid,id,title,due,reminder,created,category,priority,status,desc,assignto) values 
        (:userid,:folderid,:id,:title,:due,:reminder,:created,:category,:priority,:status,:desc,:assignto);"""
        ok = database_write(sql,form)
        if ok == 1:
            return redirect(f"/main?folderid={folderid}&id{id}") 
        else:
            return redirect(f"/error?folderid={folderid}&id{id}")         
    else: #existing task Noraml Update
        maintask = database_read(f"select * from tasks where id= '{id}' ;")  #AND userid='{user['userid']}'          
        sql = "UPDATE tasks SET title =:title, due =:due, reminder =:reminder, category =:category, priority =:priority, status=:status, desc =:desc, assignto =:assignto where id =:id"
        ok = database_write(sql,form)
        if ok == 1:
           ## SEND Notification mail'##
           if maintask[0].get('assignto') != form.get('assignto'):
             #Log
            logger.info(f"Task : '{form['id']}' is now assinged to: {form.get('assignto')}  by: {user['userid']} date: {str(datetime.now())}")
            #send Email
            session['formData'] = form
            assinged_notif = f"Task : '{form['id']}' was now assinged to: {form.get('assignto')}  by: {user['userid']}"
            notif_sent = send_notification(assinged_notif) 
            if notif_sent:
                return redirect(f"/main?folderid={folderid}&id={id}") 
            else:
                return redirect(f"/error?folderid={folderid}&id={id}") 
           else:
            return redirect(f"/main?folderid={folderid}&id={id}") 
        else:
            return redirect(f"/error?folderid={folderid}&id={id}") 
    return "ok"

@app.route("/new-folder", methods=["POST"])
@flask_login.login_required
def create_new_folder():
    form = dict(request.values)
    id = str(uuid.uuid1())
    form['id'] = id
    sql = f"INSERT into folders (userid,id,name) VALUES (:userid,:id,:name);"
    ok = database_write(sql,form)
    if ok == 1:
       return "OK" 
    else:
       return "ERROR"

@app.route('/upload', methods=['POST'])
def upload(): 
        user = flask_login.current_user.get_dict() 
        data=  dict(request.values)
        id = data['id']
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)

        file = request.files['file']

        if file.filename == '':
            flash('No file selected for uploading')
            return redirect(request.url)

        if file :                            
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            create = datetime.now().strftime("%Y-%m-%d")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            sql = f"INSERT into TasksFiles (id,filename,filepath,createdate,userid) VALUES ('{id}','{filename}','{filepath}','{create}','{user['userid']}');"
            ok = database_write(sql,data)
            if ok == 1:
               print('File successfully uploaded')
               return redirect(f"/main?folderid={data['folderid']}&id={id}")            
            else:
               return "ERROR"
        else:
            print('Allowed file types are txt, pdf, png, jpg, jpeg, gif')
            return redirect(request.url)


@app.route("/upload", methods=['GET'])
def upload_page():
    id = request.args.get('id')
    user = flask_login.current_user.get_dict()
    maintask = database_read(f"select * from tasks where id= '{id}';")
    if len(maintask) == 1:
        maintask = maintask[0]
    else:
        maintask={}
    return render_template('upload.html',task=maintask)


@app.route('/delete_file', methods=['POST'])
@flask_login.login_required
def delete_file():
    data=  dict(request.values)
    id = data['id']
    filename =  data['filename']
    sql = f"Delete from TasksFiles where id = '{id}' and filename = '{filename}';"
    ok = database_write(sql,data)
    if ok == 1:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        os.remove(filepath)
        print('File successfully Deleted')
        return redirect(f"/main")             
    else:
        return "ERROR" 

@app.route('/download_file/<path:filename>',methods=['GET',"POST"])
@flask_login.login_required
def download_file(filename):
    user = flask_login.current_user.get_dict()
    data=  dict(request.values)    
    myfile =  database_read(f"select * from TasksFiles where filename= '{filename}';")
    if myfile:
        str_path = myfile[0]['filepath']
        for root, dirs, files in os.walk(app.config['UPLOAD_FOLDER']):
            for name in files:            
                # As we need to get the provided python file, 
                # comparing here like this
                if name == filename:  
                    path = os.path.abspath(os.path.join(root, name))
                    uploads = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])
                    return send_from_directory(uploads, filename)
    else:
         return "Error"

@app.route('/delete_folder', methods=['DELETE'])
@flask_login.login_required
def delete_folder():
    data=  dict(request.values)
    user = flask_login.current_user.get_dict() 
    print(data)
    id = data['folderid']
    sql = f"Delete from folders where id = '{id}';"
    print(sql)
    ok = database_write(sql,data)
    if ok == 1:
        print('project successfully Deleted')
        #Log
        logger.info(f"Project deleted - '{data['foldername']}' has been Sent by: {user['userid']} date: {str(datetime.now())}")
        return "OK"            
    else:
        return "ERROR" 
    
@app.route('/send-mail')
def send_task(notification=''):
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
            'Project': projname,
            'TaskID': form['id'],
            'Date Created': form['created'],
            'note': notification
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
    logger.info(f"New Mail - '{form['id']}' has been Sent by: {user['userid']} date: {str(datetime.now())}")
    return redirect(f"/main?folderid={form['folderid']}&id={form['id']}")

@app.route("/new-note", methods=["POST"])
@flask_login.login_required
def create_new_note():
    user = flask_login.current_user.get_dict() 
    data = dict(request.values)
    folderid = data['folderid']
    create = datetime.now().strftime("%Y-%m-%d")
    id = data['id']
    add_note =  data['note']
    sql = f"INSERT into TasksNotes (id,note,createdate,userid) VALUES ('{id}','{add_note}','{create}','{user['userid']}');"
    ok = database_write(sql,data)
    if ok == 1:
       #Log
       logger.info(f"New Note To Task '{id}' has been Added by: {user['userid']} date: {str(datetime.now())}")
       #mail
       notif_sent = send_notification(add_note) 
       if notif_sent:
            return redirect(f"/main?folderid={folderid}&id={id}") 
       else:
            return redirect(f"/error?folderid={folderid}&id={id}") 
       
       return "ERROR"


@app.route("/mytasks", methods=['GET'])
def mytask_page():
    id = request.args.get('id')
    user = flask_login.current_user.get_dict()
    mytasks = database_read(f"select ts.*,fol.name as foldername from tasks as ts left join folders as fol on ts.folderid = fol.id where assignto= '{user['name']}'")
    closedtasks = database_read(f"select ts.*,fol.name as foldername from tasks as ts left join folders as fol on ts.folderid = fol.id where  status = 'CLOSE';")
    print(closedtasks)
    return render_template('mytasks.html',mytasks=mytasks,closedtasks=closedtasks)

@app.route("/error")
def error_page():
    return "there was an Error"


#dev 
app.run(debug=True)

#production  - remark above
if __name__ == "__main__":
    app.run(host="0.0.0.0", port = 80, debug=True)