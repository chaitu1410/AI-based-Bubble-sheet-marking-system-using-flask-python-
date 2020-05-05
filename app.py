from flask import Flask, render_template, request, redirect
import os
import shutil
from werkzeug.utils import secure_filename
from flask_uploads import configure_uploads,UploadSet, IMAGES, patch_request_class
from werkzeug.utils import secure_filename
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import SubmitField
from datetime import date

from imutils.perspective import four_point_transform
from imutils import contours
import numpy as np
import matplotlib.pyplot as plt
import imutils
import cv2
from PIL import ImageTk,Image

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = '3d8a5396c38b36e0418efc560c257806'
app.config['UPLOADED_PHOTOS_DEST'] = os.path.join(basedir, 'uploads')


photos = UploadSet('photos', IMAGES)
configure_uploads(app, photos)
patch_request_class(app)  # set maximum file size, default is 16MB
path=""

class UploadForm(FlaskForm):
    photo = FileField(validators=[FileAllowed(photos, 'Image only!'), FileRequired('File was empty!')])
    submit = SubmitField('Upload')

@app.route('/home',methods=['GET', 'POST'])
def home():
    global path
    form = UploadForm()
    if request.method == "POST":
        result = {}
        students = []
        key = {}
        A = 0
        B = 0
        C = 0
        FAIL = 0
        test=request.form.get('testname')
        # arr = request.form.get('k')
        # print(arr)
        # key[0] = int(arr[0])+1
        # key[1] = int(arr[1])+1
        # key[2] = int(arr[2])+1
        # key[3] = int(arr[3])+1
        # key[4] = int(arr[4])+1
        key[0] = int(request.form.get('k1'))-1
        key[1] = int(request.form.get('k2'))-1
        key[2] = int(request.form.get('k3'))-1
        key[3] = int(request.form.get('k4'))-1
        key[4] = int(request.form.get('k5'))-1
        files = request.files.getlist("file[]")
        #filename = photos.save(form.photo.data)
        #filename = photos.save(request.file('file'))
        #file_url = photos.url(filename)
        path = os.path.join(app.config['UPLOADED_PHOTOS_DEST'], test)
        if not os.path.exists(path):
            os.mkdir(path)
        else:
            shutil.rmtree(path)
            os.mkdir(path)
        if not os.path.exists(path+"\\"+test):
            os.mkdir(path+"\\"+test)
        else:
            shutil.rmtree(path+"\\"+test)
            os.mkdir(path+"\\"+test)

        _files = request.files.getlist("file[]")
        for file in _files:
            file.save(path+"\\"+file.filename)

        files_list = os.listdir(path)

        for file in files_list:
            splited = file.split('.')
            rno = splited[0]
            if len(splited)>1:
                score = img_proc(path,file,test,key)
                result[rno] = score
                if score>3:
                    A+=1
                elif score>2:
                    B+=1
                elif score>1:
                    C+=1
                else:
                    FAIL+=1

                students.append(rno)
        #if not os.path.exists(path):
        #    shutil.rmtree(path)
        #score = img_proc(path+'\\'+filename)
        return render_template('result.html',students=students,result=result,A=A,B=B,C=C,FAIL=FAIL,test=test,date=date.today())

    return render_template('home.html',form=form)

def img_proc(path,file,folder,key):
    ANSWER_KEY = key
    image = cv2.imread(path+"\\"+file)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 75, 200)

    cnts = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE)
    cnts = imutils.grab_contours(cnts)
    docCnt = None

    if len(cnts) > 0:
        cnts = sorted(cnts, key=cv2.contourArea, reverse=True)
        for c in cnts:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)

            # if our approximated contour has four points,
            # then we can assume we have found the paper
            if len(approx) == 4:
                docCnt = approx
                break
    paper = four_point_transform(image, docCnt.reshape(4, 2))
    warped = four_point_transform(gray, docCnt.reshape(4, 2))

    thresh = cv2.threshold(warped, 0, 255,
        cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]

    cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE)
    cnts = imutils.grab_contours(cnts)
    questionCnts = []

    for c in cnts:
        (x, y, w, h) = cv2.boundingRect(c)
        ar = w / float(h)

        if w >= 20 and h >= 20 and ar >= 0.9 and ar <= 1.1:
            questionCnts.append(c)

    questionCnts = contours.sort_contours(questionCnts,method="top-to-bottom")[0]
    correct = 0

    for (q, i) in enumerate(np.arange(0, len(questionCnts), 5)):
        cnts = contours.sort_contours(questionCnts[i:i + 5])[0]
        bubbled = None

        for (j, c) in enumerate(cnts):
            mask = np.zeros(thresh.shape, dtype="uint8")
            cv2.drawContours(mask, [c], -1, 255, -1)
            mask = cv2.bitwise_and(thresh, thresh, mask=mask)
            total = cv2.countNonZero(mask)
            if bubbled is None or total > bubbled[0]:
                bubbled = (total, j)
        color = (0, 0, 255)
        k = ANSWER_KEY[q]

        if k == bubbled[1]:
            color = (0, 255, 0)
            correct += 1
        cv2.drawContours(paper, [cnts[k]], -1, color, 3)

    score = correct
    cv2.imwrite(path+"\\"+folder+"\\"+file, paper)
    return score

@app.route('/',methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        uname=request.form.get("username")
        pwd=request.form.get("pass")
        if uname == "admin" and pwd == "admin123":
           return redirect('http://localhost:5000/home')

    return render_template('login.html')

if __name__ == '__main__':
    app.run(debug=True)
