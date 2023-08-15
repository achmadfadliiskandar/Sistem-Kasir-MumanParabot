import cv2
from pyzbar.pyzbar import decode
import numpy as nmp
import mysql.connector

# Konfigurasi mysql
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    passwd="",
    database="parabot"
)

cursor = conn.cursor()

capture = cv2.VideoCapture(0)
capture.set(3, 600)
capture.set(4, 500)

while True:
    success, img = capture.read()

    for barcode in decode(img):
        mydata = barcode.data.decode('utf-8')
        print(mydata)
        
        # Eksekusi SQL untuk memeriksa keberadaan data di database
        sql = "SELECT * FROM barcodebarang WHERE harga = %s"
        cursor.execute(sql, (mydata,))
        result = cursor.fetchone()
        
        if result:
            print("Ada")
        else:
            print("Tidak Ada")
            
        posisi = nmp.array([barcode.polygon], nmp.int32)
        posisi = posisi.reshape((-1, 1, 2))
        cv2.polylines(img, [posisi], True, (255, 0, 255), 5)
        positioning = barcode.rect
        cv2.putText(img, mydata, (positioning[0], positioning[1]), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 255), 2)

    cv2.imshow('Result', img)
    cv2.waitKey(1)
