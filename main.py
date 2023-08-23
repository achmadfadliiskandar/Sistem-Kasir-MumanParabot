from flask import Flask,render_template,flash,request,url_for,session,redirect,Response
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
from pyzbar.pyzbar import decode
from flask_paginate import Pagination,get_page_args
import MySQLdb.cursors
import re
import qrcode
import os
import cv2
import numpy as nmp
import time

app = Flask(__name__,template_folder='template')
app.config['STATIC_FOLDER'] = 'static'
bycript = Bcrypt(app)

# KONFIGURASI DATABASE
app.secret_key = 'your secret key'
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'parabot'

mysql = MySQL(app)

# HALAMAN LOGIN
@app.route('/')
def login():
    if 'email' in session:
        return redirect(url_for('dasboardadmin'))
    return render_template("/login.html",title="Login")

# BACKEND LOGIN
@app.route('/',methods=['POST'])
def actionlogin():
    if request.method == 'POST' and 'email' in request.form and 'password' in request.form:
        email = request.form['email']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM pengguna WHERE email = %s",(email,))
        pengguna = cursor.fetchone()

        if pengguna and bycript.check_password_hash(pengguna['password'],password) and pengguna['akses'] == "Diizinkan":
            session['id'] = pengguna['id']
            session['email'] = pengguna['email']
            session['username'] = pengguna['username']
            session['sebagai'] = pengguna['sebagai']
            return redirect("/DashboardAdmin")
        elif pengguna and bycript.check_password_hash(pengguna['password'],password) and pengguna['akses'] == "Tidak Diizinkan":
            pesan = "Anda Tidak Diizinkan Masuk Ke Situs Ini Silahkan Hubungi Admin"
        else:
            pesan = "password atau email salah kali"
        return render_template("login.html",pesan=pesan)
    
@app.route('/DashboardAdmin')
def dasboardadmin():
    # start user
    conn = mysql.connection
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(id) FROM pengguna")
    jmlhuser = cursor.fetchone()[0]
    # end user

    # start barcode
    conn = mysql.connection
    cursors = conn.cursor()
    cursors.execute("SELECT COUNT(id) FROM barcodebarang")
    jmlhbarcode = cursors.fetchone()[0]
    # end barcode

    if 'email' in session:
        return render_template("DashboardAdmin/index.html",title="Dashboard Admin",halpage="Dashboard",jmlhuser=jmlhuser,jmlhbarcode=jmlhbarcode)
    else:
        return redirect(url_for('login'))

# LOGOUT ADMIN
@app.route('/logout')
def keluar():
    session.pop('masuk',None)
    session.pop('id',None)
    session.pop('email',None)
    session.pop('username',None)
    return redirect(url_for('login'))

# DATA PENGGUNA/USER/ADMIN
@app.route('/datapengguna')
def semuadatauser():
    conn = mysql.connection
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pengguna WHERE NOT sebagai='Admin'")
    pengguna = cursor.fetchall()
    page, per_page, offset = get_page_args(page_parameter="page", per_page_parameter="per_page")
    page = page or 1
    per_page = per_page or 10
    offset = (page - 1) * per_page

    def getUser(offset=0,per_page=10):
        return pengguna[offset:offset+per_page]
    
    if 'email' in session:
        total = len(pengguna)
        pagination_barcode = getUser(offset=offset, per_page=per_page)
        pagination = Pagination(page=page, per_page=per_page, total=total, css_framework='boostrap4')
        return render_template("DashboardAdmin/datapengguna.html",title="Data Pengguna",halpage="Data Pengguna", pengguna=pagination_barcode, page=page, per_page=per_page, pagination=pagination)
    else:
        return redirect(url_for('login'))

@app.route('/tambahpengguna',methods=['GET','POST'])
def tambahkanpengguna():
    if 'email' in session:
        if request.method == 'GET':
            return render_template("DashboardAdmin/tambahpengguna.html",title="Tambah Pengguna",halpage="Tambah Pengguna")
        if request.method == 'POST':
            username = request.form['username']
            email = request.form['email']
            password = request.form['password']
            akses = request.form['akses']
            sebagai = request.form['sebagai']
            hashingpw = bycript.generate_password_hash(password).decode('utf-8')
            val = (username,email,hashingpw,akses,sebagai)
            conn = mysql.connection
            cursor = conn.cursor()
            sql = "INSERT INTO pengguna (username,email,password,akses,sebagai) VALUES (%s,%s,%s,%s,%s)"
            cursor.execute(sql,val)
            conn.commit()
            flash("Data Berhasil Ditambahkan")
            return redirect(url_for("semuadatauser"))
        else:
            return redirect(url_for('login'))
        
@app.route('/deletepengguna/<int:id>',methods=['POST'])
def hapuspengguna(id):
    if 'email' in session:
        if request.method == "POST":
            conn = mysql.connection
            cursor = conn.cursor()
            cursor.execute("DELETE FROM pengguna WHERE id = %s",(id,))
            conn.commit()
            cursor.close()
            conn.close()
            flash("Data Berhasil Dihapus")
            return redirect(url_for("semuadatauser"))
        else:
            return redirect(url_for('login'))
    
@app.route('/editpengguna/<int:id>',methods=['GET','POST'])
def updatepengguna(id):
    if 'email' in session:
        if request.method == "GET":
            conn = mysql.connection
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pengguna WHERE id = %s",(id,))
            data = cursor.fetchone()
            return render_template("DashboardAdmin/editpengguna.html",data=data,title=f"Edit {data[1]}",halpage=f"Edit {data[1]}")
        if request.method == "POST":
            if session['sebagai'] == 'Admin':
                username = request.form['username']
                email = request.form['email']
                akses = request.form['akses']
                sebagai = request.form['sebagai']
                conn = mysql.connection
                cursor = conn.cursor()
                sql = "UPDATE pengguna SET username=%s, email=%s, akses=%s, sebagai=%s WHERE id=%s"
                val = (username,email,akses,sebagai,id)
                cursor.execute(sql,val)
                conn.commit()
                flash("Data Berhasil Diubah")
                return redirect(url_for("semuadatauser"))
            if session['sebagai'] == "Pedagang":
                username = request.form['username']
                email = request.form['email']
                conn = mysql.connection
                cursor = conn.cursor()
                sql = "UPDATE pengguna SET username=%s, email=%s WHERE id=%s"
                val = (username,email,id)
                cursor.execute(sql,val)
                conn.commit()
                flash("Data Berhasil Diubah")
                return redirect(url_for("semuadatauser"))
        else:
            return redirect(url_for('login'))

#END BAGIAN DASHBOARD
# BAGIAN BARKODE
@app.route("/barcodescanner")
def BarcodeScanner():
    # database start
    conn = mysql.connection
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM barcodebarang")
    barcodeharga = cursor.fetchall()
    # data base end

    # text start
    with open("datakerja.txt", "w") as datakerja:
        for item in barcodeharga:
            datakerja.write(f"{item[1]}\n")
    # text end
    page, per_page, offset = get_page_args(page_parameter="page", per_page_parameter="per_page")
    page = page or 1
    per_page = per_page or 10
    offset = (page - 1) * per_page

    def get_barcodes(offset=0,per_page=10):
        return barcodeharga[offset:offset+per_page]

    if 'email' in session:
        total = len(barcodeharga)
        pagination_barcode = get_barcodes(offset=offset, per_page=per_page)
        pagination = Pagination(page=page, per_page=per_page, total=total, css_framework='boostrap4')
        return render_template("BarcodeScanner/index.html", title="Data Barcode", halpage="Data Barcode", barcodeharga=pagination_barcode, page=page, per_page=per_page, pagination=pagination)
    else:
        return redirect(url_for('login'))
    
@app.route("/tambahbarcode")
def AddBarcode():
    if 'email' in session:
        return render_template("BarcodeScanner/tambahbarcode.html",title="Tambah Barcode",halpage="Tambah Barcode")
    else:
        return redirect(url_for('login'))
    
@app.route("/StoreBarcode",methods=['POST'])
def StoreBarcode():
    if 'email' in session:
        # mendata input manual dari html
        harga = request.form['harga']
        jumlah = 1
        # end mendata input manual dari html
        # bagian pengolah gambar
        data = harga
        output_dir = (r"C:\Users\X260\Desktop\python\belajarguipy\ScannerParabot\static\tempatbarcode")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        gambar = qrcode.make(data)
        img_path = os.path.join(output_dir,f'barcodeharga-{data}.png')
        gambar.save(img_path)
        # end bagian pengolah gambar

        # bagian text
        teks = "Harga : {}\nJumlah : {}\nbarcodeharga-{}.png".format(harga,jumlah,data)
        fileteks = open("datakerja.txt","a")
        fileteks.write(teks)
        fileteks.close()
        # end bagian txt

        # bagian masukin ke database
        conn = mysql.connection
        cursor = conn.cursor()
        sql = "INSERT INTO barcodebarang (harga,jumlah,gambarbarcode) VALUES (%s,%s,%s)"
        val = (harga,jumlah,f'barcodeharga-{data}.png')
        cursor.execute(sql,val)
        conn.commit()
        flash("Data Berhasil Ditambahkan")
        return redirect(url_for("BarcodeScanner"))
        # end bagian masukin ke database
    else:
        return redirect(url_for('login'))
    

# halaman kerja

@app.route('/halamankerja')
def PageWork():
        perhitungan = open("penghitungan.txt", "r")
        # bagian menjumlahkan(sum) start
        total = 0
        with open("penghitungan.txt", "r") as f:
            for line in f:
                total += int(line)
        # bagian menjumlahkan(sum) end
        if 'email' in session:
            return render_template("HalamanKerja/index.html",title="Halaman Kerja",halpage="Halaman Kerja",perhitungan=perhitungan.readlines(),total=total)
        else:
            return redirect(url_for('login'))

@app.route('/clearcart',methods=['POST'])
def ClearCart():
    file = open("penghitungan.txt","r+")
    file.truncate(0)
    file.close()
    return redirect(url_for('PageWork'))
        

def frames():
    # bagian vidio dan proses scanner
    capture = cv2.VideoCapture(0)
    mydata = ""  
    frame = None
    terakhirscan = 0
    waktuscan = 1

    # bagian txt start
    with open('datakerja.txt') as f:
        isidata = f.read()
    # bagian txt end

    while True:
        success, frame = capture.read()
        if not success:
            break
        else:
            for barcode in decode(frame):
                current_time = time.time()
                if current_time - terakhirscan >= waktuscan:
                    scanned_data  = barcode.data.decode('utf-8')
                    if scanned_data in isidata:
                        output = 'Ada'
                        warna = (0,255,0)
                        teks = teks = scanned_data + '\n'
                        # konfigurasi file start
                        file = open("penghitungan.txt","a")
                        file.write(teks)
                        file.close()
                        # konfigurasi file end
                    else:
                        output = 'tidak ada'
                        warna = (0,0,255)
                    posisi = nmp.array([barcode.polygon], nmp.int32)
                    posisi = posisi.reshape((-1, 1, 2))
                    cv2.polylines(frame, [posisi], True, warna, 5)
                    positioning = barcode.rect
                    cv2.putText(frame, output, (positioning[0], positioning[1]),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 255), 2)
                terakhirscan = current_time

        if frame is not None:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        # end proses dan bagian vidio

# adding vidio to html use js
@app.route('/rekamankerja')
def rekamankerja():
    return Response(frames(),mimetype='multipart/x-mixed-replace; boundary=frame')

# OPERATOR APLIKASI JANGAN DIGGANGGU
if __name__ == '__main__':
    app.run(debug=True)