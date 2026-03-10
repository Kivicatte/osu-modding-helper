from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QFontMetrics, QPainter


class ElidingLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self._full_text = text
        self.setText(text)

    def setText(self, text: str):
        self._full_text = text
        self._update_elided_text()

    def text(self):
        return self._full_text

    def _update_elided_text(self):
        if not self._full_text:
            super().setText("")
            return

        metrics: QFontMetrics = self.fontMetrics()
        available_width = self.width() - 4

        elided = metrics.elidedText(self._full_text, Qt.ElideRight, available_width)
        super().setText(elided)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_elided_text()


class ImageContainer(QLabel):
    def __init__(self, parent=None, pixmap=None):
        super().__init__(parent)
        self._pixmap = QPixmap()
        self.setMinimumSize(32, 18)
        self.setAlignment(Qt.AlignCenter)
        self.setScaledContents(False)

        if pixmap:
            self.setPixmap(pixmap)

    def setPixmap(self, pixmap: QPixmap):
        self._pixmap = pixmap
        self.update()
        self.updateGeometry()

    def pixmap(self):
        return self._pixmap

    def sizeHint(self):
        if self._pixmap.isNull():
            return super().sizeHint()
        return self._pixmap.size()

    def paintEvent(self, event):
        if self._pixmap.isNull():
            super().paintEvent(event)
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.setRenderHint(QPainter.Antialiasing, True)

        target_rect = self.rect()
        scaled_pix = self._pixmap.scaled(target_rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)

        x = target_rect.x() + (target_rect.width() - scaled_pix.width()) // 2
        y = target_rect.y() + (target_rect.height() - scaled_pix.height()) // 2

        painter.drawPixmap(x, y, scaled_pix)


class Credits(QWidget):
    def __init__(self, art, title, artist, parent=None):
        super().__init__(parent=parent)

        self._init_ui(art, title, artist)

    def _init_ui(self, art, title, artist):
        self.setFixedHeight(150)
        self.setObjectName('credits')

        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        self.setLayout(layout)

        self.art_label = QLabel(art)
        self.art_label.setAlignment(Qt.AlignCenter)
        self.art_label.setObjectName('top')
        layout.addWidget(self.art_label)

        self.separator_container = QWidget()
        self.separator_container.setLayout(QVBoxLayout())
        self.separator_container.setFixedHeight(21)
        self.separator = QWidget()
        self.separator.setFixedHeight(1)
        self.separator.setObjectName('separator')
        self.separator_container.layout().addWidget(self.separator)
        layout.addWidget(self.separator_container)

        self.title_label = ElidingLabel(title)
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)

        self.artist_label = ElidingLabel('by ' + artist)
        self.artist_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.artist_label)

    def set_artist(self, artist):
        self.artist_label.setText('by ' + artist)

    def set_title(self, title):
        self.title_label.setText(title)
