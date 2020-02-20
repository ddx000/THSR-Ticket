import sys
sys.path.append(".")

import io
from PIL import Image
from requests.models import Response
import matplotlib.pyplot as plt  # type: ignore
import numpy as np  # type: ignore

from thsr_ticket.remote.http_request import HTTPRequest
from thsr_ticket.model.web.booking_form.booking_form import BookingForm
from thsr_ticket.model.web.booking_form.ticket_num import AdultTicket
from thsr_ticket.model.web.confirm_train import ConfirmTrain
from thsr_ticket.model.web.confirm_ticket import ConfirmTicket
from thsr_ticket.view_model.avail_trains import AvailTrains
from thsr_ticket.view_model.error_feedback import ErrorFeedback
from thsr_ticket.view_model.booking_result import BookingResult
from thsr_ticket.view.web.booking_form_info import BookingFormInfo
from thsr_ticket.view.web.show_avail_trains import ShowAvailTrains
from thsr_ticket.view.web.show_error_msg import ShowErrorMsg
from thsr_ticket.view.web.confirm_ticket_info import ConfirmTicketInfo
from thsr_ticket.view.web.show_booking_result import ShowBookingResult
from thsr_ticket.view.common import history_info
from thsr_ticket.model.db import ParamDB, Record

from PySide2 import QtCore, QtGui, QtWidgets
from PySide2.QtWidgets import QApplication, QLabel, QPushButton,QMainWindow,QFileDialog,QGridLayout,QMessageBox,QTableWidgetItem,QDialog

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

import thsr_ui as ui

"This main_qt.py will replace the original main.py & booking_flow.py"

class MyFigure(FigureCanvas):
    def __init__(self,width=6, height=5, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super(MyFigure,self).__init__(self.fig)
        self.axes = self.fig.add_subplot(111)

class MainWindow(QMainWindow, ui.Ui_MainWindow):
    def __init__(self, parent = None):
        super(MainWindow, self).__init__(parent)
        self.setupUi(self)
        self.statusBar().showMessage('template ')

        self.confirm_train = ConfirmTrain()
        self.client = HTTPRequest()

        self.error_feedback = ErrorFeedback()
        self.show_error_msg = ShowErrorMsg()

        self.b_generate_securecode.clicked.connect(self.show_security_code)
        self.b_send_bookingform.clicked.connect(self.send_booking_form)
        self.b_send_selectedtrain.clicked.connect(self.send_selected_train)

    def send_booking_form(self):
        """step1 送出表單"""
        params = self.get_booking_params()
        res = self.client.submit_booking_form(params)
        self.avail_trains = AvailTrains().parse(res.content)
        self.show_AvailTrains(self.avail_trains)

    def send_selected_train(self):
        #step2 送出選定火車
        sel = self.listWidget_availableTrain.currentRow()
        value = self.avail_trains[sel].form_value  # Selection from UI count from 1
        self.confirm_train.selection = value
        confirm_params = self.confirm_train.get_params()
        result = self.client.submit_train(confirm_params)
        if self.show_error(result.content):
            return result

        #step3 送出既有的身分證字號與電話號碼
        ticket_params = self.get_ticket_params()
        result = self.client.submit_ticket(ticket_params)
        if self.show_error(result.content):
            return result

        #顯示訂位紀錄
        result_model = BookingResult().parse(result.content)
        self.show_bookingresult(result_model)

    def get_booking_params(self):
        """取得UI前端使用者填的自定義參數"""

        # becuase index in combobox start from 0, plus 1
        Start = self.cB_depar_station.currentIndex()+1
        Destination = self.cB_arrive_station.currentIndex()+1
        Depart_date = self.calendarWidget_departure.selectedDate().toPython().strftime("%Y/%m/%d")

        depart_time_lst = ["1201A", "1230A", "600A", "630A", "700A", "730A", "800A", "830A", "900A",
        "930A", "1000A", "1030A", "1100A", "1130A", "1200N", "1230P", "100P", "130P",
        "200P", "230P", "300P", "330P", "400P", "430P", "500P", "530P", "600P",
        "630P", "700P", "730P", "800P", "830P", "900P", "930P", "1000P", "1030P",
        "1100P", "1130P"]
        depart_time = depart_time_lst[self.cB_depar_time.currentIndex()]


        params = {
            "BookingS1Form:hf:0": "",
            "selectStartStation": Start, # 出發站
            "selectDestinationStation": Destination, # 到達站
            "trainCon:trainRadioGroup": 0,
            "seatCon:seatRadioGroup": "radio17",
            "bookingMethod": 0,
            "toTimeInputField": Depart_date, # 去程日期
            "toTimeTable": depart_time, # 選擇時間
            "toTrainIDInputField": 0,
            "backTimeInputField": Depart_date, # todo 可以自訂回程時間
            "backTimeTable": "",
            "backTrainIDInputField": "",
            "ticketPanel:rows:0:ticketAmount": "1F",
            "ticketPanel:rows:1:ticketAmount": "0H",
            "ticketPanel:rows:2:ticketAmount": "0W",
            "ticketPanel:rows:3:ticketAmount": "0E",
            "ticketPanel:rows:4:ticketAmount": "0P",
            "homeCaptcha:securityCode": self.lineEdit_securecode.text() #驗證碼
        }

        return params

    def get_ticket_params(self):
        ticket_params = {
            "BookingS3FormSP:hf:0": "",
            "diffOver": 1,
            "idInputRadio": "radio33",
            "idInputRadio:idNumber": self.lineEdit_ID.text(),
            "eaiPhoneCon:phoneInputRadio": "radio40",
            "eaiPhoneCon:phoneInputRadio:mobilePhone": self.lineEdit_phone.text(),
            "email": "",
            "agree": "on",
            "isGoBackM": "",
            "backHome": ""
        }
        return ticket_params

    def show_security_code(self):
        """獲取驗證碼"""
        #todo 自動影像辨識
        try:
            self.Remove_Plot(self.securecode_img)
        except:
            pass

        resp = self.client.request_booking_page()
        img_resp = self.client.request_security_code_img(resp.content)
        image = Image.open(io.BytesIO(img_resp.content))
        img_arr = np.array(image)

        self.securecode_img = MyFigure()
        self.securecode_img.axes.imshow(img_arr)

        self.gridLayout_securecode.addWidget(self.securecode_img, 0,1)

    def show_AvailTrains(self,trains):
        """在前端顯示可以選擇的班次"""
        for idx, train in enumerate(trains, 1):
            dis_str = ""
            if "Early" in train.discount:
                dis_str += "早鳥{} ".format(train.discount["Early"])
            if "College" in train.discount:
                dis_str += "大學生{}".format(train.discount["College"])
            showstring = "{}. {:>4s} {:>3}~{} {:>3} {:4}".format(
                idx, train.id, train.depart, train.arrive, train.travel_time, dis_str
            )
            self.listWidget_availableTrain.addItem(showstring)

    def show_error(self, html):
        errors = self.error_feedback.parse(html)
        if len(errors) == 0:
            return False

        self.show_error_msg.show(errors)
        return True

    def show_bookingresult(self,tickets):
        ticket = tickets[0]
        self.textEdit_result.setPlainText("""
        \n訂位代號: {}
        \n繳費期限: {}
        \n總價:    {}
        \n[日期", "起程站", "到達站", "出發時間", "到達時間", "車次"]
        \n{}   {}     {}     {}    {}      {}
        \n{} {}""".format(ticket.id,ticket.payment_deadline,ticket.price, \
                          ticket.date, ticket.start_station, ticket.dest_station, ticket.depart_time,
                          ticket.arrival_time, ticket.train_id,ticket.seat_class, ticket.seat
                          ) )

    def Remove_Plot(self,obj):
        obj.close()
        obj.deleteLater()
        gc.collect()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())
