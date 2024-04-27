import string
from PyPDF2 import PdfReader
from io import BytesIO
import nltk
from flask import Flask, render_template, redirect, url_for, session, flash, request, jsonify
from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, ValidationError
import bcrypt
from flask_mysqldb import MySQL

app = Flask(__name__)

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'sdpdb'
app.secret_key = 'very_secret'
mysql1 = MySQL(app)


class SignupForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Signup")

    def validate_email(self, field):
        cursor = mysql1.connection.cursor()
        cursor.execute("SELECT * FROM users where email=%s", (field.data,))
        user = cursor.fetchone()
        cursor.close()
        if user:
            raise ValidationError('Email Already Taken')


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")

class PDFUploadForm(FlaskForm):
    file = FileField()
    submit = SubmitField("Submit")


@app.route('/')
def index():
    form = LoginForm()
    return render_template('login.html', form=form)


@app.route('/pdfupload', methods=["GET", "POST"])
def pdfupload():
    form = PDFUploadForm()
    if request.method == "POST":
        if form.validate_on_submit():
            file = form.file.data
            if file:
                file_content = file.stream.read()
                file_name = file.filename

                user_id = session.get('user_id')

                cursor = mysql1.connection.cursor()
                cursor.execute("INSERT INTO pdfs (user_id, fname, fcontent) VALUES (%s, %s, %s)", (user_id, file_name, file_content))
                mysql1.connection.commit()
                cursor.close()

                flash('File uploaded successfully.')
                return redirect(url_for('userpdfs'))

            flash('No file selected.')
        else:
            flash('Invalid form submission. Please try again.')

    return render_template('pdfupload.html', form=form)


@app.route('/userpdfs', methods=['GET', 'POST'])
def userpdfs():
    user_id = session.get('user_id')

    if request.method == 'POST':
        user_question = request.form['question']
        response_text = search_pdf_content(user_question, user_id)
        return jsonify(response_text)

    return render_template('home.html')


def search_pdf_content(user_query, user_id):
    cursor = mysql1.connection.cursor()
    cursor.execute("SELECT * FROM pdfs WHERE user_id = %s ORDER BY pid DESC LIMIT 1", (user_id,))
    last_pdf = cursor.fetchone()
    cursor.close()

    byte_stream = BytesIO(last_pdf[3])
    pdf_reader = PdfReader(byte_stream)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()

    raw_doc = text.lower()

    sentence_tokens = nltk.sent_tokenize(raw_doc)
    word_tokens = nltk.word_tokenize(raw_doc)

    lemmatizer = nltk.stem.WordNetLemmatizer()

    def LemTokens(tokens):
        return [lemmatizer.lemmatize(token) for token in tokens]

    remove_punc_dict = dict((ord(punct), None) for punct in string.punctuation)

    def LemNormalize(text):
        return LemTokens(nltk.word_tokenize(text.lower().translate(remove_punc_dict)))

    def response(user_response):
        robo1_response = ''
        TfidVec = TfidfVectorizer(tokenizer=LemNormalize, stop_words='english')
        tfidf = TfidVec.fit_transform(sentence_tokens + [user_response])
        vals = cosine_similarity(tfidf[-1], tfidf)
        idx = vals.argsort()[0][-2]
        flat = vals.flatten()
        flat.sort()
        req_tfidf = flat[-2]
        if req_tfidf == 0:
            robo1_response = robo1_response + "I am sorry. Unable to understand you!"
            return robo1_response
        else:
            robo1_response = robo1_response + sentence_tokens[idx]
            return robo1_response

    response_text = response(user_query)
    return response_text


@app.route('/pdfcontent')
def pdf_content():
    user_id = session.get('user_id')

    cursor = mysql1.connection.cursor()
    cursor.execute("SELECT * FROM pdfs WHERE user_id = %s ORDER BY pid DESC LIMIT 1", (user_id,))
    last_pdf = cursor.fetchone()
    cursor.close()

    byte_stream = BytesIO(last_pdf[3])
    pdf_reader = PdfReader(byte_stream)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()

    return text


@app.route('/signup', methods=['GET', 'POST'])
def register():
    form = SignupForm()
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data
        password = form.password.data

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        cursor = mysql1.connection.cursor()
        cursor.execute("INSERT INTO users (name,email,password) VALUES (%s,%s,%s)", (name, email, hashed_password))
        mysql1.connection.commit()
        cursor.close()

        return redirect(url_for('login'))

    return render_template('signup.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        cursor = mysql1.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        cursor.close()
        if user and bcrypt.checkpw(password.encode('utf-8'), user[3].encode('utf-8')):
            session['user_id'] = user[0]
            return redirect(url_for('pdfupload'))
        else:
            flash("Login failed. Please check your email and password")
            return redirect(url_for('login'))

    return render_template('login.html', form=form)


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("You have been logged out successfully.")
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
