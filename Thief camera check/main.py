#
# цель:
# поиск движения в камере.
#
# чужие библиотеки:
# OpenCV, PyQt5, PIL
#
# Весь код в классе окна Wind. Точка входа внизу.
#


import os
import sys
import time
import cv2
import ctypes
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QLineEdit
from PyQt5.QtGui import QIcon, QPixmap, QImage
from PyQt5.QtCore import Qt, QTimer
from PIL import Image, ImageDraw, ImageFont


class Wind(QMainWindow):
    # label_danger, label_last, label_time, label_cam, label_map, button_paint, textbox, timer
    def __init__(self):
        super().__init__()
        self.setGeometry(300, 300, 300, 220)
        self.setWindowTitle('police thief')
        self.setWindowIcon(QIcon('icon.png'))

        self.label_danger = QLabel(self)
        self.label_danger.setText('start initial ---')
        self.label_danger.move(5, 5)
        self.label_danger.adjustSize()

        self.label_last = QLabel(self)
        self.label_last.setText('start initial -----------------------------')
        self.label_last.move(5, 20)
        self.label_last.adjustSize()

        self.label_time = QLabel(self)
        self.label_time.setText('start initial ---')
        self.label_time.move(5, 35)
        self.label_time.adjustSize()

        self.label_cam = QLabel(self)
        self.label_cam.move(5, 50)
        self.label_cam.setPixmap(QPixmap('icon.png').scaled(100, 100, Qt.KeepAspectRatio, Qt.FastTransformation))
        self.label_cam.adjustSize()

        self.button_delete = QPushButton(self)
        self.button_delete.setText('delete')
        self.button_delete.adjustSize()
        self.button_delete.move(5, 160)
        self.button_delete.clicked.connect(self.delete)

        self.label_map = QLabel(self)
        self.label_map.move(120, 40)
        self.label_map.setPixmap(QPixmap('map.png'))
        self.label_map.adjustSize()

        self.button_paint = QPushButton(self)
        self.button_paint.setText('paint')
        self.button_paint.adjustSize()
        self.button_paint.move(5, 250)
        self.button_paint.clicked.connect(self.paintMap)

        self.textbox = QLineEdit(self)
        self.textbox.move(5, 290)
        self.textbox.setText('43200 0 100 10')
        self.textbox.resize(100, 30)

        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.tic)

        self.hid()
        self.generateMap(43200, 0, 100, 10)
        self.label_map.setPixmap(QPixmap('map.png'))
        self.show()
        self.tick = 0  # итерация в цикле, для увеличения шага "if tick % 10 == 0"
        self.danger = 0  # опасность в кадре, 0-1000
        self.can_save = 0  # ограничивает количество сохранений
        self.cap = self.getCapture()
        _, frame = self.cap.read()
        time.sleep(1)
        _, frame = self.cap.read()
        self.global_avg_frame = frame
        self.local_avg_frame = frame
        self.paintCam(frame)
        self.timer.start()

    def paintCam(self, img):
        # img -> label_cam
        qimage = QImage(img.data, 320, 240, QImage.Format.Format_BGR888)
        qpixmap = QPixmap.fromImage(qimage)
        qpixmap2 = qpixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.FastTransformation)
        self.label_cam.setPixmap(qpixmap2)

    def paintMap(self):
        # вызывает button_paint, переделывает map
        arr = self.textbox.text().split(' ')
        self.generateMap(int(arr[0]), int(arr[1]), int(arr[2]), int(arr[3]))
        self.label_map.setPixmap(QPixmap('map.png'))

    def delete(self):
        # вызывает button_delete, удаляет все фотки
        for photo in os.listdir('fold'):
            os.remove('fold\\' + photo)

    def tic(self):
        # вызывает timer
        self.tick += 1

        _, frame = self.cap.read()

        if self.tick % 10 == 0:
            self.global_avg_frame = self.mix(self.global_avg_frame, frame, 0.08)
        self.local_avg_frame = self.mix(self.local_avg_frame, frame, 0.4)

        dif = self.diff(self.global_avg_frame, self.local_avg_frame)
        gra = self.gray(dif)
        blu = self.blur(gra)
        thr = self.threshold(blu)
        dil = self.dilate(thr)

        contours = self.findContours(dil)
        for contour in contours:
            (x, y, w, h) = cv2.boundingRect(contour)
            area = cv2.contourArea(contour)
            if area < 80:
                continue
            self.drawRect(frame, x, y, w, h)
            self.danger += 1 + area * 0.002

        self.danger -= 3
        self.danger *= 0.94
        if self.danger > 1000:
            self.danger = 1000
        if self.danger < 0:
            self.danger = 0

        if (self.can_save == 0) & (self.danger > 20):
            cv2.imwrite('fold\\' + str(datetime.now().day).zfill(2) + str(datetime.now().hour).zfill(2) + str(datetime.now().minute).zfill(2) + str(datetime.now().second).zfill(2) + '.png', frame)
            self.can_save = 50
            self.label_last.setText(
                'save ' + 'fold\\' + str(datetime.now().day).zfill(2) + str(datetime.now().hour).zfill(2) + str(datetime.now().minute).zfill(2) + str(datetime.now().second).zfill(2) + '.png')
        self.can_save -= 1
        if self.can_save < 0:
            self.can_save = 0

        if self.danger > 900:
            self.timer.setInterval(0)
        elif self.danger > 200:
            self.timer.setInterval(10)
        elif self.danger > 15:
            self.timer.setInterval(50)
        elif self.danger > 1:
            self.timer.setInterval(100)
        else:
            self.timer.setInterval(300)

        self.label_danger.setText(str(self.danger))
        self.label_time.setText(str(datetime.now().time()))
        if (self.tick % 10 == 0) or (self.danger > 1):
            self.paintCam(frame)

    def generateMap(self, lastsec_left, lastsec_right, wid, lvls):
        # sec_last_left давний порог  sec_last_right недавний порог

        canvas = Image.new('RGB', (1700, 900), (0, 0, 0))

        date_now = str(datetime.now().day).zfill(2) + str(datetime.now().hour).zfill(2) + str(datetime.now().minute).zfill(2) + str(datetime.now().second).zfill(2)
        datesec_now = int(date_now[0:2]) * 86400 + int(date_now[2:4]) * 3600 + int(date_now[4:6]) * 60 + int(date_now[6:8])

        photos_all = os.listdir('fold')

        photos_include = []
        for photo in photos_all:
            datasec_file = int(photo[0:2]) * 86400 + int(photo[2:4]) * 3600 + int(photo[4:6]) * 60 + int(photo[6:8])
            lastsec_photo = datesec_now - datasec_file
            if (lastsec_photo < lastsec_left) and (lastsec_photo > lastsec_right):
                photos_include.append(photo)

        busy = [-1 for i in range(lvls)]

        for photo in photos_include:
            datasec_file = int(photo[0:2]) * 86400 + int(photo[2:4]) * 3600 + int(photo[4:6]) * 60 + int(photo[6:8])
            lastsec_photo = datesec_now - datasec_file
            with Image.open('fold\\' + photo) as im:
                im.load()
            on_timeline = int((lastsec_left - lastsec_photo) / (lastsec_left - lastsec_right) * 1700)
            level = next(filter(lambda lvl: busy[lvl] < on_timeline, range(0, len(busy))))
            if level != lvls - 1: # последняя линия всегда свободна
                busy[level] = on_timeline + wid
            height = int(900 / lvls)
            canvas.paste(im.resize((wid, height)), (on_timeline, level * height))

        draw = ImageDraw.Draw(canvas)
        sec_current_hour = int(date_now[4:6]) * 60 + int(date_now[6:8])
        for lastsec in range(lastsec_right, lastsec_left):
            if (lastsec - sec_current_hour) % 3600 == 0:
                on_timlin = int((lastsec_left - lastsec) / (lastsec_left - lastsec_right) * 1700)
                draw.line((on_timlin, 900, on_timlin, 880), fill='Gray', width=2)
                draw.text((on_timlin, 880), str(int((datesec_now - lastsec) / 3600) % 24), font=ImageFont.truetype('myarial.ttf', 15))
        canvas.save('map.png')

    def hid(self):
        kernel32 = ctypes.WinDLL('kernel32')
        user32 = ctypes.WinDLL('user32')
        SW_HIDE = 0
        hwnd = kernel32.GetConsoleWindow()
        if hwnd:
            user32.ShowWindow(hwnd, SW_HIDE)

    def getCapture(self):
        cap = cv2.VideoCapture(0)
        cap.set(3, 320)
        cap.set(4, 240)
        return cap

    def mix(self, img1, img2, wei):
        return cv2.addWeighted(img1, 1 - wei, img2, wei, 0)

    def diff(self, img1, img2):
        return cv2.absdiff(img1, img2)

    def gray(self, img):
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    def blur(self, img):
        return cv2.GaussianBlur(img, (5, 5), 0)

    def threshold(self, img):
        _, thresh = cv2.threshold(img, 20, 255, cv2.THRESH_BINARY)  # x > 20 ? 255 : 0
        return thresh

    def dilate(self, img):
        return cv2.dilate(img, None, iterations=3)  # kernel=None

    def findContours(self, img):
        contours, _ = cv2.findContours(img, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        return contours

    def drawRect(self, img, x, y, w, h):
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    wi = Wind()
    sys.exit(app.exec_())
