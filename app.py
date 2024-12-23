# python -m venv venv   Creates a new Virtual env
# .\venv\Scripts\activate      This activates a new virtual environment  
# pip install -r requirements.txt
# python app.py   this runs the file  or you click on play button in VS-Code UI

from flask import Flask, render_template, request, session, redirect
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import numpy as np
from werkzeug.datastructures import FileStorage
from flask_mail import Mail
import json
import os
import math
from datetime import datetime
import markdown
import warnings
import pickle
import pandas as pd
import sklearn

warnings.filterwarnings("ignore")

with open('config.json', 'r') as c:
    params = json.load(c)["params"]

local_server = False

app = Flask(__name__)
app.secret_key = "super-secret-key"
app.config["UPLOAD_FOLDER"] = params["upload_location"]
app.config.update(
    MAIL_SERVER = 'smtp.gmail.com',
    MAIL_PORT = '465',
    MAIL_USE_SSL = True,
    MAIL_USERNAME = params['gmail-user'],
    MAIL_PASSWORD=  params['gmail-password']
)

mail = Mail(app)


if(local_server):
    app.config['SQLALCHEMY_DATABASE_URI'] = params['local_uri']
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = params['prod_uri']

db = SQLAlchemy(app)

class Contacts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    phone_num = db.Column(db.String(12), nullable=False)
    msg = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(12), nullable=True)
    email = db.Column(db.String(20), nullable=False)

class Posts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    slug = db.Column(db.String(21), nullable=False)
    content = db.Column(db.String(120), nullable=False)
    tagline = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(12), nullable=True)
    img_file = db.Column(db.String(12), nullable=True)

@app.route("/")
def home():
    posts = Posts.query.filter_by().all()
    last = math.ceil(len(posts)/int(params['no_of_posts']))
    #[0: params['no_of_posts']]
    #posts = posts[]
    page = request.args.get('page')
    if(not str(page).isnumeric()):
        page = 1
    page= int(page)
    posts = posts[(page-1)*int(params['no_of_posts']): (page-1)*int(params['no_of_posts'])+ int(params['no_of_posts'])]
    #Pagination Logic
    #First
    if (page==1):
        prev = "#"
        next = "/?page="+ str(page+1)
    elif(page==last):
        prev = "/?page=" + str(page - 1)
        next = "#"
    else:
        prev = "/?page=" + str(page - 1)
        next = "/?page=" + str(page + 1)

    return render_template('index.html', params=params, posts=posts, prev=prev, next=next)

@app.route("/post/<string:post_slug>", methods=['GET'])
def post_route(post_slug):
    post = Posts.query.filter_by(slug=post_slug).first()
    post.content=markdown.markdown(post.content)

    # print(post_conv)
    return render_template('post.html', params=params, post=post)

@app.route("/about")
def about():
    return render_template('about.html', params=params)

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if ("user" in session and session['user']==params['admin_user']):
        posts = Posts.query.all()
        return render_template("dashboard.html", params=params, posts=posts)

    if request.method == "POST":
        username = request.form.get("uname")
        userpass = request.form.get("pass")
        if username == params['admin_user'] and userpass == params['admin_password']:
            # set the session variable
            session['user']=username
            posts = Posts.query.all()
            return render_template("dashboard.html", params=params, posts=posts)
    else:
        return render_template("login.html", params=params)

@app.route("/edit/<string:sno>", methods = ['GET', 'POST'])
def edit(sno):
    if ('user' in session and session['user'] == params['admin_user']):
        if request.method == 'POST':
            box_title = request.form.get('title')
            tline = request.form.get('tline')
            slug = request.form.get('slug')
            content = request.form.get('content')
            img_file = request.form.get('img_file')
            date = datetime.now()

            if sno=='0':
                post = Posts(title=box_title, slug=slug, content=content, tagline=tline, img_file=img_file, date=date)
                db.session.add(post)
                db.session.commit()
            else:
                post = Posts.query.filter_by(sno=sno).first()
                post.title = box_title
                post.slug = slug
                post.content = content
                post.tagline = tline
                post.img_file = img_file
                post.date = date
                db.session.commit()
                return redirect('/dashboard')
        post = Posts.query.filter_by(sno=sno).first()
        return render_template('edit.html', params=params, post=post, sno=sno)

@app.route("/uploader", methods = ['GET', 'POST'])
def uploader():
    if ('user' in session and session['user'] == params['admin_user']):
        if (request.method == 'POST'):
            f= request.files['file1']
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f.filename) ))
            return "Uploaded successfully"

@app.route("/logout")
def logout():
    session.pop('user')
    return redirect('/dashboard')

@app.route("/delete/<string:sno>", methods = ['GET', 'POST'])
def delete(sno):
    if ('user' in session and session['user'] == params['admin_user']):
        post = Posts.query.filter_by(sno=sno).first()
        db.session.delete(post)
        db.session.commit()
    return redirect('/dashboard')

@app.route("/contact", methods = ['GET', 'POST'])
def contact():
    if (request.method=='POST'):
        '''Add entry to the database'''
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        message = request.form.get('message')
        entry = Contacts(name=name, phone_num = phone, msg = message, date= datetime.now(),email = email )
        db.session.add(entry)
        db.session.commit()
        mail.send_message('New message from ' + name,
                          sender=email,
                          recipients=[params['gmail-user']],
                          body=message + "\n" + phone
                          )
    return render_template('contact.html',params=params)

@app.route("/ml-models")
def mlmodel():
    return render_template("mlmodels.html", params=params)

# Below code belongs to the News Classification
@app.route("/news")
def news():
    return render_template('news-home.html')

# News Prediction Function
def ValuePredictornews(to_predict_list):
    loaded_model = pickle.load(open("news_classification.pkl", "rb"))
    load_tfidf = pickle.load(open("news_classification_tfidf_vectorizer.pkl", "rb"))

    test_article = to_predict_list.lower()
    test_frame = pd.DataFrame({"Text": [test_article]})
    print(test_frame)

    test_feature = load_tfidf.transform(test_frame.Text).toarray()
    # print("Checking this", test_feature)

    prediction = loaded_model.predict(test_feature)
    id_to_category = {0: "business", 1: "tech", 2: "politics", 3: "sport", 4: "entertainment"}
    pred_category = id_to_category[prediction[0]]

    return pred_category


@app.route('/news-cat', methods=['POST'])
def result():
    if request.method == 'POST':
        to_predict_list = request.form["text"]
        print(to_predict_list)
        result = ValuePredictornews(to_predict_list)

        return render_template("news-cat.html", prediction=f"Model predicts this excerpt belong to {str.upper(result)} category!")


#For income prediction page
@app.route("/income")
def income():
    return render_template("income_index.html")


# prediction function for income
def ValuePredictor_income(to_predict_list):
    to_predict = np.array(to_predict_list).reshape(1, 12)
    loaded_model = pickle.load(open("income_model.pkl", "rb"))
    result = loaded_model.predict(to_predict)
    return result[0]



@app.route('/income_result', methods=['POST'])
def income_result():
    if request.method == 'POST':
        to_predict_list = request.form.to_dict()

        to_predict_list = list(to_predict_list.values())
        print(to_predict_list)
        to_predict_list = list(map(float, to_predict_list))
        print(to_predict_list)

        result = ValuePredictor_income(to_predict_list)

        if int(result) == 1:
            prediction = 'Income is more than 50K'

        else:
            prediction = 'Income is less than 50K'

        return render_template("income_result.html", prediction=prediction)



if __name__ == "__main__":
        app.run(debug=True)
          # app.run(host='0.0.0.0')