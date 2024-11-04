import mimetypes
import sys
import soundfile as sf
import librosa
from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError
import os
import sqlite3
from PyQt5.uic import loadUi
from PyQt5.QtSql import QSqlDatabase, QSqlQuery, QSqlTableModel
from PyQt5.QtWidgets import QWidget, QMainWindow, QApplication, QTableView, QSlider, QAbstractItemView, QTabWidget
from PyQt5.QtWidgets import QSpinBox, QFileDialog, QMessageBox
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt

# Условия на запуск программы на мониторах с высоким и обычным разрешением
if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)

if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)


class AudioEditor(QMainWindow):

    def __init__(self):
        super().__init__()
        loadUi('project.ui', self)
        self.selected_data = None
        self.name_file = None
        self.initUI()

    def initUI(self):
        database_name = 'audio_1.db'

        success = self.try_connect_to_database(database_name)

        if not success:
            self.show_error_message('База данных не найдена!')
            sys.exit(1)

        # Подключение к бд
        self.db = QSqlDatabase.addDatabase('QSQLITE')
        self.db.setDatabaseName('audio_1.db')
        self.db.open()

        self.model = QSqlTableModel(self)  # Указываем имя нашей таблицы
        self.model.setTable("name_files")  # Выбираем все данные из таблицы
        self.model.select()

        self.model_two = QSqlTableModel(self)  # Указываем имя нашей таблицы
        self.model_two.setTable("changes")  # Выбираем все данные из таблицы
        self.model_two.select()

        self.model.setHeaderData(0, 1, "ID")  # Изменяем названия на более понятные пользователю
        self.model.setHeaderData(1, 1, "Название")
        self.model.setHeaderData(2, 1, "Время воспроизведения (сек)")
        self.model.setHeaderData(3, 1, "Формат файла")
        self.model.setHeaderData(4, 1, "Размер (МБ)")
        self.model.setHeaderData(5, 1, "Ссылка к файлу")
        self.model.setHeaderData(6, 1, "Изменялся ли?")

        self.model_two.setHeaderData(0, 1, "ID")
        self.model_two.setHeaderData(1, 1, "Название")
        self.model_two.setHeaderData(2, 1, "Был ли перевёрнут?")
        self.model_two.setHeaderData(3, 1, "Ускорялся?")
        self.model_two.setHeaderData(4, 1, "Замедлялся?")
        self.model_two.setHeaderData(5, 1, "Повышали тональность?")
        self.model_two.setHeaderData(6, 1, "Понижали тональность?")

        # Получение QTabWidget
        tab_widget = self.findChild(QTabWidget, 'tabWidget')  # Замените на имя вашего QTabWidget

        tab_widget_1 = tab_widget.findChild(QWidget, 'tab')  # Получение виджета вкладки
        table_view_1 = tab_widget_1.findChild(QTableView, 'tableview_1')  # Получение таблицы виджета
        table_view_1.setModel(self.model)

        # То же самое с остальными
        tab_widget_information = tab_widget.findChild(QWidget, 'information')
        table_view_3 = tab_widget_information.findChild(QTableView, 'tableview_3')
        table_view_3.setModel(self.model_two)

        tab_widget_change = tab_widget.findChild(QWidget, 'change')
        table_view_2 = tab_widget_change.findChild(QTableView, 'tableview_2')
        table_view_2.setModel(self.model)

        table_view_2.setSelectionMode(QAbstractItemView.SingleSelection)
        table_view_2.setSelectionBehavior(QAbstractItemView.SelectItems)

        # Подключаем QSlider и QSpinBox вместе
        spinbox_key = tab_widget_change.findChild(QSpinBox, 'spinbox_key')
        horizontalslider_key = tab_widget_change.findChild(QSlider, 'horizontalslider_key')
        spinbox_key.valueChanged.connect(horizontalslider_key.setValue)
        horizontalslider_key.valueChanged.connect(spinbox_key.setValue)

        horizontalslider_key.setMinimum(-12)
        horizontalslider_key.setMaximum(12)

        spinbox_key.setRange(-12, 12)

        spinbox_speed = tab_widget_change.findChild(QSpinBox, 'spinbox_speed')
        horizontalslider_speed = tab_widget_change.findChild(QSlider, 'horizontalslider_speed')
        spinbox_speed.valueChanged.connect(horizontalslider_speed.setValue)
        horizontalslider_speed.valueChanged.connect(spinbox_speed.setValue)

        horizontalslider_speed.setMinimum(1)
        horizontalslider_speed.setMaximum(3)

        spinbox_speed.setRange(1, 3)

        # Подключаем кнопки
        self.button_for_upload.clicked.connect(self.upload_name_files)
        self.upscaling.clicked.connect(self.key_up)
        self.downscaling.clicked.connect(self.key_down)
        self.speed_up.clicked.connect(self.change_speed_up)
        self.speed_down.clicked.connect(self.change_speed_down)
        self.reverse.clicked.connect(self.reverse_file)
        self.search.clicked.connect(self.search_file_name_files)
        self.search_2.clicked.connect(self.search_file_change)
        self.tableview_2.clicked.connect(self.cell_clicked)

    def try_connect_to_database(self, database_name): # Проверка на наличие базы данных
        try:
            connection = sqlite3.connect(database_name)
            cursor = connection.cursor()
            cursor.execute('SELECT * from name_files')
            connection.close()
            return True
        except sqlite3.Error:
            return False

    def cell_clicked(self, index):
        # Получение данных из выбранной ячейки
        row = index.row()
        column = index.column()
        data = self.model.data(self.model.index(row, column), Qt.DisplayRole)
        self.selected_data = data
        self.name_file = self.model.data(self.model.index(row, 1), Qt.DisplayRole)

    def change_speed_down(self):  # Понижение скорости
        if self.name_file is None:
            return self.show_error_message('Файл не выбран!')
        qslider_speed = self.horizontalslider_speed.value()
        if qslider_speed == 2:
            qslider_speed = 0.5
        else:
            qslider_speed = 0.33
        if self.is_audio_file(self.selected_data):
            self.change_speed(self.selected_data, f'{self.name_file}_speed_down', qslider_speed)
            conn = sqlite3.connect('audio_1.db')
            cursor = conn.cursor()
            update_query = "UPDATE changes SET speed_low = ? WHERE name = ?"
            data = 'Да'
            cursor.execute(update_query, (data, self.name_file))
            conn.commit()
            conn.close()
            self.model_two.select()
        else:
            self.show_error_message('Это не ссылка на аудиофайл или вообще не ссылка!')

    def change_speed_up(self):  # Повышение скорости
        if self.name_file is None:
            return self.show_error_message('Файл не выбран!')
        qslider_speed = self.horizontalslider_speed.value()
        if self.is_audio_file(self.selected_data):
            self.change_speed(self.selected_data, f'{self.name_file}_speed_up', qslider_speed)
            conn = sqlite3.connect('audio_1.db')
            cursor = conn.cursor()
            update_query = "UPDATE changes SET speed_up = ? WHERE name = ?"
            data = 'Да'
            cursor.execute(update_query, (data, self.name_file))
            conn.commit()
            conn.close()
            self.model_two.select()
        else:
            self.show_error_message('Это не ссылка на аудиофайл или вообще не ссылка!')

    def change_speed(self, input_file, output_file, speed_factor=1.0):
        y, sr = librosa.load(input_file)

        # Изменение скорости аудио
        y_modified_speed = librosa.effects.time_stretch(y, rate=speed_factor)

        # Сохраняем измененный аудиофайл
        output_speed_file = f"{output_file}_speed.wav"
        sf.write(output_speed_file, y_modified_speed, sr)
        self.save_change_on_table_bd()

    def key_up(self):  # Повышение тональности
        if self.name_file is None:
            return self.show_error_message('Файл не выбран!')
        qslider_key = self.horizontalslider_key.value()
        if qslider_key == 0:
            qslider_key = 1
        if qslider_key < 0:
            qslider_key = abs(qslider_key)
        if self.is_audio_file(self.selected_data):
            self.change_speed(self.selected_data, f'{self.name_file}_key_up', qslider_key)
            conn = sqlite3.connect('audio_1.db')
            cursor = conn.cursor()
            update_query = "UPDATE changes SET raising_tone = ? WHERE name = ?"
            data = 'Да'
            cursor.execute(update_query, (data, self.name_file))
            conn.commit()
            conn.close()
            self.model_two.select()
        else:
            self.show_error_message('Это не ссылка на аудиофайл или вообще не ссылка!')

    def key_down(self):  # Понижение тональности
        if self.name_file is None:
            return self.show_error_message('Файл не выбран!')
        qslider_key = self.horizontalslider_key.value()
        if qslider_key == 0:
            qslider_key = 1
        if qslider_key > 0:
            qslider_key = -qslider_key
        if self.is_audio_file(self.selected_data):
            self.change_pitch(self.selected_data, f'{self.name_file}_key_down.wav', qslider_key)
            self.reverse_audio(self.selected_data, f'{self.name_file}_reverse.wav')
            conn = sqlite3.connect('audio_1.db')
            cursor = conn.cursor()
            update_query = "UPDATE changes SET downscaling_tone = ? WHERE name = ?"
            data = 'Да'
            cursor.execute(update_query, (data, self.name_file))
            conn.commit()
            conn.close()
            self.model_two.select()
        else:
            self.show_error_message('Это не ссылка на аудиофайл или вообще не ссылка!')

    def change_pitch(self, input_file, output_file, semitones):
        audio = AudioSegment.from_file(input_file)
        # Изменение тональности аудио
        modified_audio = audio._spawn(audio.raw_data, overrides={
            "frame_rate": int(audio.frame_rate * (2 ** (semitones / 12.0)))
        })
        modified_audio.export(output_file, format="wav")
        self.save_change_on_table_bd()

    def reverse_file(self):  # Обратная перемотка
        if self.name_file is None:
            return self.show_error_message('Файл не выбран!')
        if self.is_audio_file(self.selected_data):
            self.reverse_audio(self.selected_data, f'{self.name_file}_reverse.wav')
            conn = sqlite3.connect('audio_1.db')
            cursor = conn.cursor()
            update_query = "UPDATE changes SET reverse = ? WHERE name = ?"
            data = 'Да'
            cursor.execute(update_query, (data, self.name_file))
            conn.commit()
            conn.close()
            self.model_two.select()
        else:
            self.show_error_message('Это не ссылка на аудиофайл или вообще не ссылка!')

    def reverse_audio(self, input_file, output_file):  # Обратная перемотка
        audio = AudioSegment.from_file(input_file)
        reversed_audio = audio.reverse()
        reversed_audio.export(output_file, format="wav")
        self.save_change_on_table_bd()

    def save_change_on_table_bd(self):  # Обновляем бд, если файл изменялся
        conn = sqlite3.connect('audio_1.db')
        cursor = conn.cursor()
        update_query = "UPDATE name_files SET change = ? WHERE name = ?"
        data = 'Да'
        cursor.execute(update_query, (data, self.name_file))
        conn.commit()
        conn.close()
        self.model.select()

    def upload_name_files(self):  # Загрузка данных о файле в бд
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(self, 'Открыть аудиофайл', '', 'Audio Files (*.mp3 *.wav)')

        if file_path:
            try:
                # Открываем аудиофайл
                audio = AudioSegment.from_file(file_path)

                # Получаем информацию
                audio_name = os.path.basename(file_path)[:-4]
                audio_size_mb = round(os.path.getsize(file_path) / (1024 * 1024))  # в мегабайтах
                audio_duration = round(len(audio) / 1000)  # в секундах
                audio_absolute_path = os.path.abspath(file_path)
                audio_type = os.path.basename(file_path)[-3:]
                if audio_size_mb > 100 or audio_duration > 360:
                    return self.show_error_message('Слишком большой или слишком длинный аудиофайл, попробуйте другой')

                conn = sqlite3.connect('audio_1.db')
                cursor = conn.cursor()
                dubl = 'SELECT name from name_files'
                cursor.execute(dubl)
                result = [name[0] for name in cursor.fetchall()]
                if audio_name in result:
                    self.show_error_message('Такой файл уже есть!')
                else:
                    sql_query = ("INSERT INTO name_files (name, time, type, size, link, change) VALUES "
                                 "(?, ?, ?, ?, ?, ?);")
                    data = (audio_name, audio_duration, audio_type, audio_size_mb, audio_absolute_path, 'Нет')
                    cursor.execute(sql_query, data)
                    conn.commit()
                    conn.close()
                    self.upload_changes(audio_name)
                self.model.select()
            except CouldntDecodeError:
                self.show_error_message("Ошибка: Файл не является аудиофайлом в поддерживаемом формате.")

    def upload_changes(self, name_file):  # Параллельно загружаем данные в таблицу change
        conn = sqlite3.connect('audio_1.db')
        cursor = conn.cursor()
        sql_query = ("INSERT INTO changes (name, reverse, speed_up, speed_low, raising_tone, downscaling_tone) VALUES "
                     "(?, ?, ?, ?, ?, ?);")
        data = (name_file, 'Нет', 'Нет', 'Нет', 'Нет', 'Нет')
        cursor.execute(sql_query, data)
        conn.commit()
        conn.close()
        self.model_two.select()

    def search_file_name_files(self):  # Фильтр для name_files
        selected_column = self.filter_selection.currentText()
        filter_text = self.parameter.toPlainText()
        query = QSqlQuery()
        if selected_column == 'Сбросить':
            self.model.setFilter('')
            self.model.select()
        else:
            query.prepare(f"SELECT * FROM name_files WHERE {self.info_col_file(selected_column)} LIKE :filter_value")
            query.bindValue(":filter_value", f"%{filter_text}%")
            query.exec_()
            self.model.setQuery(query)
            # Обновляем запрос в существующей модели
            # Применение результата запроса к модели данных

    def info_col_file(self, select_col):
        if select_col == 'Название файла':
            return 'name'
        if select_col == 'Время воспроизведения файла':
            return 'time'
        if select_col == 'Формат файла':
            return 'type'
        if select_col == 'Размер файла':
            return 'size'
        if select_col == 'Ссылка к файлу':
            return 'link'

    def search_file_change(self):  # Фильтр для changes
        selected_column = self.filter_selection_2.currentText()
        filter_text = self.parameter_2.toPlainText()
        query = QSqlQuery()
        if selected_column == 'Сбросить':
            self.model_two.setFilter('')
            self.model_two.select()
        else:
            query.prepare(f"SELECT * FROM changes WHERE {self.info_column_change(selected_column)} LIKE :filter_value")
            query.bindValue(":filter_value", f"%{filter_text}%")
            query.exec_()
            self.model_two.setQuery(query)
            # Обновляем запрос в существующей модели
            # Применение результата запроса к модели данных

    def info_column_change(self, col):
        if col == 'Название файла':
            return 'name'
        if col == 'Обратная перемотка':
            return 'reverse'
        if col == 'Ускорение':
            return 'speed_up'
        if col == 'Замедление':
            return 'speed_low'
        if col == 'Повышение тональности':
            return 'raising_tone'
        if col == 'Понижение тональности':
            return 'downscaling_tone'
        
    def is_audio_file(self, file_path):  # Проверка на файл
        # Проверяем, существует ли файл
        if not os.path.exists(file_path):
            return False

        # Получаем MIME-тип файла
        mime_type, _ = mimetypes.guess_type(file_path)

        # Проверяем, является ли MIME-тип аудио
        if mime_type and mime_type.startswith('audio'):
            return True

        return False

    def show_error_message(self, error_text):  # Окно ошибки для вывода
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText("Произошла ошибка")
        msg.setInformativeText("Подробности ошибки:\n" + error_text)
        msg.setWindowTitle("Ошибка")
        msg.exec_()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = AudioEditor()
    ex.show()
    sys.exit(app.exec_())
