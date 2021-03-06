import cv2
import sys
import pdb
import time
import EyeIsolation
import ClosedEyeDetection
import SpraySystem
from PyQt5.QtWidgets import  QWidget, QLabel, QApplication
from PyQt5.QtCore import QThread, Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QImage, QPixmap

cap = cv2.VideoCapture(0)

class Thread(QThread):
    changePixmapMainCamera = pyqtSignal(QImage)
    changePixmapEye1 = pyqtSignal(QImage)
    changePixmapEye2 = pyqtSignal(QImage)
    changeTextEyeStatus = pyqtSignal(str)

    def convertToQT(self, image):
        height, width = image.shape
        #bytesPerLine = width
        ConvertToQTImage = QImage(image.data.tobytes(), width, height, width,QImage.Format_Grayscale8)
        scaled = ConvertToQTImage.scaled(width, height, Qt.KeepAspectRatio)
        return scaled
    
    def run(self):
        startTimer = False
        eyesClosed = True
        model = ClosedEyeDetection.create_model()
        while True:
            ret, frame = cap.read()
            if ret:
                grayImage = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                eyeImages =  EyeIsolation.isolateEye(grayImage)
                eyesQT = []
                for eye in eyeImages:
                    eyesQT.append(self.convertToQT(eye))
                mainCamera = self.convertToQT(grayImage)
                self.changePixmapMainCamera.emit(mainCamera)
                if (len(eyesQT)>0):
                    self.changePixmapEye1.emit(eyesQT[0])
                if (len(eyesQT)>1):
                    self.changePixmapEye2.emit(eyesQT[1])
                    tooFar = False
                    for i, eyeImage in enumerate(eyeImages):
                        if(eyeImage.shape <= (70,70)):
                            print("Too far !!!!")
                            tooFar = True
                        else: 
                            eyeImages[i] = ClosedEyeDetection.crop_center(eyeImages[i], 70, 70)
                            eyeImages[i] = eyeImages[i] / 255.0
                    if(not tooFar):
                        eyesClosed = ClosedEyeDetection.eyeClosed(model, eyeImages)
                        if (ClosedEyeDetection.eyeClosed(model, eyeImages) == True and startTimer == False):
                            self.changeTextEyeStatus.emit('Eyes Closed')
                            initTime = time.perf_counter()
                            startTimer = True
                        elif (ClosedEyeDetection.eyeClosed(model, eyeImages) == True and startTimer == True):
                            timePassed = time.perf_counter() - initTime
                            self.changeTextEyeStatus.emit('Eyes Closed')
                            if (timePassed > 5):
                                SpraySystem.spray()
                                startTimer = False
                        elif (ClosedEyeDetection.eyeClosed(model, eyeImages) == False):
                            self.changeTextEyeStatus.emit('Eyes Opened')
                            startTimer = False

class App(QWidget):
    def __init__(self):
        super().__init__()
        self.title = 'Driver Alert System'
        self.left = 100
        self.top = 100
        self.width = 640
        self.height = 480
        self.initUI()

    @pyqtSlot(QImage)
    def setMainCameraImage(self, image):
        self.MainCamera.setPixmap(QPixmap.fromImage(image))
    
    @pyqtSlot(QImage)
    def setEye1Image(self, image):
        self.Eye1.setPixmap(QPixmap.fromImage(image))

    @pyqtSlot(QImage)
    def setEye2Image(self, image):
        self.Eye2.setPixmap(QPixmap.fromImage(image))

    @pyqtSlot(str)
    def setEyeStatusLabel(self, status):
        self.EyeStatus.setText(status)

    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
        self.resize(1800, 1200)
        # create a label

        self.EyeStatus = QLabel(self)
        self.EyeStatus.move(1000, 300)

        self.MainCamera = QLabel(self)
        self.MainCamera.move(100, 120)

        self.Eye1 = QLabel(self)
        self.Eye1.move(1000, 120)

        self.Eye2 = QLabel(self)
        self.Eye2.move(1000, 220)

        self.MainCamera.resize(640, 480)
        self.Eye1.resize(100, 100)
        self.Eye2.resize(100, 100)
        self.EyeStatus.resize(100,100)

        th = Thread(self)
        th.changePixmapMainCamera.connect(self.setMainCameraImage)
        th.changePixmapEye1.connect(self.setEye1Image)
        th.changePixmapEye2.connect(self.setEye2Image)
        th.changeTextEyeStatus.connect(self.setEyeStatusLabel)
        th.start()
        self.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    ex.show()
    sys.exit(app.exec_())
    cap.release()
    cv2.destroyAllWindows()